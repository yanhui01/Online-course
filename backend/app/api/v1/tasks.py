"""任务 API 路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user_id
from app.schemas.task import TaskCreateRequest, TaskDetailResponse
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["刷课任务"])


@router.post("", status_code=201)
async def create_task(
    data: TaskCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """创建刷课任务"""
    arq = None  # TODO: 注入 ARQ Redis 连接
    return await task_service.create_task(db, arq, user_id, data)


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    items, total = await task_service.get_tasks(db, user_id, page, page_size)
    return {"items": items, "total": total}


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取任务详情（含日志）"""
    return await task_service.get_task_detail(db, user_id, task_id)


@router.post("/{task_id}/pause")
async def pause_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """暂停任务"""
    await task_service.pause_task(db, user_id, task_id)
    return {"message": "任务已暂停"}


@router.post("/{task_id}/resume")
async def resume_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """恢复任务"""
    arq = None  # TODO: 注入 ARQ Redis 连接
    return await task_service.resume_task(db, arq, user_id, task_id)


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """取消任务"""
    await task_service.cancel_task(db, user_id, task_id)
    return {"message": "任务已取消"}
