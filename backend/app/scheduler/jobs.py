"""APScheduler 定时任务 — 检查卡死任务、清理过期数据"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.auto_task import AutoTask

engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def check_stuck_tasks():
    """
    检查运行超过 2 小时但没有进度更新的任务（可能卡死）
    """
    async with async_session_factory() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        result = await db.execute(
            select(AutoTask).where(
                AutoTask.status == "running",
                AutoTask.updated_at < cutoff,
            )
        )
        stuck_tasks = result.scalars().all()

        for task in stuck_tasks:
            task.status = "failed"
            task.error_message = "任务疑似卡死（2小时无更新），已自动标记为失败"
            task.completed_at = datetime.now(timezone.utc)

        if stuck_tasks:
            await db.commit()
            print(f"[Scheduler] 标记 {len(stuck_tasks)} 个卡死任务为失败")


async def cleanup_old_data():
    """
    清理 30 天前的已完成/已取消任务
    """
    async with async_session_factory() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            select(AutoTask).where(
                AutoTask.status.in_(["completed", "cancelled"]),
                AutoTask.completed_at < cutoff,
            )
        )
        old_tasks = result.scalars().all()

        for task in old_tasks:
            await db.delete(task)

        if old_tasks:
            await db.commit()
            print(f"[Scheduler] 清理 {len(old_tasks)} 个过期任务")
