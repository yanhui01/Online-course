"""课程服务"""

import asyncio
import traceback

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_adapter
from app.core.crypto import decrypt_optional
from app.core.database import async_session_factory
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.platform_account import PlatformAccount
from app.schemas.course import CourseDetailResponse, CourseResponse, SectionResponse

PLATFORM_LABELS = {"icve": "智慧职教", "zhihuishu": "知到/智慧树", "xuetangx": "学堂在线"}

# 存储正在进行的同步任务状态 {account_id: {"status": "running"|"done"|"error", "message": ""}}
_sync_tasks: dict[str, dict] = {}


def get_sync_status(account_id: str) -> dict | None:
    """查询同步任务状态"""
    return _sync_tasks.get(account_id)


async def sync_courses(
    db: AsyncSession, user_id: str, account_id: str
) -> dict:
    """启动后台同步任务，立即返回"""
    # 1. 验证账号归属
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == account_id, PlatformAccount.user_id == user_id
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台账号不存在")

    # 2. 检查是否已有同步任务正在运行
    existing = _sync_tasks.get(account_id)
    if existing and existing.get("status") == "running":
        return {"message": "同步任务正在进行中", "status": "running"}

    # 3. 启动后台任务
    _sync_tasks[account_id] = {"status": "running", "message": "开始同步..."}

    asyncio.create_task(
        _do_sync(
            user_id=user_id,
            account_id=account_id,
            platform=account.platform,
            account_name=account.account_name,
            encrypted_password=account.encrypted_password,
        )
    )

    return {"message": "同步任务已启动", "status": "running"}


async def _do_sync(
    user_id: str,
    account_id: str,
    platform: str,
    account_name: str,
    encrypted_password: str | None,
):
    """后台执行同步（独立的数据库会话）"""
    password = decrypt_optional(encrypted_password)
    platform_label = PLATFORM_LABELS.get(platform, platform)

    adapter = get_adapter(
        platform=platform,
        username=account_name,
        password=password or "",
        headless=True,
    )

    try:
        # 登录（最多等待 30 秒）
        _sync_tasks[account_id] = {"status": "running", "message": "正在登录..."}
        login_ok = await asyncio.wait_for(adapter.login(), timeout=45)
        if not login_ok:
            _sync_tasks[account_id] = {
                "status": "error",
                "message": f"{platform_label} 登录失败，请检查账号密码",
            }
            return

        # 获取课程（最多等待 30 秒）
        _sync_tasks[account_id] = {"status": "running", "message": "正在获取课程列表..."}
        course_infos = await asyncio.wait_for(adapter.get_courses(), timeout=60)
        if not course_infos:
            _sync_tasks[account_id] = {
                "status": "error",
                "message": f"未在 {platform_label} 上找到课程",
            }
            return

        # 写入数据库
        _sync_tasks[account_id] = {"status": "running", "message": f"正在保存 {len(course_infos)} 门课程..."}
        async with async_session_factory() as db:
            synced_count = 0
            for info in course_infos:
                try:
                    existing = await db.execute(
                        select(Course).where(
                            Course.account_id == account_id,
                            Course.platform_course_id == info.platform_course_id,
                        )
                    )
                    course = existing.scalar_one_or_none()

                    if course is None:
                        course = Course(
                            user_id=user_id,
                            account_id=account_id,
                            platform=platform,
                            platform_course_id=info.platform_course_id,
                            name=info.name,
                            teacher=info.teacher,
                            cover_url=info.cover_url,
                            total_sections=0,
                            completed_sections=0,
                            progress=0.0,
                            status="not_started",
                        )
                        db.add(course)
                        await db.flush()
                        await db.refresh(course)
                    else:
                        course.name = info.name
                        course.teacher = info.teacher
                        await db.flush()

                    # 章节同步在用户查看课程详情时按需触发，不在批量同步时获取

                    synced_count += 1

                except Exception as e:
                    print(f"[sync] 课程 {info.name} 同步失败: {e}")
                    continue

            await db.commit()

        _sync_tasks[account_id] = {
            "status": "done",
            "message": f"同步完成，共 {synced_count} 门课程",
            "count": synced_count,
        }

    except asyncio.TimeoutError:
        _sync_tasks[account_id] = {
            "status": "error",
            "message": "同步超时，请检查网络连接或平台是否可访问",
        }
    except NotImplementedError:
        _sync_tasks[account_id] = {
            "status": "error",
            "message": f"{platform_label} 平台适配器尚未实现",
        }
    except Exception as e:
        traceback.print_exc()
        _sync_tasks[account_id] = {
            "status": "error",
            "message": str(e),
        }
    finally:
        try:
            await adapter.close()
        except Exception:
            pass


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

    sections_result = await db.execute(
        select(CourseSection)
        .where(CourseSection.course_id == course_id)
        .order_by(CourseSection.sort_order)
    )
    sections = sections_result.scalars().all()

    resp = CourseDetailResponse.model_validate(course)
    resp.sections = [SectionResponse.model_validate(s) for s in sections]

    # 章节为空时，异步触发同步
    if not sections:
        account_result = await db.execute(
            select(PlatformAccount).where(PlatformAccount.id == course.account_id)
        )
        account = account_result.scalar_one_or_none()
        if account:
            asyncio.create_task(
                _sync_sections(
                    course_id=course_id,
                    platform=course.platform,
                    platform_course_id=course.platform_course_id,
                    account_name=account.account_name,
                    encrypted_password=account.encrypted_password,
                )
            )

    return resp


async def _sync_sections(
    course_id: str,
    platform: str,
    platform_course_id: str,
    account_name: str,
    encrypted_password: str | None,
):
    """后台同步单个课程的章节"""
    password = decrypt_optional(encrypted_password)
    adapter = get_adapter(platform=platform, username=account_name, password=password or "")

    try:
        await asyncio.wait_for(adapter.login(), timeout=30)
        sections_infos = await asyncio.wait_for(
            adapter.get_sections(platform_course_id), timeout=30
        )

        if sections_infos:
            async with async_session_factory() as db:
                for idx, sec in enumerate(sections_infos):
                    existing = await db.execute(
                        select(CourseSection).where(
                            CourseSection.course_id == course_id,
                            CourseSection.platform_section_id == sec.platform_section_id,
                        )
                    )
                    if existing.scalar_one_or_none() is None:
                        db.add(CourseSection(
                            course_id=course_id,
                            platform_section_id=sec.platform_section_id,
                            name=sec.name,
                            section_type=sec.section_type,
                            duration_minutes=sec.duration_minutes,
                            sort_order=idx,
                            is_completed=sec.is_completed,
                        ))

                # 更新课程章节计数
                count_r = await db.execute(
                    select(func.count()).select_from(CourseSection).where(
                        CourseSection.course_id == course_id
                    )
                )
                course = await db.get(Course, course_id)
                if course:
                    course.total_sections = count_r.scalar() or 0
                await db.commit()
                print(f"[sync_sections] 同步了 {len(sections_infos)} 个章节")

    except asyncio.TimeoutError:
        print(f"[sync_sections] 章节同步超时")
    except NotImplementedError:
        print(f"[sync_sections] 章节同步未实现")
    except Exception as e:
        print(f"[sync_sections] 异常: {e}")
    finally:
        try:
            await adapter.close()
        except Exception:
            pass
