import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

logger = logging.getLogger(__name__)

# 创建调度器实例
# 使用内存存储（服务重启后任务会丢失，如需持久化可改用 SQLAlchemyJobStore）
scheduler = AsyncIOScheduler(
    jobstores={'default': MemoryJobStore()},
    timezone='Asia/Shanghai',  # 设置时区
    coalesce=True,  # 如果任务因某种原因导致多次未执行，合并为一次
    max_instances=3,  # 每个任务最多同时运行的实例数
)


def init_scheduler(app: FastAPI) -> None:
    """
    初始化调度器，绑定到 FastAPI 应用生命周期

    Args:
        app: FastAPI 应用实例
    """

    @app.on_event("startup")
    async def startup_event() -> None:
        """应用启动时启动调度器"""
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ 定时任务调度器已启动")
            register_jobs()
        else:
            logger.warning("⚠️ 调度器已在运行中")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """应用关闭时关闭调度器"""
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✅ 定时任务调度器已关闭")


def register_jobs() -> None:
    """
    注册所有定时任务
    在这里添加你的定时任务
    """
    from app.scheduler.jobs import example_job

    # 示例任务 1：每天凌晨2点执行
    scheduler.add_job(
        example_job.daily_task,
        CronTrigger(hour=2, minute=0),  # 每天凌晨2点
        id='daily_task',
        name='每日定时任务',
        replace_existing=True,  # 如果任务已存在则替换
        misfire_grace_time=300,  # 任务错过执行时间后的容忍时间（秒）
    )

    # 示例任务 2：每5分钟执行一次（用于测试，生产环境可删除或调整）
    scheduler.add_job(
        example_job.interval_task,
        IntervalTrigger(minutes=5),  # 每5分钟
        id='interval_task',
        name='间隔任务（每5分钟）',
        replace_existing=True,
    )

    # 示例任务 3：每周一早上9点执行
    scheduler.add_job(
        example_job.weekly_task,
        CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='weekly_task',
        name='每周任务（周一9点）',
        replace_existing=True,
    )

    logger.info(f"✅ 已注册 {len(scheduler.get_jobs())} 个定时任务")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.id}: {job.name} (下次执行: {job.next_run_time})")

