"""任务服务"""

import asyncio
import json

from arq import ArqRedis
from fastapi import HTTPException, status, WebSocket
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auto_task import AutoTask
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.platform_account import PlatformAccount
from app.models.task_log import TaskLog
from app.schemas.task import (
    TaskCreateRequest,
    TaskDetailResponse,
    TaskLogResponse,
    TaskResponse,
)


async def create_task(
    db: AsyncSession,
    arq: ArqRedis | None,
    user_id: str,
    data: TaskCreateRequest,
) -> TaskResponse:
    """创建刷课任务并推送到 ARQ 队列"""
    # 验证课程归属
    course_result = await db.execute(
        select(Course).where(Course.id == data.course_id, Course.user_id == user_id)
    )
    course = course_result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    # 验证账号归属
    account_result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == data.account_id, PlatformAccount.user_id == user_id
        )
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台账号不存在")

    # 检查是否有进行中的同课程任务
    existing = await db.execute(
        select(AutoTask).where(
            AutoTask.user_id == user_id,
            AutoTask.course_id == data.course_id,
            AutoTask.status.in_(["pending", "running", "paused"]),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该课程已有进行中的任务")

    # 创建任务
    task = AutoTask(
        user_id=user_id,
        course_id=data.course_id,
        account_id=data.account_id,
        platform=account.platform,
        max_retries=data.max_retries,
    )
    db.add(task)

    # 统计章节数
    sections_count = await db.execute(
        select(func.count()).select_from(CourseSection).where(
            CourseSection.course_id == data.course_id
        )
    )
    task.total_sections = sections_count.scalar() or 0

    await db.flush()
    await db.refresh(task)

    # 推送到 ARQ 任务队列
    if arq is not None:
        await arq.enqueue_job("execute_task", task.id)

    return TaskResponse.model_validate(task)


async def get_tasks(
    db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[TaskResponse], int]:
    base_query = select(AutoTask).where(AutoTask.user_id == user_id)
    count_query = (
        select(func.count()).select_from(AutoTask).where(AutoTask.user_id == user_id)
    )

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        base_query.order_by(AutoTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tasks = result.scalars().all()
    return [TaskResponse.model_validate(t) for t in tasks], total


async def get_task_detail(db: AsyncSession, user_id: str, task_id: str) -> TaskDetailResponse:
    result = await db.execute(
        select(AutoTask).where(AutoTask.id == task_id, AutoTask.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 获取日志
    logs_result = await db.execute(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.created_at.desc())
        .limit(100)
    )
    logs = logs_result.scalars().all()

    resp = TaskDetailResponse.model_validate(task)
    resp.logs = [TaskLogResponse.model_validate(log) for log in logs]
    return resp


async def pause_task(db: AsyncSession, user_id: str, task_id: str):
    task = await _get_owned_task(db, user_id, task_id)
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能暂停进行中的任务")
    task.status = "paused"
    await db.commit()


async def resume_task(
    db: AsyncSession, arq: ArqRedis | None, user_id: str, task_id: str
) -> TaskResponse:
    task = await _get_owned_task(db, user_id, task_id)
    if task.status != "paused":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能恢复已暂停的任务")
    task.status = "pending"
    task.retry_count = 0
    await db.commit()

    if arq is not None:
        await arq.enqueue_job("execute_task", task.id)

    return TaskResponse.model_validate(task)


async def cancel_task(db: AsyncSession, user_id: str, task_id: str):
    task = await _get_owned_task(db, user_id, task_id)
    if task.status in ("completed", "cancelled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务已完成或已取消")
    task.status = "cancelled"
    await db.commit()


async def _get_owned_task(db: AsyncSession, user_id: str, task_id: str) -> AutoTask:
    result = await db.execute(
        select(AutoTask).where(AutoTask.id == task_id, AutoTask.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task
