"""学堂在线 (xuetangx.com) 平台适配器 — Playwright 浏览器自动化"""

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


class XuetangxAdapter(BasePlatformAdapter):
    platform_name = "xuetangx"

    LOGIN_URLS = [
        "https://www.xuetangx.com/",       # 首页弹窗登录（更快）
        "https://www.xuetangx.com/login",   # 独立登录页（备用）
    ]
    BASE_URL = "https://www.xuetangx.com"

    def __init__(self, username: str, password: str = "", headless: bool = True):
        super().__init__(username, password, headless)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._logged_in = False

    async def login(self) -> bool:
        """登录学堂在线（密码方式）"""
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
            window.chrome = { runtime: {} };
        """)

        self._page = await self._context.new_page()
        os.makedirs("screenshots", exist_ok=True)

        for url in self.LOGIN_URLS:
            try:
                print(f"[XUETANGX] 尝试打开: {url}")
                await self._page.goto(url, wait_until="domcontentloaded", timeout=8000)
                await asyncio.sleep(3)

                await self._page.screenshot(path=f"screenshots/xuetangx_page_{self._username}.png")

                page_text = (await self._page.text_content("body") or "")[:2000]
                print(f"[XUETANGX] 页面预览: {page_text[:200]}...")

                if await self._try_login():
                    self._logged_in = True
                    return True

            except PlaywrightTimeout:
                print(f"[XUETANGX] {url} 加载超时")
                continue
            except Exception as e:
                print(f"[XUETANGX] {url} 异常: {e}")
                continue

        return False

    async def _try_login(self) -> bool:
        """在当前页面尝试密码登录"""
        body_text = (await self._page.text_content("body") or "")[:1000]

        # 判断当前是首页还是登录页
        is_homepage = any(kw in body_text for kw in ["首页", "合作院校", "全部课程", "精品课程"])
        is_login_page = any(kw in body_text for kw in ["密码登录", "短信登录", "验证码登录"])

        # 如果是首页，点击登录按钮打开弹窗
        if is_homepage and not is_login_page:
            print("[XUETANGX] 当前为首页，查找登录入口...")
            for btn_text in ["登录", "登录/注册", "登 录", "Sign in"]:
                try:
                    btn = self._page.locator(f'text="{btn_text}"').first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        print(f"[XUETANGX] 点击了登录入口")
                        await asyncio.sleep(3)
                        break
                except Exception:
                    continue

            # 检查是否弹出了登录弹窗
            body_text = (await self._page.text_content("body") or "")[:1000]

        # 优先切换到"密码登录"tab
        for tab_text in ["密码登录", "密码", "账号密码"]:
            try:
                tab = self._page.locator(f'text="{tab_text}"').first
                if await tab.is_visible(timeout=500):
                    await tab.click()
                    await asyncio.sleep(1)
                    print(f"[XUETANGX] 切换到密码登录 tab")
                    break
            except Exception:
                continue

        # 截图看登录弹窗
        await self._page.screenshot(path=f"screenshots/xuetangx_login_modal_{self._username}.png")

        # 重新获取输入框（tab切换后SMS字段可能隐藏）
        all_inputs = await self._page.locator("input").all()
        print(f"[XUETANGX] 找到 {len(all_inputs)} 个 input")

        for i, inp in enumerate(all_inputs):
            try:
                t = (await inp.get_attribute("type") or "").lower()
                ph = (await inp.get_attribute("placeholder") or "")
                nm = (await inp.get_attribute("name") or "")
                visible = await inp.is_visible()
                print(f"  input[{i}]: type={t}, name={nm}, placeholder={ph}, visible={visible}")
            except Exception:
                pass

        # 填写用户名：只找可见的、非验证码的手机号输入框
        username_filled = False
        for inp in all_inputs:
            try:
                if not await inp.is_visible():
                    continue
                t = (await inp.get_attribute("type") or "").lower()
                ph = (await inp.get_attribute("placeholder") or "").lower()
                nm = (await inp.get_attribute("name") or "").lower()
                if any(kw in ph for kw in ["验证码", "code", "sms"]):
                    continue
                if t in ("text", "tel", "email", "") and any(
                    kw in ph + nm for kw in ["手机", "mobile", "phone", "邮箱", "email", "账号", "account", "username"]
                ):
                    await inp.click()
                    await inp.fill(self._username)
                    print(f"[XUETANGX] 填写用户名: placeholder={ph}")
                    username_filled = True
                    break
            except Exception:
                continue

        if not username_filled:
            for inp in all_inputs:
                try:
                    if not await inp.is_visible():
                        continue
                    t = (await inp.get_attribute("type") or "").lower()
                    ph = (await inp.get_attribute("placeholder") or "").lower()
                    if any(kw in ph for kw in ["搜索", "search", "验证码", "code", "sms", "邮箱"]):
                        continue
                    if t in ("text", "tel", ""):
                        await inp.click()
                        await inp.fill(self._username)
                        print(f"[XUETANGX] 降级填写: placeholder={ph}")
                        username_filled = True
                        break
                except Exception:
                    continue

        if not username_filled:
            print("[XUETANGX] 未找到用户名输入框")
            return False

        await human_wait(300, 150)

        # 填写密码：只找可见的密码输入框
        password_filled = False
        for inp in all_inputs:
            try:
                if not await inp.is_visible():
                    continue
                if (await inp.get_attribute("type") or "").lower() == "password":
                    ph = (await inp.get_attribute("placeholder") or "").lower()
                    if "确认" in ph:
                        continue
                    await inp.click()
                    await inp.fill(self._password)
                    print(f"[XUETANGX] 填写密码: placeholder={ph}")
                    password_filled = True
                    break
            except Exception:
                continue

        if not password_filled:
            # 学堂在线可能是分步登录：先填邮箱/手机号 → 点"下一步" → 再输密码
            print("[XUETANGX] 未找到密码框，尝试分步登录...")
            next_clicked = False
            for selector in [
                'button:has-text("下一步")', 'button:has-text("继续")',
                'button:has-text("Next")', 'button[type="submit"]', 'button',
            ]:
                try:
                    btn = self._page.locator(selector).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        next_clicked = True
                        print(f"[XUETANGX] 点击下一步")
                        break
                except Exception:
                    continue
            if not next_clicked:
                await self._page.keyboard.press("Enter")

            await asyncio.sleep(3)

            # 重新获取输入框（密码框应该可见了）
            all_inputs = await self._page.locator("input").all()
            for inp in all_inputs:
                try:
                    if not await inp.is_visible():
                        continue
                    if (await inp.get_attribute("type") or "").lower() == "password":
                        ph = (await inp.get_attribute("placeholder") or "").lower()
                        if "确认" in ph:
                            continue
                        await inp.click()
                        await inp.fill(self._password)
                        print(f"[XUETANGX] 填写密码: {ph}")
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
            'button[type="submit"]', '[class*="login-btn"]',
            '[class*="submit"]', 'button',
        ]:
            try:
                btn = self._page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    print(f"[XUETANGX] 点击: {(await btn.text_content()).strip()[:20]}")
                    await btn.click()
                    submit_clicked = True
                    break
            except Exception:
                continue

        if not submit_clicked:
            await self._page.keyboard.press("Enter")

        await asyncio.sleep(4)
        await self._page.screenshot(path=f"screenshots/xuetangx_after_login_{self._username}.png")

        current_url = self._page.url
        body_text = (await self._page.text_content("body") or "")[:800]

        print(f"[XUETANGX] 登录后 URL={current_url}")
        print(f"[XUETANGX] 登录后 body预览={body_text[:200]}")

        for kw in ["密码错误", "账号不存在", "验证码", "登录失败", "密码不正确",
                     "账号或密码", "用户名或密码", "请重新输入", "incorrect",
                     "invalid", "wrong password"]:
            if kw.lower() in body_text.lower():
                print(f"[XUETANGX] 登录失败: 检测到 '{kw}'")
                return False

        # 检查是否还在登录弹窗（说明登录没成功）
        if any(kw in body_text[:300] for kw in ["手机号登录", "短信登录", "密码登录"]):
            print("[XUETANGX] 仍在登录弹窗中，登录可能失败")
            return False

        success_indicators = [
            "退出", "我的课程", "课程列表", "个人中心", "dashboard",
            "学习中心", "我的主页", "已登录",
        ]
        if any(kw in body_text for kw in success_indicators):
            print(f"[XUETANGX] 登录成功: {current_url}")
            return True

        if any(domain in current_url for domain in ["xuetangx.com", "next.xuetangx.com"]):
            if "login" not in current_url.lower():
                print(f"[XUETANGX] 已跳转到非登录页，假定成功: {current_url}")
                return True
            else:
                # 还在登录页，检查是否有错误
                return False

        return "登录" not in body_text[:200]

    async def send_sms_code(self) -> bool:
        """发送短信验证码 — 打开首页弹窗 → 切短信tab → 填手机号 → 点发送"""
        if not self._playwright:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1366, "height": 768},
                locale="zh-CN",
            )
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                window.chrome = { runtime: {} };
            """)
            self._page = await self._context.new_page()
        os.makedirs("screenshots", exist_ok=True)

        try:
            # 1. 打开首页
            await self._page.goto("https://www.xuetangx.com/", wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(2)

            # 2. 点击登录按钮打开弹窗
            for btn_text in ["登录", "登录/注册"]:
                try:
                    btn = self._page.locator(f'text="{btn_text}"').first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        print(f"[XUETANGX-SMS] 点击了登录入口")
                        break
                except Exception:
                    continue
            await asyncio.sleep(3)

            # 3. 切换到短信验证码登录 tab
            for tab_text in ["短信登录", "验证码登录", "手机验证码", "短信"]:
                try:
                    tab = self._page.locator(f'text="{tab_text}"').first
                    if await tab.is_visible(timeout=500):
                        await tab.click()
                        await asyncio.sleep(1)
                        print(f"[XUETANGX-SMS] 切换到短信登录 tab")
                        break
                except Exception:
                    continue

            await self._page.screenshot(path=f"screenshots/xuetangx_sms_{self._username}.png")

            # 4. 填写手机号（只找可见的）
            all_inputs = await self._page.locator("input").all()
            phone_filled = False
            for inp in all_inputs:
                try:
                    if not await inp.is_visible():
                        continue
                    ph = (await inp.get_attribute("placeholder") or "").lower()
                    if any(kw in ph for kw in ["手机", "mobile", "phone"]):
                        await inp.click()
                        await inp.fill(self._username)
                        print(f"[XUETANGX-SMS] 填写手机号: {self._username}")
                        phone_filled = True
                        break
                except Exception:
                    continue

            if not phone_filled:
                print("[XUETANGX-SMS] 未找到可见的手机号输入框")
                return False

            await human_wait(200, 100)

            # 5. 点击发送验证码
            for btn_text in ["获取验证码", "发送验证码", "获取", "发送"]:
                try:
                    btn = self._page.locator(f'button:has-text("{btn_text}")').first
                    if not await btn.is_visible(timeout=500):
                        btn = self._page.locator(f'text="{btn_text}"').first
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                        print(f"[XUETANGX-SMS] 已点击发送验证码")
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            print(f"[XUETANGX-SMS] 发送短信失败: {e}")
            return False

    async def login_with_sms(self, sms_code: str) -> bool:
        """输入短信验证码完成登录"""
        if not self._page:
            raise RuntimeError("请先调用 send_sms_code()")

        # 填写验证码（只找可见的）
        all_inputs = await self._page.locator("input").all()
        for inp in all_inputs:
            try:
                if not await inp.is_visible():
                    continue
                ph = (await inp.get_attribute("placeholder") or "").lower()
                if any(kw in ph for kw in ["验证码", "code", "sms"]):
                    await inp.click()
                    await inp.fill(sms_code)
                    print(f"[XUETANGX-SMS] 填写验证码")
                    break
            except Exception:
                continue

        # 点登录按钮
        for selector in ['button:has-text("登录")', 'button[type="submit"]', 'button']:
            try:
                btn = self._page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    break
            except Exception:
                continue

        await asyncio.sleep(4)
        await self._page.screenshot(path=f"screenshots/xuetangx_sms_result_{self._username}.png")

        body_text = (await self._page.text_content("body") or "")[:500]
        if "验证码错误" in body_text or "验证码不正确" in body_text:
            print("[XUETANGX-SMS] 验证码错误")
            return False

        # 检查登录成功
        current_url = self._page.url
        success_kw = ["退出", "我的课程", "个人中心", "学习中心", "已登录"]
        if any(kw in body_text for kw in success_kw) or ("xuetangx" in current_url and "login" not in current_url):
            self._logged_in = True
            print(f"[XUETANGX-SMS] 短信登录成功! URL={current_url}")
            return True

        # 没有明显错误就乐观认为成功
        self._logged_in = True
        return True

    async def export_cookies(self) -> str:
        if self._context:
            import json
            return json.dumps(await self._context.cookies())
        return ""

    async def get_courses(self) -> List[CourseInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        courses = []
        try:
            # 学堂在线的课程入口：
            # 1. 个人主页(需要先切过去)
            # 2. 学习中心
            course_urls = [
                self._page.url,  # 保持登录后的当前页面（通常就是个人主页或学习中心）
                "https://www.xuetangx.com/dashboard",
                "https://www.xuetangx.com/student/dashboard",
                "https://www.xuetangx.com/courses",
                "https://www.xuetangx.com/my-courses",
                "https://next.xuetangx.com/courses",
                "https://next.xuetangx.com/dashboard",
            ]
            for url in course_urls:
                try:
                    await self._page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(4)  # SPA 渲染
                    body_len = len((await self._page.text_content("body") or ""))
                    print(f"[XUETANGX] 课程页 {url} body长度={body_len}")
                    if body_len > 500:
                        break
                except Exception:
                    continue

            await self._page.screenshot(path=f"screenshots/xuetangx_courses_{self._username}.png")

            # 诊断：打印页面上的可见文本
            body_text = (await self._page.text_content("body") or "")[:800]
            print(f"[XUETANGX] 页面文本: {body_text[:300]}...")

            # JS 批量提取课程（使用更多选择器）
            courses_raw = await self._page.evaluate("""
                () => {
                    const courses = [];
                    // 学堂在线可能使用的 class 名称
                    let cards = document.querySelectorAll(
                        '.course-card, .course-item, .courseItem, ' +
                        '[class*="course-card"], [class*="courseCard"], ' +
                        '[class*="course-item"], [class*="courseItem"], ' +
                        '.card, [class*="card"], ' +
                        'a[href*="/course/"], a[href*="/learn/"], ' +
                        '[class*="list"] > div, [class*="grid"] > div'
                    );
                    console.log('course cards found:', cards.length);
                    cards.forEach((card, idx) => {
                        const text = (card.innerText || card.textContent || '').trim();
                        const lines = text.split('\\n').filter(l => l.trim());
                        if (!text || text.length < 4) return;

                        let name = '';
                        const titleEl = card.querySelector(
                            'h3, h4, h5, h2, .title, .name, [class*="title"], [class*="name"], strong, b'
                        );
                        if (titleEl) name = titleEl.innerText.trim();
                        if (!name && lines.length > 0) {
                            for (const l of lines) {
                                if (l.length >= 4 && !/进行|已学|完成|继续|进入|免费|报名/.test(l)) {
                                    name = l; break;
                                }
                            }
                            if (!name) name = lines[0] || '';
                        }

                        let teacher = '';
                        const tEl = card.querySelector(
                            '[class*="teacher"], [class*="author"], [class*="university"], ' +
                            '[class*="school"], [class*="org"]'
                        );
                        if (tEl) teacher = tEl.innerText.trim();
                        if (!teacher && lines.length >= 2) {
                            for (const l of lines.slice(1)) {
                                if (/老师|教师|教授|大学|学院/.test(l)) { teacher = l; break; }
                            }
                        }

                        let courseId = 'xuetangx_' + idx;
                        const link = card.tagName === 'A' ? card : card.querySelector('a[href]');
                        if (link) {
                            const href = link.getAttribute('href') || '';
                            let m = href.match(/\\/course\\/([^/?]+)/);
                            if (!m) m = href.match(/\\/learn\\/([^/?]+)/);
                            if (!m) m = href.match(/courseId=([^&]+)/);
                            if (m) courseId = m[1];
                        }

                        let coverUrl = '';
                        const img = card.querySelector('img');
                        if (img) coverUrl = img.getAttribute('src') || '';

                        if (name) courses.push({ name, teacher, courseId, coverUrl });
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
                    platform_course_id=item.get("courseId", f"xuetangx_{len(courses)}"),
                    name=name[:200],
                    teacher=(item.get("teacher") or "").strip(),
                    cover_url=item.get("coverUrl") or "",
                ))
                print(f"[XUETANGX] {name[:60]} | {(item.get('teacher') or '')[:30]}")

            print(f"[XUETANGX] 共解析 {len(courses)} 门课程")
            return courses

        except Exception as e:
            print(f"[XUETANGX] 获取课程异常: {e}")
            import traceback; traceback.print_exc()
            return courses

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")
        raise NotImplementedError("学堂在线章节获取尚未实现")

    async def play_section(self, course_id: str, section_id: str) -> AsyncIterator[ProgressInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")
        raise NotImplementedError("学堂在线视频播放尚未实现")

    async def detect_quiz(self) -> Optional[QuizInfo]:
        return None

    async def submit_answer(self, answer: str) -> bool:
        return False

    async def get_course_progress(self, course_id: str) -> float:
        return 0.0

    async def close(self):
        try:
            if self._context: await self._context.close()
            if self._browser: await self._browser.close()
            if self._playwright: await self._playwright.stop()
        except Exception:
            pass
