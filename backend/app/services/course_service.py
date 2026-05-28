"""课程服务"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.platform_account import PlatformAccount
from app.schemas.course import CourseDetailResponse, CourseResponse, SectionResponse


async def sync_courses(db: AsyncSession, user_id: str, account_id: str) -> list[CourseResponse]:
    """从平台同步课程列表到本地数据库"""
    # 验证账号归属
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == account_id, PlatformAccount.user_id == user_id
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台账号不存在")

    # 解密密码
    password = decrypt(account.encrypted_password)

    # TODO: 调用适配器同步课程
    # adapter = get_adapter(account.platform, account.account_name, password)
    # await adapter.login()
    # courses = await adapter.get_courses()
    # await adapter.close()
    #
    # 目前返回占位数据，提示用户适配器尚未实现

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{account.platform} 平台适配器尚未实现，敬请期待",
    )


async def get_courses(
    db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[CourseResponse], int]:
    base_query = select(Course).where(Course.user_id == user_id)
    count_query = select(func.count()).select_from(Course).where(Course.user_id == user_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        base_query.order_by(Course.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    courses = result.scalars().all()
    return [CourseResponse.model_validate(c) for c in courses], total


async def get_course_detail(db: AsyncSession, user_id: str, course_id: str) -> CourseDetailResponse:
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在")

    # 获取章节列表
    sections_result = await db.execute(
        select(CourseSection)
        .where(CourseSection.course_id == course_id)
        .order_by(CourseSection.sort_order)
    )
    sections = sections_result.scalars().all()

    resp = CourseDetailResponse.model_validate(course)
    resp.sections = [SectionResponse.model_validate(s) for s in sections]
    return resp
