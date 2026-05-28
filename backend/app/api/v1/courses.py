"""课程 API 路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.course import CourseDetailResponse, CourseSyncRequest
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["课程"])


@router.post("/sync")
async def sync_courses(
    data: CourseSyncRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """从平台同步课程列表"""
    courses = await course_service.sync_courses(db, user_id, data.account_id)
    return {"items": courses, "total": len(courses)}


@router.get("")
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取课程列表"""
    items, total = await course_service.get_courses(db, user_id, page, page_size)
    return {"items": items, "total": total}


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取课程详情（含章节）"""
    return await course_service.get_course_detail(db, user_id, course_id)
