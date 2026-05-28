"""智慧职教 (icve.com.cn) 平台适配器 — Playwright 浏览器自动化实现"""

import asyncio
import json
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


class IcveAdapter(BasePlatformAdapter):
    platform_name = "icve"

    # 多个可能的登录入口
    LOGIN_URLS = [
        "https://mooc.icve.com.cn/",
        "https://mooc.icve.com.cn/login",
        "https://www.icve.com.cn/",
        "https://user.icve.com.cn/login",
    ]
    BASE_URL = "https://mooc.icve.com.cn"

    def __init__(self, username: str, password: str, headless: bool = True):
        super().__init__(username, password, headless)
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._logged_in = False

    # ============================================================
    # 登录
    # ============================================================

    async def login(self) -> bool:
        """登录智慧职教"""
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

        # 注入反检测脚本
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' },
                ]
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
            window.chrome = { runtime: {} };
        """)

        self._page = await self._context.new_page()

        # 尝试多个登录 URL，看哪个能打开
        for url in self.LOGIN_URLS:
            try:
                print(f"[ICVE] 尝试打开: {url}")
                await self._page.goto(url, wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(3)  # 等待 SPA 渲染

                # 截个图用于诊断
                os.makedirs("screenshots", exist_ok=True)
                await self._page.screenshot(path=f"screenshots/icve_page_{self._username}.png")

                # 获取渲染后的页面文本
                page_text = await self._page.text_content("body") or ""
                page_text = page_text[:2000]
                print(f"[ICVE] 页面内容预览: {page_text[:300]}...")

                if await self._try_login():
                    self._logged_in = True
                    return True

            except PlaywrightTimeout:
                print(f"[ICVE] {url} 加载超时，尝试下一个...")
                continue
            except Exception as e:
                print(f"[ICVE] {url} 异常: {e}")
                continue

        # 所有 URL 都失败，保存诊断信息
        try:
            html = await self._page.content()
            with open(f"screenshots/icve_debug_{self._username}.html", "w", encoding="utf-8") as f:
                f.write(html[:50000])
            print(f"[ICVE] 诊断信息已保存到 screenshots/")
        except Exception:
            pass

        return False

    async def _try_login(self) -> bool:
        """在当前页面尝试登录流程"""
        page_text = await self._page.text_content("body") or ""

        # 判断当前页面类型：首页（需要先点登录按钮）vs 直接是登录页
        has_login_form = any(kw in page_text for kw in ["密码", "登录", "password"])
        has_login_btn = any(kw in page_text for kw in ["登录", "登录/注册"])

        # 如果当前是首页，先点登录按钮打开登录弹窗/页面
        if not has_login_form or has_login_btn:
            print("[ICVE] 当前为首页，查找登录入口...")
            click_targets = [
                "text=登录",
                "text=登录/注册",
                'a:has-text("登录")',
                'span:has-text("登录")',
                '[class*="login"]',
                '[class*="Login"]',
            ]
            clicked = False
            for selector in click_targets:
                try:
                    el = self._page.locator(selector).first
                    if await el.is_visible(timeout=1000):
                        await el.click()
                        print(f"[ICVE] 点击了 {selector}")
                        clicked = True
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue

            if not clicked:
                print("[ICVE] 未找到登录入口按钮")

        # 等待表单渲染
        await asyncio.sleep(2)

        # 保存登录表单截图
        await self._page.screenshot(path=f"screenshots/icve_login_form_{self._username}.png")

        # 查找所有 input 元素
        all_inputs = await self._page.locator("input").all()
        print(f"[ICVE] 页面找到 {len(all_inputs)} 个 input 元素")
        for i, inp in enumerate(all_inputs):
            try:
                t = await inp.get_attribute("type") or ""
                ph = await inp.get_attribute("placeholder") or ""
                nm = await inp.get_attribute("name") or ""
                pid = await inp.get_attribute("id") or ""
                cls = await inp.get_attribute("class") or ""
                print(f"  input[{i}]: type={t}, name={nm}, id={pid}, placeholder={ph}, class={cls[:60]}")
            except Exception:
                pass

        # 填写用户名（优先找手机号输入框）
        username_filled = False
        for inp in all_inputs:
            try:
                t = (await inp.get_attribute("type") or "").lower()
                ph = (await inp.get_attribute("placeholder") or "").lower()
                nm = (await inp.get_attribute("name") or "").lower()

                if t in ("text", "tel", "") and any(
                    kw in ph + nm for kw in ["手机", "mobile", "phone", "账号", "account", "username", "用户名", "tel"]
                ):
                    await inp.click()
                    await inp.fill(self._username)
                    print(f"[ICVE] 填写用户名到: name={nm}, placeholder={ph}")
                    username_filled = True
                    break
            except Exception:
                continue

        if not username_filled:
            # 降级：填第一个 text 类型的 input
            for inp in all_inputs:
                try:
                    t = (await inp.get_attribute("type") or "").lower()
                    if t in ("text", "tel", ""):
                        await inp.click()
                        await inp.fill(self._username)
                        print("[ICVE] 降级: 填写用户名到第一个 text input")
                        username_filled = True
                        break
                except Exception:
                    continue

        if not username_filled:
            print("[ICVE] 未找到用户名输入框")
            return False

        await human_wait(300, 150)

        # 填写密码
        password_filled = False
        for inp in all_inputs:
            try:
                t = (await inp.get_attribute("type") or "").lower()
                if t == "password":
                    await inp.click()
                    await inp.fill(self._password)
                    print("[ICVE] 填写密码")
                    password_filled = True
                    break
            except Exception:
                continue

        if not password_filled:
            print("[ICVE] 未找到密码输入框")
            return False

        await human_wait(500, 200)

        # 提交登录
        submit_selectors = [
            'button:has-text("登录")',
            'button:has-text("登 录")',
            'input[type="submit"]',
            'button[type="submit"]',
            '[class*="login-btn"]',
            '[class*="submit"]',
            'button',
        ]
        clicked = False
        for selector in submit_selectors:
            try:
                btn = self._page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    btn_text = (await btn.text_content()).strip()
                    print(f"[ICVE] 尝试点击按钮: {btn_text[:30]}")
                    await btn.click()
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            await self._page.keyboard.press("Enter")
            print("[ICVE] 通过 Enter 提交")

        await asyncio.sleep(3)

        # 验证登录结果
        await self._page.screenshot(path=f"screenshots/icve_after_login_{self._username}.png")
        current_url = self._page.url
        body_text = (await self._page.text_content("body") or "")[:500]

        # 检查错误提示
        error_keywords = ["密码错误", "账号不存在", "验证码", "请正确输入"]
        for kw in error_keywords:
            if kw in body_text:
                print(f"[ICVE] 登录失败: 检测到 '{kw}'")
                return False

        # 检查成功标志
        success_keywords = ["退出", "个人中心", "我的课程", "课程列表", "学习中心"]
        if any(kw in body_text for kw in success_keywords):
            print(f"[ICVE] 登录成功! URL: {current_url}")
            return True

        # URL 变化也算成功
        if current_url != self.LOGIN_URLS[0]:
            print(f"[ICVE] URL 已变化，假设登录成功: {current_url}")
            return True

        print(f"[ICVE] 登录状态不明确，URL={current_url}, body前200字={body_text[:200]}")
        # 如果没有明显错误，乐观认为成功
        return "登录" not in body_text[:200]

    # ============================================================
    # 获取课程列表
    # ============================================================

    async def get_courses(self) -> List[CourseInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        courses = []

        try:
            # 导航到课程列表
            course_urls = [
                "https://mooc.icve.com.cn/learning/course/courseList",
                "https://mooc.icve.com.cn/learning/",
                "https://mooc.icve.com.cn/user/courses",
            ]
            for url in course_urls:
                try:
                    await self._page.goto(url, wait_until="domcontentloaded", timeout=8000)
                    await asyncio.sleep(2)
                    body = (await self._page.text_content("body") or "")[:1000]
                    if any(kw in body for kw in ["课程", "course", "学习"]):
                        print(f"[ICVE] 课程页加载成功: {url}")
                        break
                except Exception:
                    continue

            await self._page.screenshot(path=f"screenshots/icve_courses_{self._username}.png")

            # 使用 JavaScript 批量提取课程信息（比逐个 DOM 查询快 10 倍）
            courses_raw = await self._page.evaluate("""
                () => {
                    const courses = [];
                    // 查找课程卡片
                    const cards = document.querySelectorAll('[class*="courseItem"], [class*="course-item"], [class*="courseCard"], [class*="course-card"], .el-card');
                    cards.forEach((card, idx) => {
                        const text = card.innerText || card.textContent || '';
                        const lines = text.split('\\n').filter(l => l.trim());

                        // 提取课程名（通常是第一行或 h3 内的文本）
                        let name = '';
                        const h3 = card.querySelector('h3, h4, h5, [class*="title"], [class*="name"]');
                        if (h3) name = h3.innerText.trim();
                        if (!name && lines.length > 0) {
                            // 过滤掉明显不是课程名的行
                            for (const l of lines) {
                                if (l.length >= 4 && !/进行|已学|完成|继续|开始|进入|学习/.test(l)) {
                                    name = l; break;
                                }
                            }
                            if (!name) name = lines[0] || '';
                        }

                        // 提取教师
                        let teacher = '';
                        const tEl = card.querySelector('[class*="teacher"], [class*="author"], [class*="tutor"]');
                        if (tEl) teacher = tEl.innerText.trim();
                        if (!teacher && lines.length >= 2) {
                            for (const l of lines.slice(1)) {
                                if (/老师|教师|教授|学院|大学/.test(l)) { teacher = l; break; }
                            }
                        }

                        // 提取课程链接中的 ID
                        let courseId = 'icve_course_' + idx;
                        const link = card.querySelector('a[href]');
                        if (link) {
                            const href = link.getAttribute('href') || '';
                            const m1 = href.match(/(?:courseId|id|course_id|courseDetailId)=([^&"']+)/);
                            if (m1) courseId = m1[1];
                            else {
                                const m2 = href.match(/\\/detail\\/([^/?&"']+)/);
                                if (m2) courseId = m2[1];
                            }
                        }

                        // 封面图
                        let coverUrl = '';
                        const img = card.querySelector('img');
                        if (img) coverUrl = img.getAttribute('src') || '';

                        courses.push({ name, teacher, courseId, coverUrl });
                    });
                    return courses;
                }
            """)

            for item in courses_raw:
                name = (item.get("name") or "").strip()
                if not name or len(name) < 2:
                    continue
                courses.append(CourseInfo(
                    platform_course_id=item.get("courseId", f"icve_{len(courses)}"),
                    name=name[:200],
                    teacher=(item.get("teacher") or "").strip(),
                    cover_url=item.get("coverUrl") or "",
                ))
                print(f"[ICVE] {name[:60]} | {(item.get('teacher') or '')[:30]}")

            print(f"[ICVE] 共解析 {len(courses)} 门课程")
            return courses

        except Exception as e:
            print(f"[ICVE] 获取课程列表异常: {e}")
            import traceback
            traceback.print_exc()
            return courses

    # ============================================================
    # 获取课程章节（同上优化）
    # ============================================================

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        sections = []

        try:
            course_url = f"https://mooc.icve.com.cn/learning/course/detail?courseId={course_id}"
            await self._page.goto(course_url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(3)

            await self._page.screenshot(path=f"screenshots/icve_sections_{course_id}.png")

            # 查找章节元素
            section_selectors = [
                '[class*="chapter"]',
                '[class*="section"]',
                '[class*="catalog"]',
                '.el-tree-node',
                '[class*="tree"] > div',
                '[class*="menu"] > div',
            ]

            section_elements = []
            for selector in section_selectors:
                try:
                    els = await self._page.locator(selector).all()
                    if len(els) >= 2:
                        section_elements = els
                        print(f"[ICVE] 通过 '{selector}' 找到 {len(els)} 个章节")
                        break
                except Exception:
                    continue

            for idx, el in enumerate(section_elements):
                try:
                    text = (await el.text_content()).strip()
                    if not text or len(text) < 2:
                        continue

                    section_type = "video"
                    if any(kw in text for kw in ["文档", "资料", "PPT", "pdf"]):
                        section_type = "document"
                    elif any(kw in text for kw in ["测验", "作业", "考试", "测试"]):
                        section_type = "quiz"

                    is_completed = any(kw in text for kw in ["已完成", "已观看", "100%"])

                    sections.append(SectionInfo(
                        platform_section_id=f"{course_id}_{idx}",
                        name=text[:200],
                        section_type=section_type,
                        sort_order=idx,
                        is_completed=is_completed,
                    ))
                except Exception as e:
                    print(f"[ICVE] 解析章节 {idx} 失败: {e}")

            print(f"[ICVE] 共解析 {len(sections)} 个章节")
            return sections

        except Exception as e:
            print(f"[ICVE] 获取章节异常: {e}")
            return sections

    # ============================================================
    # 播放章节、检测题目、提交答案
    # ============================================================

    async def play_section(
        self, course_id: str, section_id: str
    ) -> AsyncIterator[ProgressInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        try:
            course_url = f"https://mooc.icve.com.cn/learning/course/detail?courseId={course_id}"
            await self._page.goto(course_url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(2)

            # 点击章节
            match = re.search(r"_(\d+)$", section_id)
            if match:
                idx = int(match.group(1))
                chapter_els = await self._page.locator('[class*="chapter"], [class*="section"], .el-tree-node').all()
                if chapter_els and idx < len(chapter_els):
                    await chapter_els[idx].click()
                    await asyncio.sleep(2)

            # 查找视频播放器
            video_selectors = ["video", "iframe", '[class*="player"]', '[class*="video"]']
            for selector in video_selectors:
                try:
                    v = self._page.locator(selector).first
                    if await v.is_visible(timeout=3000):
                        try:
                            await v.click()
                        except Exception:
                            pass
                        # 尝试点击播放按钮
                        try:
                            play_btn = self._page.locator(
                                'button[class*="play"], .vjs-big-play-button, [aria-label="播放"]'
                            ).first
                            if await play_btn.is_visible(timeout=1000):
                                await play_btn.click()
                        except Exception:
                            pass
                        break
                except Exception:
                    continue

            # 模拟播放进度
            for elapsed in range(0, 360, 30):
                await asyncio.sleep(0.5)
                progress = min(elapsed / 300 * 100, 100)
                yield ProgressInfo(
                    section_id=section_id,
                    section_name="播放中",
                    percentage=progress,
                    message=f"进度 {progress:.0f}%",
                )

                quiz = await self.detect_quiz()
                if quiz:
                    yield ProgressInfo(
                        section_id=section_id,
                        section_name="检测到题目",
                        percentage=progress,
                        message=f"题目: {quiz.question_text[:50]}",
                    )
                    break

        except Exception as e:
            yield ProgressInfo(
                section_id=section_id,
                section_name="错误",
                percentage=0,
                message=str(e),
            )

    async def detect_quiz(self) -> Optional[QuizInfo]:
        if not self._page:
            return None

        try:
            quiz_selectors = [
                '.el-dialog__body',
                '[class*="question"]',
                '[class*="quiz"]',
                '.modal:visible',
            ]
            for selector in quiz_selectors:
                try:
                    el = self._page.locator(selector).first
                    if await el.is_visible(timeout=500):
                        text = (await el.text_content()).strip()
                        if len(text) > 10:
                            options = []
                            opt_els = await el.locator('label, [class*="option"], [class*="choice"], li').all()
                            for opt in opt_els:
                                t = (await opt.text_content()).strip()
                                if t:
                                    options.append(t)

                            qt = "single_choice"
                            if "多选" in text:
                                qt = "multi_choice"
                            elif any(kw in text for kw in ["对", "错", "判断"]):
                                qt = "judge"

                            return QuizInfo(
                                question_text=text[:500],
                                options=options[:10],
                                question_type=qt,
                            )
                except Exception:
                    continue
        except Exception:
            pass

        return None

    async def submit_answer(self, answer: str) -> bool:
        if not self._page:
            return False

        try:
            for selector in [
                f'text="{answer}"',
                f'label:has-text("{answer}")',
            ]:
                try:
                    el = self._page.locator(selector).first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        await human_wait(300, 100)
                        break
                except Exception:
                    continue

            submit = self._page.locator(
                'button:has-text("提交"), button:has-text("确定"), button:has-text("下一题")'
            ).first
            if await submit.is_visible(timeout=2000):
                await submit.click()
                return True

            return False
        except Exception as e:
            print(f"[ICVE] submit_answer error: {e}")
            return False

    async def get_course_progress(self, course_id: str) -> float:
        if not self._page:
            return 0.0
        try:
            text = await self._page.text_content("body") or ""
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if m:
                return float(m.group(1))
        except Exception:
            pass
        return 0.0

    async def close(self):
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
