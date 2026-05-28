"""学堂在线 (xuetangx.com) 平台适配器"""

import asyncio
from typing import AsyncIterator, List, Optional

from playwright.async_api import async_playwright

from app.adapters.base import (
    BasePlatformAdapter,
    CourseInfo,
    ProgressInfo,
    QuizInfo,
    SectionInfo,
)


class XuetangxAdapter(BasePlatformAdapter):
    """学堂在线适配器 — 支持密码登录和手机验证码登录"""

    platform_name = "xuetangx"
    LOGIN_URL = "https://www.xuetangx.com/login"
    SMS_LOGIN_URL = "https://www.xuetangx.com/login#sms"

    def __init__(self, username: str, password: str = "", headless: bool = True):
        super().__init__(username, password, headless)
        self._browser = None
        self._context = None
        self._page = None
        self._sms_code: str | None = None

    # ============================================================
    # 密码登录
    # ============================================================

    async def login(self) -> bool:
        """使用密码登录学堂在线"""
        p = await async_playwright().start()
        browser_type = getattr(p, self._browser_type())
        self._browser = await browser_type.launch(headless=self._headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

        await self._page.goto(self.LOGIN_URL)
        await asyncio.sleep(2)

        # TODO: 填写手机号/邮箱和密码，点击登录按钮
        # await self._page.fill('input[placeholder*="手机号"]', self._username)
        # await self._page.fill('input[type="password"]', self._password)
        # await self._page.click('button:has-text("登录")')
        # await self._page.wait_for_url("**/dashboard")

        raise NotImplementedError("学堂在线密码登录尚未实现")

    # ============================================================
    # 短信验证码登录
    # ============================================================

    async def send_sms_code(self) -> bool:
        """
        打开发送短信验证码页面，点击"获取验证码"按钮
        用户手机会收到验证码，通过前端界面输入后调用 login_with_sms()
        """
        p = await async_playwright().start()
        browser_type = getattr(p, self._browser_type())
        self._browser = await browser_type.launch(headless=self._headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

        await self._page.goto(self.SMS_LOGIN_URL)
        await asyncio.sleep(2)

        # TODO: 填写手机号，点击"发送验证码"
        # await self._page.fill('input[placeholder*="手机号"]', self._username)
        # await self._page.click('button:has-text("获取验证码")')

        raise NotImplementedError("学堂在线短信验证码发送尚未实现")

    async def login_with_sms(self, sms_code: str) -> bool:
        """
        使用已收到的短信验证码完成登录
        send_sms_code() 必须先调用
        """
        if self._page is None:
            raise RuntimeError("请先调用 send_sms_code()")

        # TODO: 填写验证码并完成登录
        # await self._page.fill('input[placeholder*="验证码"]', sms_code)
        # await self._page.click('button:has-text("登录")')
        # await self._page.wait_for_url("**/dashboard")

        raise NotImplementedError("学堂在线短信验证码登录尚未实现")

    async def export_cookies(self) -> str:
        """导出当前 session 的 cookie（JSON 格式）"""
        if self._context is None:
            return ""
        import json
        cookies = await self._context.cookies()
        return json.dumps(cookies)

    # ============================================================
    # 课程相关（Stub）
    # ============================================================

    async def get_courses(self) -> List[CourseInfo]:
        raise NotImplementedError("学堂在线适配器尚未实现")

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        raise NotImplementedError("学堂在线适配器尚未实现")

    async def play_section(
        self, course_id: str, section_id: str
    ) -> AsyncIterator[ProgressInfo]:
        raise NotImplementedError("学堂在线适配器尚未实现")

    async def detect_quiz(self) -> Optional[QuizInfo]:
        raise NotImplementedError("学堂在线适配器尚未实现")

    async def submit_answer(self, answer: str) -> bool:
        raise NotImplementedError("学堂在线适配器尚未实现")

    async def get_course_progress(self, course_id: str) -> float:
        raise NotImplementedError("学堂在线适配器尚未实现")

    async def close(self):
        if self._browser:
            await self._browser.close()

    @staticmethod
    def _browser_type() -> str:
        return "chromium"
