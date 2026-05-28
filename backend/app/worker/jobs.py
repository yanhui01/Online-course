"""ARQ Worker 任务函数 — Playwright 浏览器自动化执行入口"""

import asyncio
import json
from datetime import datetime, timezone

import playwright
from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.auto_task import AutoTask
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.task_log import TaskLog
from app.adapters.factory import get_adapter
from app.core.crypto import decrypt
from app.models.platform_account import PlatformAccount

engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def execute_task(ctx, task_id: str):
    """
    核心刷课任务
    ctx: ARQ job context (包含 Redis 等)
    task_id: auto_tasks 表的主键 ID
    """
    async with async_session_factory() as db:
        # 加载任务
        result = await db.execute(select(AutoTask).where(AutoTask.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            return

        # 更新状态为 running
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        await _add_log(db, task_id, "INFO", "任务开始执行")

        try:
            # 加载课程信息
            course_result = await db.execute(select(Course).where(Course.id == task.course_id))
            course = course_result.scalar_one_or_none()
            if course is None:
                raise ValueError("课程不存在")

            # 加载平台账号
            account_result = await db.execute(
                select(PlatformAccount).where(PlatformAccount.id == task.account_id)
            )
            account = account_result.scalar_one_or_none()
            if account is None:
                raise ValueError("平台账号不存在")

            password = decrypt(account.encrypted_password)
            await _add_log(db, task_id, "INFO", f"开始登录 {account.platform} 平台...")

            # 创建适配器并执行
            adapter = get_adapter(
                account.platform,
                account.account_name,
                password,
                headless=settings.PLAYWRIGHT_HEADLESS,
            )

            login_ok = await adapter.login()
            if not login_ok:
                raise RuntimeError("登录失败，请检查账号密码")

            await _add_log(db, task_id, "INFO", "登录成功，开始刷课")

            # 获取未完成的章节
            sections_result = await db.execute(
                select(CourseSection)
                .where(CourseSection.course_id == task.course_id)
                .order_by(CourseSection.sort_order)
            )
            sections = sections_result.scalars().all()

            pending_sections = [s for s in sections if not s.is_completed]
            task.total_sections = len(sections)
            task.completed_sections = len(sections) - len(pending_sections)
            await db.commit()

            for section in pending_sections:
                # 检查任务状态（支持外部暂停/取消）
                await db.refresh(task)
                if task.status in ("paused", "cancelled"):
                    await _add_log(db, task_id, "INFO", f"任务被{task.status}，停止执行")
                    break

                await _add_log(db, task_id, "INFO", f"正在处理: {section.name}")
                task.current_section_id = section.id
                await db.commit()

                try:
                    # 播放章节
                    async for progress in adapter.play_section(
                        course.platform_course_id, section.platform_section_id
                    ):
                        task.progress = progress.percentage
                        await db.commit()

                        # 通过 Redis pub/sub 推送到 WebSocket
                        await ctx["redis"].publish(
                            f"task:{task_id}:progress",
                            json.dumps({
                                "section_name": progress.section_name,
                                "percentage": progress.percentage,
                                "message": progress.message,
                            }),
                        )

                    # 检测题目
                    quiz = await adapter.detect_quiz()
                    if quiz:
                        await _add_log(db, task_id, "INFO", f"检测到题目: {quiz.question_text[:50]}...")
                        # TODO: 调用题库搜索答案
                        # answer = await question_bank_service.search(quiz.question_text)
                        # if answer:
                        #     await adapter.submit_answer(answer)
                        #     await _add_log(db, task_id, "INFO", "已自动答题")

                    # 标记章节完成
                    section.is_completed = True
                    section.completed_at = datetime.now(timezone.utc)
                    task.completed_sections += 1
                    await db.commit()

                    await _add_log(db, task_id, "INFO", f"完成: {section.name}")

                except Exception as e:
                    await _add_log(db, task_id, "ERROR", f"章节失败: {str(e)}")
                    task.retry_count += 1
                    if task.retry_count >= task.max_retries:
                        raise RuntimeError(f"达到最大重试次数 {task.max_retries}")

            # 所有章节完成
            await adapter.close()
            task.status = "completed"
            task.progress = 100.0
            task.completed_at = datetime.now(timezone.utc)

            # 更新课程进度
            course.progress = 100.0
            course.status = "completed"
            course.completed_sections = len(sections)

            await db.commit()
            await _add_log(db, task_id, "INFO", "任务完成!")

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            await db.commit()
            await _add_log(db, task_id, "ERROR", f"任务失败: {str(e)}")


async def _add_log(db: AsyncSession, task_id: str, level: str, message: str):
    """添加任务日志"""
    log = TaskLog(task_id=task_id, level=level, message=message)
    db.add(log)
    await db.commit()
