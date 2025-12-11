"""
FastAPI 路由定义
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from pydantic import BaseModel
from pathlib import Path

from app.database import get_db
from app.models import SurfAccount
from app.services.project_service import ProjectService
from app.services.surf_account_pool import SurfAccountPool
from app.services.surf_report_generator import SurfReportGenerator
from app.services.feishu_client import ReportPusher
from app.services.rootdata_client import RootDataClient

router = APIRouter()

# 模板配置
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """前端管理界面"""
    return templates.TemplateResponse("index.html", {"request": request})


# ==================== Schemas ====================

class ProjectSearchRequest(BaseModel):
    query: str


class ProjectFetchRequest(BaseModel):
    project_id: int
    mode: Literal["basic", "full"] = "basic"


class BatchFetchRequest(BaseModel):
    project_ids: List[int]
    mode: Literal["basic", "full"] = "basic"


class SurfAccountCreate(BaseModel):
    email: str
    password: str


class GenerateReportRequest(BaseModel):
    project_id: int
    mode: Literal["chat", "research"] = "chat"  # chat=快速问答, research=深度研究


# ==================== RootData & Projects ====================

@router.get("/api/quota")
async def get_rootdata_quota():
    """查询 RootData API 余额"""
    client = RootDataClient()
    return await client.get_quota()


@router.post("/api/projects/search")
async def search_projects(request: ProjectSearchRequest, db: Session = Depends(get_db)):
    """搜索项目"""
    service = ProjectService(db)
    results = await service.search_projects(request.query)
    return {"data": results, "count": len(results)}


@router.post("/api/projects/fetch")
async def fetch_project(request: ProjectFetchRequest, db: Session = Depends(get_db)):
    """
    抓取单个项目信息
    - mode=basic: 基本信息（不含Pro字段）
    - mode=full: 全部信息（含Pro字段）
    """
    service = ProjectService(db)
    project = await service.fetch_and_save_project(request.project_id, request.mode)
    return {
        "message": f"Project '{project.name}' fetched successfully",
        "data": service.get_project_as_dict(project)
    }


@router.post("/api/projects/fetch/batch")
async def batch_fetch_projects(
    request: BatchFetchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量抓取项目（后台执行）"""
    service = ProjectService(db)
    
    async def fetch_task():
        await service.batch_fetch_projects(request.project_ids, request.mode)
    
    background_tasks.add_task(fetch_task)
    
    return {
        "message": f"Batch fetch started for {len(request.project_ids)} projects",
        "mode": request.mode
    }


@router.get("/api/projects/hot")
async def fetch_hot_projects(
    days: int = Query(7, description="1 或 7"),
    mode: Literal["basic", "full"] = "basic",
    db: Session = Depends(get_db)
):
    """抓取热门项目Top100"""
    service = ProjectService(db)
    projects = await service.fetch_hot_projects(days, mode)
    return {
        "message": f"Fetched {len(projects)} hot projects",
        "count": len(projects)
    }


@router.get("/api/projects")
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    fetch_mode: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出数据库中的项目"""
    service = ProjectService(db)
    projects = service.list_projects(skip, limit, fetch_mode)
    return {
        "data": [service.get_project_as_dict(p) for p in projects],
        "count": len(projects)
    }


@router.get("/api/projects/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """获取单个项目详情"""
    service = ProjectService(db)
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return service.get_project_as_dict(project)


@router.get("/api/projects/{project_id}/export")
async def export_project(project_id: int, db: Session = Depends(get_db)):
    """导出项目为JSON"""
    service = ProjectService(db)
    try:
        path = service.export_project_json(project_id)
        return {"message": "Exported successfully", "path": path}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Surf Accounts ====================

@router.get("/api/surf/accounts")
async def list_surf_accounts(db: Session = Depends(get_db)):
    """列出所有Surf账号状态"""
    pool = SurfAccountPool(db)
    return {
        "data": pool.get_all_accounts_status(),
        "total_remaining_quota": pool.get_total_remaining_quota()
    }


@router.post("/api/surf/accounts")
async def add_surf_account(request: SurfAccountCreate, db: Session = Depends(get_db)):
    """添加Surf账号（使用邮箱验证码登录）"""
    pool = SurfAccountPool(db)
    try:
        # 现在需要邮箱密码和IMAP配置
        account = pool.add_account(
            email=request.email,
            email_password=request.password,  # 这里的password实际是邮箱密码
            email_server=getattr(request, 'email_server', 'imap.gmail.com'),
            email_port=getattr(request, 'email_port', 993)
        )
        return {
            "message": "Account added successfully",
            "id": account.id,
            "email": account.email
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class UpdateEmailPasswordRequest(BaseModel):
    email_password: str
    email_server: Optional[str] = None
    email_port: Optional[int] = None


# 注意：更具体的路由（带 /enable 和 /password）必须放在更通用的路由（只有 {account_id}）之前
@router.put("/api/surf/accounts/{account_id}/enable")
async def enable_surf_account(account_id: int, db: Session = Depends(get_db)):
    """启用Surf账号"""
    pool = SurfAccountPool(db)
    account = db.query(SurfAccount).filter(SurfAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    pool.enable_account(account_id)
    return {"message": "Account enabled"}


@router.put("/api/surf/accounts/{account_id}/password")
async def update_surf_account_password(
    account_id: int,
    request: UpdateEmailPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    更新Surf账号的邮箱密码
    
    用于更新应用密码（当Outlook等邮箱需要应用密码时）
    """
    pool = SurfAccountPool(db)
    account = db.query(SurfAccount).filter(SurfAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # 加密新密码
    encrypted_password = pool.cipher.encrypt(request.email_password.encode()).decode()
    account.email_password_encrypted = encrypted_password
    
    # 更新IMAP服务器配置（如果提供）
    if request.email_server:
        account.email_server = request.email_server
    if request.email_port:
        account.email_port = request.email_port
    
    db.commit()
    
    return {
        "message": "Password updated successfully",
        "id": account.id,
        "email": account.email
    }


@router.delete("/api/surf/accounts/{account_id}")
async def disable_surf_account(account_id: int, db: Session = Depends(get_db)):
    """禁用Surf账号"""
    pool = SurfAccountPool(db)
    account = db.query(SurfAccount).filter(SurfAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    pool.disable_account(account_id)
    return {"message": "Account disabled"}


# ==================== Reports ====================

@router.post("/api/reports/generate")
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    生成投研报告
    
    mode参数:
    - chat: 快速问答模式（30秒-1分钟）
    - research: 深度研究模式（3-10分钟，每周2次免费）
    """
    from app.services.surf_report_generator import ReportMode
    
    pool = SurfAccountPool(db)
    
    if pool.get_total_remaining_quota() <= 0:
        raise HTTPException(
            status_code=400,
            detail="No remaining quota. All accounts have exhausted their weekly limit."
        )
    
    generator = SurfReportGenerator(db)
    report_mode = ReportMode.RESEARCH if request.mode == "research" else ReportMode.CHAT
    
    async def generate_task():
        await generator.generate_report(request.project_id, report_mode)
    
    background_tasks.add_task(generate_task)
    
    mode_desc = "深度研究" if request.mode == "research" else "快速问答"
    return {
        "message": f"Report generation started ({mode_desc})",
        "project_id": request.project_id,
        "mode": request.mode
    }


@router.get("/api/reports")
async def list_reports(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """列出投研报告"""
    from app.models import Report
    
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    
    reports = query.offset(skip).limit(limit).all()
    
    return {
        "data": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "status": r.status,
                "pdf_path": r.report_pdf_path,
                "feishu_record_id": r.feishu_record_id,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reports
        ]
    }


# ==================== Feishu ====================

@router.post("/api/feishu/push/{report_id}")
async def push_to_feishu(report_id: int, db: Session = Depends(get_db)):
    """推送报告到飞书"""
    from app.models import Report
    
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != 'completed':
        raise HTTPException(status_code=400, detail="Report not completed yet")
    
    service = ProjectService(db)
    project = service.get_project(report.project_id)
    
    pusher = ReportPusher(settings.feishu_base_file_path)
    
    try:
        record_id = await pusher.push_report(
            project_name=project.name,
            project_info=service.get_project_as_dict(project),
            report_pdf_path=report.report_pdf_path
        )
        
        report.feishu_record_id = record_id
        db.commit()
        
        return {
            "message": "Pushed to Feishu successfully",
            "feishu_record_id": record_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VC/机构 ====================

@router.get("/api/vcs")
async def list_vcs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出数据库中的VC/机构"""
    from app.services.vc_service import VCService
    service = VCService(db)
    vcs = service.list_vcs(skip, limit)
    return {
        "data": [service.get_vc_as_dict(v) for v in vcs],
        "count": len(vcs)
    }


@router.post("/api/vcs/fetch")
async def fetch_vc(
    org_id: int,
    include_team: bool = True,
    include_investments: bool = True,
    db: Session = Depends(get_db)
):
    """抓取单个VC/机构信息"""
    from app.services.vc_service import VCService
    service = VCService(db)
    vc = await service.fetch_and_save_vc(org_id, include_team, include_investments)
    return {
        "message": f"VC '{vc.org_name}' fetched successfully",
        "data": service.get_vc_as_dict(vc)
    }


@router.post("/api/vcs/fetch/batch")
async def fetch_investor_batches(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """批量抓取投资者信息"""
    from app.services.vc_service import VCService
    service = VCService(db)
    vcs = await service.fetch_and_save_investor_batches(page, page_size)
    return {
        "message": f"Fetched {len(vcs)} investors",
        "count": len(vcs)
    }


# ==================== 人物 ====================

@router.get("/api/people")
async def list_people(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出数据库中的人物"""
    from app.services.people_service import PeopleService
    service = PeopleService(db)
    people = service.list_people(skip, limit)
    return {
        "data": [service.get_people_as_dict(p) for p in people],
        "count": len(people)
    }


@router.post("/api/people/fetch")
async def fetch_people(
    people_id: int,
    db: Session = Depends(get_db)
):
    """抓取单个人物信息"""
    from app.services.people_service import PeopleService
    service = PeopleService(db)
    person = await service.fetch_and_save_people(people_id)
    return {
        "message": f"People '{person.people_name}' fetched successfully",
        "data": service.get_people_as_dict(person)
    }


@router.post("/api/people/job-changes")
async def fetch_job_changes(
    recent_joinees: bool = True,
    recent_resignations: bool = True,
    db: Session = Depends(get_db)
):
    """获取人物职位变动"""
    from app.services.people_service import PeopleService
    service = PeopleService(db)
    result = await service.fetch_and_save_job_changes(recent_joinees, recent_resignations)
    return {
        "message": "Job changes fetched successfully",
        "recent_joinees_count": len(result["recent_joinees"]),
        "recent_resignations_count": len(result["recent_resignations"])
    }


# ==================== 投资轮次 ====================

@router.get("/api/funding-rounds")
async def list_funding_rounds(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """列出投资轮次"""
    from app.services.data_service import DataService
    service = DataService(db)
    rounds = service.list_funding_rounds(skip, limit, project_id)
    return {
        "data": [service.get_funding_round_as_dict(r) for r in rounds],
        "count": len(rounds)
    }


@router.post("/api/funding-rounds/fetch")
async def fetch_funding_rounds(
    page: int = 1,
    page_size: int = 10,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """批量抓取投资轮次"""
    from app.services.data_service import DataService
    service = DataService(db)
    rounds = await service.fetch_and_save_funding_rounds(
        page, page_size, start_time, end_time, min_amount, max_amount, project_id
    )
    return {
        "message": f"Fetched {len(rounds)} funding rounds",
        "count": len(rounds)
    }


# ==================== 生态 ====================

@router.get("/api/ecosystems")
async def list_ecosystems(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出生态"""
    from app.services.data_service import DataService
    service = DataService(db)
    ecosystems = service.list_ecosystems(skip, limit)
    return {
        "data": [service.get_ecosystem_as_dict(e) for e in ecosystems],
        "count": len(ecosystems)
    }


@router.post("/api/ecosystems/fetch")
async def fetch_ecosystems(db: Session = Depends(get_db)):
    """抓取生态列表"""
    from app.services.data_service import DataService
    service = DataService(db)
    ecosystems = await service.fetch_and_save_ecosystems()
    return {
        "message": f"Fetched {len(ecosystems)} ecosystems",
        "count": len(ecosystems)
    }


# ==================== 标签 ====================

@router.get("/api/tags")
async def list_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出标签"""
    from app.services.data_service import DataService
    service = DataService(db)
    tags = service.list_tags(skip, limit)
    return {
        "data": [service.get_tag_as_dict(t) for t in tags],
        "count": len(tags)
    }


@router.post("/api/tags/fetch")
async def fetch_tags(db: Session = Depends(get_db)):
    """抓取标签列表"""
    from app.services.data_service import DataService
    service = DataService(db)
    tags = await service.fetch_and_save_tags()
    return {
        "message": f"Fetched {len(tags)} tags",
        "count": len(tags)
    }


# ==================== X数据 ====================

@router.get("/api/x-data")
async def list_x_data(
    skip: int = 0,
    limit: int = 100,
    entity_type: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """列出X数据 (entity_type: 1=项目, 2=机构, 3=人物)"""
    from app.services.data_service import DataService
    service = DataService(db)
    x_data = service.list_x_data(skip, limit, entity_type)
    return {
        "data": [service.get_x_data_as_dict(x) for x in x_data],
        "count": len(x_data)
    }


@router.post("/api/x-data/fetch")
async def fetch_x_data(
    entity_type: int = Query(..., description="1=项目, 2=机构, 3=人物"),
    db: Session = Depends(get_db)
):
    """批量抓取X数据"""
    from app.services.data_service import DataService
    service = DataService(db)
    x_data = await service.fetch_and_save_x_data(entity_type)
    return {
        "message": f"Fetched {len(x_data)} X data entries",
        "count": len(x_data)
    }


@router.get("/api/x-data/hot-projects")
async def get_hot_projects_on_x(
    heat: bool = True,
    influence: bool = True,
    followers: bool = True,
    db: Session = Depends(get_db)
):
    """获取X热门项目"""
    from app.services.data_service import DataService
    service = DataService(db)
    data = await service.fetch_hot_projects_on_x(heat, influence, followers)
    return {"data": data}


# ==================== 测试功能 - 搜索并保存 ====================

@router.post("/api/test/search-and-save")
async def test_search_and_save(
    query: str,
    precise_x_search: bool = False,
    db: Session = Depends(get_db)
):
    """
    测试功能：搜索项目/机构/人物并保存到数据库
    使用 ser_inv 接口（免费，不限次数）
    """
    from app.models import SearchResult
    
    # 调用搜索接口
    client = RootDataClient()
    results = await client.search(query, precise_x_search)
    
    saved_count = 0
    saved_items = []
    
    for item in results:
        entity_id = item.get("id")
        if not entity_id:
            continue
        
        # 创建新记录
        search_result = SearchResult(
            query=query,
            entity_id=entity_id,
            entity_type=item.get("type"),
            name=item.get("name"),
            logo=item.get("logo"),
            introduce=item.get("introduce"),
            active=item.get("active", True),
            rootdataurl=item.get("rootdataurl"),
            raw_json=item
        )
        db.add(search_result)
        saved_count += 1
        saved_items.append({
            "entity_id": entity_id,
            "type": item.get("type"),
            "name": item.get("name"),
            "introduce": item.get("introduce"),
            "active": item.get("active"),
            "rootdataurl": item.get("rootdataurl")
        })
    
    db.commit()
    
    return {
        "message": f"搜索完成，保存了 {saved_count} 条结果",
        "query": query,
        "count": saved_count,
        "data": saved_items
    }


@router.get("/api/test/search-results")
async def list_search_results(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=50, description="每页条数"),
    query: Optional[str] = None,
    entity_type: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """列出已保存的搜索结果（支持分页）"""
    from app.models import SearchResult
    
    q = db.query(SearchResult)
    if query:
        q = q.filter(SearchResult.query.like(f"%{query}%"))
    if entity_type:
        q = q.filter(SearchResult.entity_type == entity_type)
    
    # 获取总数
    total_count = q.count()

    # 分页查询
    skip = (page - 1) * page_size
    results = q.order_by(SearchResult.created_at.desc()).offset(skip).limit(page_size).all()

    # 计算总页数
    total_pages = (total_count + page_size - 1) // page_size
    
    return {
        "data": [
            {
                "id": r.id,
                "query": r.query,
                "entity_id": r.entity_id,
                "entity_type": r.entity_type,
                "type_name": {1: "项目", 2: "机构", 3: "人物"}.get(r.entity_type, "未知"),
                "name": r.name,
                "logo": r.logo,
                "introduce": r.introduce,
                "active": r.active,
                "rootdataurl": r.rootdataurl,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in results
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@router.delete("/api/test/search-results/{result_id}")
async def delete_search_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """删除搜索结果"""
    from app.models import SearchResult
    
    result = db.query(SearchResult).filter(SearchResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    db.delete(result)
    db.commit()
    
    return {"message": "删除成功"}


# ==================== 图片代理 ====================

@router.get("/api/proxy/image")
async def proxy_image(url: str):
    """
    图片代理接口 - 解决RootData图片403错误
    通过服务器代理获取图片，避免浏览器直接访问时的防盗链限制
    """
    try:
        import httpx
        from fastapi.responses import StreamingResponse
        import io

        # 验证URL是否来自RootData
        if not url.startswith("https://public.rootdata.com/"):
            raise HTTPException(status_code=403, detail="只允许代理RootData图片")

        # 设置适当的User-Agent和Referer来绕过防盗链
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.rootdata.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        }

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=headers
        ) as client:
            response = await client.get(url)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"获取图片失败: {response.status_code}"
                )

            # 获取图片内容类型
            content_type = response.headers.get("content-type", "image/jpeg")

            # 返回图片流
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 缓存1小时
                    "Access-Control-Allow-Origin": "*"
                }
            )

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"网络请求错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片代理错误: {str(e)}")


@router.get("/api/image/{path:path}")
async def get_image(path: str):
    """
    便捷的图片访问接口
    使用方式: /api/image/b12/1683864953207.jpg
    """
    full_url = f"https://public.rootdata.com/images/{path}"
    return await proxy_image(full_url)
