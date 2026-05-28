"""知到/智慧树 (zhihuishu.com) 平台适配器 — Playwright 浏览器自动化"""

import asyncio
import os
import re
from typing import AsyncIterator, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright._impl._errors import TimeoutError as PlaywrightTimeout

from app.adapters.base import (
    BasePlatformAdapter,
    CourseInfo,
    ProgressInfo,
    QuizInfo,
    SectionInfo,
)
from app.utils.human_like import human_wait, random_delay


class ZhihuishuAdapter(BasePlatformAdapter):
    platform_name = "zhihuishu"

    LOGIN_URLS = [
        "https://passport.zhihuishu.com/login",
        "https://online.zhihuishu.com/",
    ]
    BASE_URL = "https://online.zhihuishu.com"

    def __init__(self, username: str, password: str, headless: bool = True):
        super().__init__(username, password, headless)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._logged_in = False

    async def login(self) -> bool:
        """登录知到/智慧树"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        self._context = await self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )

        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [{ name: 'Chrome PDF Plugin' }, { name: 'Chrome PDF Viewer' }]
            });
            window.chrome = { runtime: {} };
        """)

        self._page = await self._context.new_page()
        os.makedirs("screenshots", exist_ok=True)

        for url in self.LOGIN_URLS:
            try:
                print(f"[ZHIHUISHU] 尝试打开: {url}")
                await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(3)

                await self._page.screenshot(path=f"screenshots/zhihuishu_page_{self._username}.png")

                page_text = (await self._page.text_content("body") or "")[:2000]
                print(f"[ZHIHUISHU] 页面预览: {page_text[:200]}...")

                if await self._try_login():
                    self._logged_in = True
                    return True

            except PlaywrightTimeout:
                print(f"[ZHIHUISHU] {url} 加载超时")
                continue
            except Exception as e:
                print(f"[ZHIHUISHU] {url} 异常: {e}")
                continue

        return False

    async def _try_login(self) -> bool:
        """在当前页面尝试登录"""
        # 知到登录页：手机号 + 密码，或者学号 + 密码
        # 查找所有 input
        all_inputs = await self._page.locator("input").all()
        print(f"[ZHIHUISHU] 找到 {len(all_inputs)} 个 input")

        for i, inp in enumerate(all_inputs):
            try:
                t = (await inp.get_attribute("type") or "").lower()
                ph = (await inp.get_attribute("placeholder") or "")
                nm = (await inp.get_attribute("name") or "")
                print(f"  input[{i}]: type={t}, name={nm}, placeholder={ph}")
            except Exception:
                pass

        # 填写用户名
        username_filled = False
        for inp in all_inputs:
            try:
                t = (await inp.get_attribute("type") or "").lower()
                ph = (await inp.get_attribute("placeholder") or "").lower()
                nm = (await inp.get_attribute("name") or "").lower()
                if t in ("text", "tel", "") and any(
                    kw in ph + nm for kw in ["手机", "mobile", "phone", "学号", "账号", "account", "username", "用户名"]
                ):
                    await inp.click()
                    await inp.fill(self._username)
                    print(f"[ZHIHUISHU] 填写用户名到 placeholder={ph}")
                    username_filled = True
                    break
            except Exception:
                continue

        if not username_filled:
            for inp in all_inputs:
                try:
                    t = (await inp.get_attribute("type") or "").lower()
                    if t in ("text", "tel", ""):
                        await inp.click()
                        await inp.fill(self._username)
                        print("[ZHIHUISHU] 降级填写用户名")
                        username_filled = True
                        break
                except Exception:
                    continue

        if not username_filled:
            return False

        await human_wait(300, 150)

        # 填写密码
        password_filled = False
        for inp in all_inputs:
            try:
                if (await inp.get_attribute("type") or "").lower() == "password":
                    await inp.click()
                    await inp.fill(self._password)
                    print("[ZHIHUISHU] 填写密码")
                    password_filled = True
                    break
            except Exception:
                continue

        if not password_filled:
            return False

        await human_wait(500, 200)

        # 提交登录
        submit_clicked = False
        for selector in [
            'button:has-text("登录")', 'button:has-text("登 录")',
            'button[type="submit"]', 'a:has-text("登录")',
            '[class*="login-btn"]', '[class*="submit"]', 'button',
        ]:
            try:
                btn = self._page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    print(f"[ZHIHUISHU] 点击: {(await btn.text_content()).strip()[:20]}")
                    await btn.click()
                    submit_clicked = True
                    break
            except Exception:
                continue

        if not submit_clicked:
            await self._page.keyboard.press("Enter")

        await asyncio.sleep(4)
        await self._page.screenshot(path=f"screenshots/zhihuishu_after_login_{self._username}.png")

        current_url = self._page.url
        body_text = (await self._page.text_content("body") or "")[:500]

        # 检查错误
        for kw in ["密码错误", "账号不存在", "验证码", "请正确输入", "登录失败"]:
            if kw in body_text:
                print(f"[ZHIHUISHU] 登录失败: {kw}")
                return False

        # 成功标志：进入了在线学习页面
        success_indicators = ["退出", "我的课程", "课程列表", "在线学堂", "个人中心", "online"]
        if any(kw in body_text for kw in success_indicators):
            print(f"[ZHIHUISHU] 登录成功: {current_url}")
            return True

        if "online" in current_url or "zhihuishu" in current_url:
            print(f"[ZHIHUISHU] URL 变化，假定成功: {current_url}")
            return True

        print(f"[ZHIHUISHU] 状态不明，URL={current_url}")
        return "登录" not in body_text[:200]

    async def get_courses(self) -> List[CourseInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        courses = []
        try:
            # 导航到课程列表
            course_urls = [
                "https://online.zhihuishu.com/online/student/courseList",
                "https://online.zhihuishu.com/online/",
            ]
            for url in course_urls:
                try:
                    await self._page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(3)
                    body = (await self._page.text_content("body") or "")[:1000]
                    if any(kw in body for kw in ["课程", "course", "学习", "在线"]):
                        break
                except Exception:
                    continue

            await self._page.screenshot(path=f"screenshots/zhihuishu_courses_{self._username}.png")

            # JS 批量提取课程
            courses_raw = await self._page.evaluate("""
                () => {
                    const courses = [];
                    const cards = document.querySelectorAll(
                        '[class*="course"]:not([class*="nav"]):not([class*="header"]):not([class*="footer"]), ' +
                        '.el-card, [class*="card"], li[class*="item"]'
                    );
                    cards.forEach((card, idx) => {
                        const text = (card.innerText || card.textContent || '').trim();
                        const lines = text.split('\\n').filter(l => l.trim());
                        if (!text || text.length < 4) return;

                        let name = '';
                        const h3 = card.querySelector('h3, h4, h5, [class*="title"], [class*="name"]');
                        if (h3) name = h3.innerText.trim();
                        if (!name && lines.length > 0) {
                            for (const l of lines) {
                                if (l.length >= 4 && !/进行|已学|完成|继续|开始|进入|学习/.test(l)) {
                                    name = l; break;
                                }
                            }
                            if (!name) name = lines[0] || '';
                        }

                        let teacher = '';
                        const tEl = card.querySelector('[class*="teacher"], [class*="author"]');
                        if (tEl) teacher = tEl.innerText.trim();
                        if (!teacher && lines.length >= 2) {
                            for (const l of lines.slice(1)) {
                                if (/老师|教师|教授|学院|大学/.test(l)) { teacher = l; break; }
                            }
                        }

                        let courseId = 'zhihuishu_' + idx;
                        const link = card.querySelector('a[href]');
                        if (link) {
                            const href = link.getAttribute('href') || '';
                            const m = href.match(/(?:courseId|id|recruitId)=([^&"']+)/);
                            if (m) courseId = m[1];
                        }

                        let coverUrl = '';
                        const img = card.querySelector('img');
                        if (img) coverUrl = img.getAttribute('src') || '';

                        courses.push({ name, teacher, courseId, coverUrl });
                    });
                    // 去重
                    const seen = new Set();
                    return courses.filter(c => {
                        const key = c.name + c.teacher;
                        if (seen.has(key)) return false;
                        seen.add(key);
                        return true;
                    });
                }
            """)

            for item in courses_raw:
                name = (item.get("name") or "").strip()
                if not name or len(name) < 2:
                    continue
                courses.append(CourseInfo(
                    platform_course_id=item.get("courseId", f"zhihuishu_{len(courses)}"),
                    name=name[:200],
                    teacher=(item.get("teacher") or "").strip(),
                    cover_url=item.get("coverUrl") or "",
                ))
                print(f"[ZHIHUISHU] {name[:60]} | {(item.get('teacher') or '')[:30]}")

            print(f"[ZHIHUISHU] 共解析 {len(courses)} 门课程")
            return courses

        except Exception as e:
            print(f"[ZHIHUISHU] 获取课程异常: {e}")
            import traceback; traceback.print_exc()
            return courses

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")
        # TODO: 实现章节获取
        raise NotImplementedError("知到章节获取尚未实现")

    async def play_section(self, course_id: str, section_id: str) -> AsyncIterator[ProgressInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")
        raise NotImplementedError("知到视频播放尚未实现")

    async def detect_quiz(self) -> Optional[QuizInfo]:
        return None

    async def submit_answer(self, answer: str) -> bool:
        return False

    async def get_course_progress(self, course_id: str) -> float:
        return 0.0

    # ============================================================
    # 扫码登录
    # ============================================================

    async def get_qrcode(self) -> str | None:
        import base64, os
        os.makedirs("screenshots", exist_ok=True)
        try:
            if not self._playwright:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self._headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                )
                self._context = await self._browser.new_context(
                    viewport={"width": 1366, "height": 768}, locale="zh-CN",
                )
                self._page = await self._context.new_page()

            await self._page.goto("https://passport.zhihuishu.com/login", wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(3)

            for tab_text in ["扫码登录", "微信登录", "二维码"]:
                try:
                    tab = self._page.locator(f'text="{tab_text}"').first
                    if await tab.is_visible(timeout=1000):
                        await tab.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue

            await self._page.screenshot(path=f"screenshots/zhihuishu_qrcode_{self._username}.png")
            with open(f"screenshots/zhihuishu_qrcode_{self._username}.png", "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return None

    async def wait_qrcode_scan(self, timeout: int = 120) -> bool:
        if not self._page:
            return False
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < timeout:
            await asyncio.sleep(2)
            try:
                body = (await self._page.text_content("body") or "")[:500]
                if any(kw in body for kw in ["退出", "我的课程", "课程列表", "在线学堂", "个人中心"]):
                    self._logged_in = True
                    return True
            except Exception:
                continue
        return False

    async def close(self):
        try:
            if self._context: await self._context.close()
            if self._browser: await self._browser.close()
            if self._playwright: await self._playwright.stop()
        except Exception:
            pass
