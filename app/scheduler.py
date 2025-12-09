"""
定时任务调度器
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from app.database import SessionLocal
from app.services.project_service import ProjectService
from app.services.surf_report_generator import SurfReportGenerator
from app.services.surf_account_pool import SurfAccountPool

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def job_fetch_hot_projects():
    """定时抓取热门项目"""
    logger.info(f"[{datetime.now()}] Starting scheduled hot projects fetch...")
    
    db = SessionLocal()
    try:
        service = ProjectService(db)
        projects = await service.fetch_hot_projects(days=7, mode="basic")
        logger.info(f"Fetched {len(projects)} hot projects")
    except Exception as e:
        logger.error(f"Failed to fetch hot projects: {e}")
    finally:
        db.close()


async def job_generate_pending_reports():
    """定时生成待处理的报告"""
    logger.info(f"[{datetime.now()}] Checking for pending report generation...")
    
    db = SessionLocal()
    try:
        pool = SurfAccountPool(db)
        remaining = pool.get_total_remaining_quota()
        
        if remaining <= 0:
            logger.info("No remaining Surf quota this week")
            return
        
        # 获取需要生成报告但还没有报告的项目
        from app.models import Project, Report
        
        projects_without_report = db.query(Project).outerjoin(Report).filter(
            Report.id.is_(None)
        ).limit(remaining).all()
        
        if not projects_without_report:
            logger.info("No projects pending for report generation")
            return
        
        generator = SurfReportGenerator(db)
        
        for project in projects_without_report:
            try:
                await generator.generate_report(project.id)
                logger.info(f"Generated report for project: {project.name}")
            except Exception as e:
                logger.error(f"Failed to generate report for {project.name}: {e}")
            
            # 检查剩余配额
            if pool.get_total_remaining_quota() <= 0:
                logger.info("Surf quota exhausted")
                break
    
    except Exception as e:
        logger.error(f"Error in report generation job: {e}")
    finally:
        db.close()


async def job_reset_weekly_quota():
    """每周一重置Surf账号配额（实际由账号池自动处理，这里只是日志记录）"""
    logger.info(f"[{datetime.now()}] Weekly quota reset check...")
    
    db = SessionLocal()
    try:
        pool = SurfAccountPool(db)
        status = pool.get_all_accounts_status()
        total = pool.get_total_remaining_quota()
        logger.info(f"Total remaining quota: {total}")
        for acc in status:
            logger.info(f"  Account {acc['email']}: {acc['remaining']}/{acc['weekly_quota_limit']}")
    finally:
        db.close()


def start_scheduler():
    """启动调度器"""
    # 每天凌晨2点抓取热门项目
    scheduler.add_job(
        job_fetch_hot_projects,
        trigger=CronTrigger(hour=2, minute=0),
        id="fetch_hot_projects",
        replace_existing=True
    )
    
    # 每天上午10点和下午3点尝试生成报告
    scheduler.add_job(
        job_generate_pending_reports,
        trigger=CronTrigger(hour=10, minute=0),
        id="generate_reports_morning",
        replace_existing=True
    )
    
    scheduler.add_job(
        job_generate_pending_reports,
        trigger=CronTrigger(hour=15, minute=0),
        id="generate_reports_afternoon",
        replace_existing=True
    )
    
    # 每周一凌晨检查配额重置
    scheduler.add_job(
        job_reset_weekly_quota,
        trigger=CronTrigger(day_of_week="mon", hour=0, minute=5),
        id="weekly_quota_check",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.id}: {job.trigger}")


def shutdown_scheduler():
    """关闭调度器"""
    scheduler.shutdown()
    logger.info("Scheduler shutdown")


def add_custom_job(func, trigger, job_id: str):
    """添加自定义任务"""
    scheduler.add_job(func, trigger=trigger, id=job_id, replace_existing=True)


def remove_job(job_id: str):
    """移除任务"""
    scheduler.remove_job(job_id)


def get_jobs():
    """获取所有任务"""
    return [
        {
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        }
        for job in scheduler.get_jobs()
    ]
