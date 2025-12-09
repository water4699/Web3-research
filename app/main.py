"""
FastAPI 应用主入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.database import init_db
from app.api.routes import router
from app.scheduler import start_scheduler, shutdown_scheduler
from app.config import get_settings

settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    init_db()
    start_scheduler()
    yield
    # 关闭时
    shutdown_scheduler()


app = FastAPI(
    title="Crypto Research System",
    description="""
    加密项目投研系统
    
    ## 功能
    - RootData 项目数据抓取（基本信息/全部信息两种模式）
    - Surf 投研报告自动生成
    - 飞书多维表格推送
    - Surf 账号池管理（每周2次免费额度自动轮换）
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 注册API路由
app.include_router(router)


@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "name": "Crypto Research System",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "projects": "/api/projects",
            "surf_accounts": "/api/surf/accounts",
            "reports": "/api/reports",
            "quota": "/api/quota"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
