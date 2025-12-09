"""
项目服务 - 整合 RootData 抓取和数据库操作
"""
import json
from typing import List, Optional, Dict, Literal
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Project
from app.services.rootdata_client import RootDataClient, FetchMode


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.rootdata = RootDataClient()
    
    async def search_projects(self, query: str) -> List[Dict]:
        """搜索项目（RootData）"""
        results = await self.rootdata.search(query)
        # 只返回项目类型（type=1）
        return [r for r in results if r.get("type") == 1]
    
    async def fetch_and_save_project(
        self,
        project_id: int,
        mode: Literal["basic", "full"] = "basic"
    ) -> Project:
        """
        抓取项目信息并保存到数据库
        
        Args:
            project_id: RootData项目ID
            mode: 
                - "basic": 基本信息（不含Pro字段），适合快速浏览
                - "full": 全部信息（含Pro字段），适合深度分析
        """
        fetch_mode = FetchMode.FULL if mode == "full" else FetchMode.BASIC
        
        # 从 RootData 获取数据
        data = await self.rootdata.get_project(project_id=project_id, mode=fetch_mode)
        
        # 检查是否已存在
        existing = self.db.query(Project).filter(
            Project.rootdata_id == project_id
        ).first()
        
        if existing:
            # 更新现有记录
            project = existing
        else:
            # 创建新记录
            project = Project(rootdata_id=project_id)
            self.db.add(project)
        
        # 填充基本字段
        project.name = data.get("project_name")
        project.logo = data.get("logo")
        project.rootdataurl = data.get("rootdataurl")
        project.token_symbol = data.get("token_symbol")
        project.establishment_date = data.get("establishment_date")
        project.one_liner = data.get("one_liner")
        project.description = data.get("description")
        project.active = data.get("active", True)
        project.total_funding = data.get("total_funding")
        project.tags = data.get("tags")
        project.investors = data.get("investors")
        project.social_media = data.get("social_media")
        project.similar_project = data.get("similar_project")
        
        # Pro字段（仅在full模式下有值）
        if mode == "full":
            project.ecosystem = data.get("ecosystem")
            project.on_main_net = data.get("on_main_net")
            project.plan_to_launch = data.get("plan_to_launch")
            project.on_test_net = data.get("on_test_net")
            project.fully_diluted_market_cap = data.get("fully_diluted_market_cap")
            project.market_cap = data.get("market_cap")
            project.price = data.get("price")
            project.event = data.get("event")
            project.reports = data.get("reports")
            project.team_members = data.get("team_members")
            project.token_launch_time = data.get("token_launch_time")
            project.contracts = data.get("contracts")
            project.support_exchanges = data.get("support_exchanges")
            project.heat = data.get("heat")
            project.heat_rank = data.get("heat_rank")
            project.influence = data.get("influence")
            project.influence_rank = data.get("influence_rank")
            project.followers = data.get("followers")
            project.following = data.get("following")
        
        # 保存原始JSON和抓取模式
        project.raw_json = data
        project.fetch_mode = mode
        project.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(project)
        
        return project
    
    async def batch_fetch_projects(
        self,
        project_ids: List[int],
        mode: Literal["basic", "full"] = "basic"
    ) -> List[Project]:
        """批量抓取项目"""
        projects = []
        for pid in project_ids:
            try:
                project = await self.fetch_and_save_project(pid, mode)
                projects.append(project)
            except Exception as e:
                print(f"Failed to fetch project {pid}: {e}")
        return projects
    
    async def fetch_hot_projects(
        self,
        days: int = 7,
        mode: Literal["basic", "full"] = "basic"
    ) -> List[Project]:
        """抓取热门项目Top100"""
        hot_list = await self.rootdata.get_hot_projects(days)
        project_ids = [p["project_id"] for p in hot_list]
        return await self.batch_fetch_projects(project_ids, mode)
    
    def get_project(self, project_id: int) -> Optional[Project]:
        """从数据库获取项目"""
        return self.db.query(Project).filter(
            Project.id == project_id
        ).first()
    
    def get_project_by_rootdata_id(self, rootdata_id: int) -> Optional[Project]:
        """通过RootData ID获取项目"""
        return self.db.query(Project).filter(
            Project.rootdata_id == rootdata_id
        ).first()
    
    def list_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        fetch_mode: str = None
    ) -> List[Project]:
        """列出数据库中的项目"""
        query = self.db.query(Project)
        if fetch_mode:
            query = query.filter(Project.fetch_mode == fetch_mode)
        return query.offset(skip).limit(limit).all()
    
    def get_project_as_dict(self, project: Project) -> Dict:
        """将项目转换为字典"""
        return {
            "id": project.id,
            "rootdata_id": project.rootdata_id,
            "name": project.name,
            "logo": project.logo,
            "rootdataurl": project.rootdataurl,
            "token_symbol": project.token_symbol,
            "one_liner": project.one_liner,
            "description": project.description,
            "total_funding": float(project.total_funding) if project.total_funding else None,
            "tags": project.tags,
            "investors": project.investors,
            "fetch_mode": project.fetch_mode,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        }
    
    def export_project_json(self, project_id: int, output_path: str = None) -> str:
        """导出项目为JSON文件"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        data = project.raw_json or self.get_project_as_dict(project)
        
        if output_path is None:
            output_path = f"data/projects/{project.name}_{project.rootdata_id}.json"
        
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return output_path
