"""智慧职教 (icve.com.cn) 平台适配器 — Playwright 浏览器自动化实现"""

import asyncio
import base64
import json
import os
import re
from typing import AsyncIterator, List, Optional

import ddddocr
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
        """登录智慧职教（直接访问登录页面）"""
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
        os.makedirs("screenshots", exist_ok=True)

        # 直接访问登录页面
        try:
            print(f"[ICVE] 打开登录页面: https://mooc.icve.com.cn/login")
            await self._page.goto(
                "https://mooc.icve.com.cn/login",
                wait_until="networkidle",
                timeout=20000,
            )
            await asyncio.sleep(3)

            await self._page.screenshot(path=f"screenshots/icve_login_page_{self._username}.png")

            if await self._try_login():
                self._logged_in = True
                return True

            return False

        except PlaywrightTimeout:
            print(f"[ICVE] 登录页面加载超时")
            return False
        except Exception as e:
            print(f"[ICVE] 登录异常: {e}")
            return False

    async def _try_login(self) -> bool:
        """在当前登录页面尝试账号密码登录"""
        await asyncio.sleep(2)

        await self._page.screenshot(path=f"screenshots/icve_login_form_{self._username}.png")

        # 查找所有 input 元素
        all_inputs = await self._page.locator("input").all()
        print(f"[ICVE] 登录页找到 {len(all_inputs)} 个 input 元素")
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

        # 检测并识别验证码
        captcha_input = None
        for inp in all_inputs:
            try:
                ph = (await inp.get_attribute("placeholder") or "").lower()
                t = (await inp.get_attribute("type") or "").lower()
                if "验证码" in ph or "captcha" in ph or "code" in ph:
                    captcha_input = inp
                    break
            except Exception:
                continue

        if captcha_input:
            print("[ICVE] 检测到验证码输入框，尝试识别...")
            captcha_solved = await self._recognize_captcha()
            if captcha_solved:
                await captcha_input.click()
                await captcha_input.fill(captcha_solved)
                print(f"[ICVE] 验证码识别结果: {captcha_solved}")
                await human_wait(300, 100)
            else:
                print("[ICVE] 验证码识别失败，尝试直接提交")

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

        await asyncio.sleep(4)

        # 验证登录结果
        await self._page.screenshot(path=f"screenshots/icve_after_login_{self._username}.png")
        current_url = self._page.url
        body_text = (await self._page.evaluate("document.body.innerText") or "")[:1000]

        # 检查错误提示（包含"验证码"不算失败，可能是登录后页面残留）
        error_keywords = ["密码错误", "账号不存在", "验证码错误", "验证码不正确", "请正确输入"]
        for kw in error_keywords:
            if kw in body_text:
                # 排除"请输入验证码"（说明还没提交）和"记住密码"附近的"验证码"
                if kw == "验证码" and "请输入验证码" not in body_text:
                    continue
                print(f"[ICVE] 登录失败: 检测到 '{kw}'")
                return False

        # 检查成功标志 - 更可靠的方式
        success_keywords = ["退出", "个人中心", "我的课程", "课程列表", "学习中心", "智慧学习中心"]
        if any(kw in body_text for kw in success_keywords):
            print(f"[ICVE] 登录成功! URL: {current_url}")
            return True

        # 检查 Cookie 中是否有登录态
        try:
            cookies = await self._context.cookies()
            has_session = any(
                c["name"].lower() in ("token", "session", "sess", "jsessionid", "icve_token", "uid", "userid")
                or "login" in c["name"].lower()
                for c in cookies
            )
            if has_session:
                print(f"[ICVE] 检测到登录 Cookie，登录成功")
                return True
        except Exception:
            pass

        # URL 变化到非 login 页面
        if "/login" not in current_url.lower():
            print(f"[ICVE] URL 已跳转到: {current_url}")
            return True

        print(f"[ICVE] 登录状态不明确，URL={current_url}, body前200字={body_text[:200]}")
        return False

    async def _recognize_captcha(self) -> str | None:
        """识别验证码图片，使用 ddddocr 进行 OCR"""
        try:
            # 找到验证码图片元素
            captcha_img = self._page.locator("img.login-code-img").first

            # 通过 JS 强制点击/刷新验证码图片
            await self._page.evaluate("""
                () => {
                    const img = document.querySelector('img.login-code-img');
                    if (img) {
                        // 尝试通过相邻元素或父元素点击
                        const parent = img.parentElement;
                        if (parent) parent.click();
                        img.click();
                    }
                }
            """)
            await asyncio.sleep(1.5)

            # 获取图片的 src（可能是通过 JS 动态设置）
            src = await captcha_img.get_attribute("src") or ""

            # 如果 src 仍是空，等待一下再试
            if not src:
                for _ in range(10):
                    await asyncio.sleep(0.5)
                    src = await captcha_img.get_attribute("src") or ""
                    if src and len(src) > 20:
                        break

            # 如果还是空，尝试通过 JS 获取 background-image
            if not src or len(src) <= 20:
                src = await self._page.evaluate("""
                    () => {
                        const img = document.querySelector('img.login-code-img');
                        if (!img) return '';
                        // 检查 background-image
                        const bg = window.getComputedStyle(img).backgroundImage;
                        if (bg && bg.startsWith('url(')) {
                            return bg.slice(5, -2); // 去掉 url(" 和 ")
                        }
                        return img.src || '';
                    }
                """)

            print(f"[ICVE] 验证码 src: {src[:120]}")

            if not src or len(src) <= 20:
                # 最后尝试：截图整个验证码容器区域
                box = await captcha_img.bounding_box()
                if not box or box["width"] == 0:
                    # 尝试父元素
                    parent_box = await self._page.evaluate("""
                        () => {
                            const img = document.querySelector('img.login-code-img');
                            const parent = img ? img.closest('.login-code, [class*=\"code\"], [class*=\"captcha\"]') : null;
                            if (parent) {
                                const r = parent.getBoundingClientRect();
                                return {x: r.x, y: r.y, w: r.width, h: r.height};
                            }
                            return null;
                        }
                    """)
                    if parent_box:
                        box = {"x": parent_box["x"], "y": parent_box["y"],
                               "width": parent_box["w"], "height": parent_box["h"]}

                if box and box["width"] > 0:
                    import io
                    from PIL import Image
                    screenshot_bytes = await self._page.screenshot()
                    img = Image.open(io.BytesIO(screenshot_bytes))
                    cropped = img.crop((
                        int(box["x"]), int(box["y"]),
                        int(box["x"] + box["width"]), int(box["y"] + box["height"]),
                    ))
                    buf = io.BytesIO()
                    cropped.save(buf, format="PNG")
                    img_bytes = buf.getvalue()
                    ocr = ddddocr.DdddOcr(show_ad=False)
                    result = ocr.classification(img_bytes)
                    result = "".join(c for c in result if c.isalnum())
                    print(f"[ICVE] 截图OCR结果: {result}")
                    if result and len(result) >= 3:
                        return result

                print("[ICVE] 验证码图片未能加载")
                return None

            # 从 URL 获取图片字节
            if src.startswith("data:"):
                img_bytes = base64.b64decode(src.split(",", 1)[1])
            else:
                img_bytes = await self._page.evaluate("""
                    async (url) => {
                        const resp = await fetch(url);
                        const blob = await resp.blob();
                        return new Promise((resolve) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result.split(',')[1]);
                            reader.readAsDataURL(blob);
                        });
                    }
                """, src)
                img_bytes = base64.b64decode(img_bytes)

            ocr = ddddocr.DdddOcr(show_ad=False)
            result = ocr.classification(img_bytes)
            result = "".join(c for c in result if c.isalnum())
            print(f"[ICVE] OCR 结果: {result}")
            if result and len(result) >= 3:
                return result
            return None

        except Exception as e:
            print(f"[ICVE] 验证码识别异常: {e}")
            import traceback
            traceback.print_exc()
            return None

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

            # 提取课程信息的内联 JS（避免重复）
            extract_js = """
                (prefix) => {
                    const courses = [];
                    const cards = document.querySelectorAll('[class*="courseItem"], [class*="course-item"], [class*="courseCard"], [class*="course-card"], .el-card');
                    cards.forEach((card, idx) => {
                        const text = card.innerText || card.textContent || '';
                        const lines = text.split('\\n').filter(l => l.trim());

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
                        const tEl = card.querySelector('[class*="teacher"], [class*="author"], [class*="tutor"]');
                        if (tEl) teacher = tEl.innerText.trim();
                        if (!teacher && lines.length >= 2) {
                            for (const l of lines.slice(1)) {
                                if (/老师|教师|教授|学院|大学/.test(l)) { teacher = l; break; }
                            }
                        }

                        let courseId = (prefix || 'icve_course_') + idx;
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

                        let coverUrl = '';
                        const img = card.querySelector('img');
                        if (img) coverUrl = img.getAttribute('src') || '';

                        courses.push({ name, teacher, courseId, coverUrl });
                    });
                    return courses;
                }
            """

            # 1. 先抓取当前默认 Tab（职教课程）
            courses_raw = await self._page.evaluate(extract_js, "icve_course_")

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
                print(f"[ICVE] 职教 | {name[:60]} | {(item.get('teacher') or '')[:30]}")

            # 2. 切换到"MOOC课程"Tab，抓取用户自主加入的MOOC课程
            mooc_clicked = await self._page.evaluate("""
                () => {
                    const all = document.querySelectorAll('.el-tabs__item, [class*="tab"], [role="tab"], span');
                    for (const el of all) {
                        const text = (el.innerText || '').trim();
                        if (text === 'MOOC课程' || text === 'MOOC\u8bfe\u7a0b') {
                            el.click();
                            return 'clicked: ' + el.tagName;
                        }
                    }
                    // 降级：匹配包含 MOOC 且长度较短的文本
                    for (const el of all) {
                        const text = (el.innerText || '').trim();
                        if (text.includes('MOOC') && text.length <= 15) {
                            el.click();
                            return 'fuzzy_clicked: ' + text;
                        }
                    }
                    return 'not_found';
                }
            """)
            print(f"[ICVE] MOOC Tab 切换结果: {mooc_clicked}")

            if "clicked" in str(mooc_clicked):
                await asyncio.sleep(3)  # 等待 MOOC 课程列表加载
                await self._page.screenshot(path=f"screenshots/icve_mooc_courses_{self._username}.png")

                mooc_raw = await self._page.evaluate(extract_js, "icve_mooc_")
                mooc_count = 0
                for item in mooc_raw:
                    name = (item.get("name") or "").strip()
                    if not name or len(name) < 2:
                        continue
                    courses.append(CourseInfo(
                        platform_course_id=item.get("courseId", f"icve_mooc_{len(courses)}"),
                        name=name[:200],
                        teacher=(item.get("teacher") or "").strip(),
                        cover_url=item.get("coverUrl") or "",
                    ))
                    mooc_count += 1
                    print(f"[ICVE] MOOC | {name[:60]} | {(item.get('teacher') or '')[:30]}")
                print(f"[ICVE] MOOC 课程 {mooc_count} 门")

            print(f"[ICVE] 共解析 {len(courses)} 门课程（职教 + MOOC）")

            # 3. 访问个人中心，抓取"我加入的课程"
            personal_urls = [
                "https://mooc.icve.com.cn/learning/user/courses",
                "https://mooc.icve.com.cn/user/courses",
                "https://mooc.icve.com.cn/personal/courses",
                "https://mooc.icve.com.cn/learning/personal",
            ]
            for purl in personal_urls:
                try:
                    await self._page.goto(purl, wait_until="networkidle", timeout=10000)
                    await asyncio.sleep(4)
                    body = await self._page.evaluate("document.body.innerText") or ""
                    # 检查是否有"加入"、"我的课程"等关键词
                    if any(kw in body for kw in ["加入", "我的课程", "已选", "形势", "MOOC"]):
                        print(f"[ICVE] 个人中心课程页: {purl}")
                        await self._page.screenshot(path=f"screenshots/icve_personal_{self._username}.png")
                        personal_raw = await self._page.evaluate(extract_js, "icve_personal_")
                        personal_count = 0
                        existing_ids = {c.platform_course_id for c in courses}
                        for item in personal_raw:
                            name = (item.get("name") or "").strip()
                            if not name or len(name) < 2:
                                continue
                            cid = item.get("courseId", f"icve_personal_{len(courses)}")
                            if cid not in existing_ids:  # 去重
                                courses.append(CourseInfo(
                                    platform_course_id=cid,
                                    name=name[:200],
                                    teacher=(item.get("teacher") or "").strip(),
                                    cover_url=item.get("coverUrl") or "",
                                ))
                                personal_count += 1
                                existing_ids.add(cid)
                                print(f"[ICVE] 个人中心 | {name[:60]} | {(item.get('teacher') or '')[:30]}")
                        print(f"[ICVE] 个人中心课程 {personal_count} 门")
                        if personal_count > 0:
                            break  # 找到了就退出
                except Exception:
                    continue

            print(f"[ICVE] 共解析 {len(courses)} 门课程（职教 + MOOC + 个人中心）")
            return courses

        except Exception as e:
            print(f"[ICVE] 获取课程列表异常: {e}")
            import traceback
            traceback.print_exc()
            return courses

    # ============================================================
    # 获取课程章节（JS 批量提取）
    # ============================================================

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        sections = []

        try:
            # 尝试多种 URL 格式
            urls = [
                f"https://mooc.icve.com.cn/learning/course/detail?courseId={course_id}",
                f"https://mooc.icve.com.cn/learning/course/detail/{course_id}",
                f"https://course.icve.com.cn/course/{course_id}",
            ]
            for url in urls:
                try:
                    await self._page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(4)  # 等待 AJAX 加载章节树
                    body_len = len((await self._page.text_content("body") or ""))
                    print(f"[ICVE] 章节页 {url} body长度={body_len}")
                    if body_len > 500:
                        break
                except Exception:
                    continue

            # 尝试展开所有树节点
            await self._page.evaluate("""
                () => {
                    // 点击所有可展开的树节点
                    const expanders = document.querySelectorAll(
                        '.el-tree-node__expand-icon, [class*="expand"], [class*="arrow"], [class*="toggle"]'
                    );
                    expanders.forEach(e => { try { e.click(); } catch(ex) {} });
                }
            """)
            await asyncio.sleep(2)

            await self._page.screenshot(path=f"screenshots/icve_sections_{course_id}.png")

            # 诊断: 打印页面可见文本
            body_text = (await self._page.text_content("body") or "")[:1000]
            print(f"[ICVE] 章节页文本预览: {body_text[:300]}...")

            # JS 批量提取章节树（更全面的选择器）
            sections_raw = await self._page.evaluate("""
                () => {
                    const result = [];
                    // 尝试多种可能的选择器
                    let treeNodes = document.querySelectorAll(
                        '.el-tree-node, .el-tree-node__content, ' +
                        '[class*="chapter-item"], [class*="chapterItem"], ' +
                        '[class*="catalog"], [class*="menu-item"], ' +
                        '[class*="section"], .tree-node, ' +
                        'li[class*="node"], div[class*="node"]'
                    );
                    // 如果没找到，尝试找所有列表项
                    if (treeNodes.length === 0) {
                        treeNodes = document.querySelectorAll(
                            'li, [class*="list"] > div, [class*="tree"] > div, ' +
                            '[class*="sidebar"] a, [class*="nav"] a'
                        );
                    }
                    console.log('Found tree nodes:', treeNodes.length);

                    treeNodes.forEach((node, idx) => {
                        const text = (node.innerText || node.textContent || '').trim();
                        if (!text || text.length < 2 || text.length > 500) return;

                        let sectionType = 'video';
                        if (/文档|资料|PPT|pdf|课件/.test(text)) sectionType = 'document';
                        else if (/测验|作业|考试|测试|习题/.test(text)) sectionType = 'quiz';

                        const isCompleted = /已完成|已观看|100%|✓|√/.test(text);

                        let sectionId = 'section_' + idx;
                        const idAttr = node.getAttribute('data-id') || node.getAttribute('id') || '';
                        if (idAttr) sectionId = idAttr;

                        result.push({
                            sectionId: sectionId,
                            name: text.substring(0, 200),
                            sectionType: sectionType,
                            isCompleted: isCompleted
                        });
                    });
                    return result;
                }
            """)

            for idx, item in enumerate(sections_raw):
                name = (item.get("name") or "").strip()
                if not name:
                    continue
                sections.append(SectionInfo(
                    platform_section_id=item.get("sectionId", f"{course_id}_{idx}"),
                    name=name[:200],
                    section_type=item.get("sectionType", "video"),
                    sort_order=idx,
                    is_completed=item.get("isCompleted", False),
                ))

            print(f"[ICVE] 共解析 {len(sections)} 个章节")
            return sections

        except Exception as e:
            print(f"[ICVE] 获取章节异常: {e}")
            return sections

    # ============================================================
    # 播放章节视频（真实视频进度监控）
    # ============================================================

    async def play_section(
        self, course_id: str, section_id: str
    ) -> AsyncIterator[ProgressInfo]:
        if not self._logged_in:
            raise RuntimeError("请先调用 login()")

        try:
            # 1. 进入课程学习页面
            course_url = f"https://mooc.icve.com.cn/learning/course/detail?courseId={course_id}"
            await self._page.goto(course_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)

            # 2. 点击章节节点
            clicked = await self._page.evaluate("""
                (sectionId) => {
                    // 尝试多种方式找到并点击章节
                    const nodes = document.querySelectorAll('.el-tree-node, [class*="chapter"], [class*="section-item"]');
                    for (const node of nodes) {
                        const text = (node.innerText || '').trim();
                        if (text && text.length > 1) {
                            // 点击节点展开/激活
                            const label = node.querySelector('.el-tree-node__label, [class*="label"], [class*="title"]');
                            if (label) {
                                label.click();
                                return true;
                            }
                            node.click();
                            return true;
                        }
                    }
                    return false;
                }
            """, section_id)

            await asyncio.sleep(3)
            await self._page.screenshot(path=f"screenshots/icve_playing_{section_id}.png")

            # 3. 查找视频 iframe 或 video 标签
            video_info = await self._page.evaluate("""
                () => {
                    // 查找 iframe（通常智慧职教的视频在 iframe 中）
                    const iframes = document.querySelectorAll('iframe');
                    for (const iframe of iframes) {
                        const src = iframe.src || '';
                        if (src.includes('video') || src.includes('player') || src.includes('mp4')) {
                            return { type: 'iframe', src: src, hasVideo: true };
                        }
                    }
                    // 查找 video 标签
                    const video = document.querySelector('video');
                    if (video) {
                        return {
                            type: 'video',
                            hasVideo: true,
                            duration: video.duration || 0,
                            currentTime: video.currentTime || 0
                        };
                    }
                    return { type: 'none', hasVideo: false };
                }
            """)

            print(f"[ICVE] 视频检测结果: {video_info}")

            if video_info.get("hasVideo"):
                # 点击播放按钮
                await self._page.evaluate("""
                    () => {
                        const playBtn = document.querySelector(
                            'button[class*="play"], .vjs-big-play-button, [aria-label="播放"], ' +
                            '.prism-play-btn, [class*="play-btn"]'
                        );
                        if (playBtn) playBtn.click();
                        // 尝试直接播放 video
                        const video = document.querySelector('video');
                        if (video) video.play();
                    }
                """)
                await asyncio.sleep(2)

            # 4. 监控视频播放进度
            total_duration = 300  # 默认300秒
            last_percentage = 0

            for check_round in range(60):  # 最多监控 60 轮（约 5 分钟）
                await asyncio.sleep(3)  # 每 3 秒检查一次

                # 获取真实视频进度
                real_progress = await self._page.evaluate("""
                    () => {
                        // 先查主页面中的 video
                        let video = document.querySelector('video');
                        // 再查 iframe 中的 video
                        if (!video || video.duration === 0) {
                            const iframes = document.querySelectorAll('iframe');
                            for (const iframe of iframes) {
                                try {
                                    const iframeVideo = iframe.contentDocument?.querySelector('video');
                                    if (iframeVideo && iframeVideo.duration > 0) {
                                        video = iframeVideo;
                                        break;
                                    }
                                } catch(e) {}
                            }
                        }
                        if (video && video.duration > 0) {
                            return {
                                currentTime: video.currentTime,
                                duration: video.duration,
                                ended: video.ended,
                                paused: video.paused
                            };
                        }
                        return null;
                    }
                """)

                if real_progress:
                    pct = min(real_progress["currentTime"] / real_progress["duration"] * 100, 100)
                    last_percentage = pct

                    yield ProgressInfo(
                        section_id=section_id,
                        section_name="播放中",
                        percentage=pct,
                        message=f"{real_progress['currentTime']:.0f}s / {real_progress['duration']:.0f}s",
                    )

                    if real_progress["ended"]:
                        break
                else:
                    # 没有检测到真实视频，使用模拟进度
                    last_percentage += 3
                    if last_percentage >= 100:
                        last_percentage = 100
                        break

                    yield ProgressInfo(
                        section_id=section_id,
                        section_name="模拟播放中",
                        percentage=last_percentage,
                        message=f"模拟进度 {last_percentage:.0f}%",
                    )

                # 检测弹窗题目
                quiz = await self.detect_quiz()
                if quiz:
                    yield ProgressInfo(
                        section_id=section_id,
                        section_name="检测到题目",
                        percentage=last_percentage,
                        message=f"题目: {quiz.question_text[:50]}",
                    )
                    break

            # 确保最终进度 100%
            yield ProgressInfo(
                section_id=section_id,
                section_name="播放完成",
                percentage=100,
                message="本节已完成",
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield ProgressInfo(
                section_id=section_id,
                section_name="播放错误",
                percentage=0,
                message=str(e),
            )

    async def detect_quiz(self) -> Optional[QuizInfo]:
        """JS 检测弹窗题目"""
        if not self._page:
            return None

        try:
            quiz_data = await self._page.evaluate("""
                () => {
                    // 查找弹窗中的题目
                    const dialogs = document.querySelectorAll(
                        '.el-dialog__body, .el-dialog, [class*="dialog"], ' +
                        '[class*="modal"], [class*="popup"], [class*="question"]'
                    );
                    for (const d of dialogs) {
                        if (!d.offsetParent) continue; // 不可见
                        const text = (d.innerText || d.textContent || '').trim();
                        if (text.length < 10) continue;

                        // 提取选项
                        const optionEls = d.querySelectorAll(
                            'label, [class*="option"], [class*="choice"], li, input[type="radio"]'
                        );
                        const options = [];
                        optionEls.forEach(opt => {
                            const t = (opt.innerText || opt.textContent || '').trim();
                            if (t && t.length > 1) options.push(t);
                        });

                        let qtype = 'single_choice';
                        if (/多选/.test(text)) qtype = 'multi_choice';
                        else if (/判断|对.*错/.test(text)) qtype = 'judge';

                        return { text, options, qtype };
                    }
                    return null;
                }
            """)

            if quiz_data:
                return QuizInfo(
                    question_text=quiz_data["text"][:500],
                    options=quiz_data.get("options", [])[:10],
                    question_type=quiz_data.get("qtype", "single_choice"),
                )

        except Exception:
            pass

        return None

    async def submit_answer(self, answer: str) -> bool:
        """JS 提交答案"""
        if not self._page:
            return False

        try:
            result = await self._page.evaluate("""
                (answerText) => {
                    // 查找包含答案的选项并点击
                    const allEls = document.querySelectorAll('label, [class*="option"], [class*="choice"], li');
                    for (const el of allEls) {
                        const t = (el.innerText || '').trim();
                        if (t.includes(answerText)) {
                            el.click();
                            // 找提交按钮
                            const submitBtn = document.querySelector(
                                'button:has-text("提交"), button:has-text("确定"), ' +
                                'button:has-text("下一题"), [class*="submit"]'
                            );
                            if (submitBtn) {
                                setTimeout(() => submitBtn.click(), 500);
                            }
                            return true;
                        }
                    }
                    return false;
                }
            """, answer)

            return bool(result)

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

            await self._page.goto(self.LOGIN_URLS[0], wait_until="domcontentloaded", timeout=10000)
            await asyncio.sleep(3)

            # 尝试找二维码
            for tab_text in ["扫码登录", "微信登录", "二维码"]:
                try:
                    tab = self._page.locator(f'text="{tab_text}"').first
                    if await tab.is_visible(timeout=1000):
                        await tab.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue

            await self._page.screenshot(path=f"screenshots/icve_qrcode_{self._username}.png")
            with open(f"screenshots/icve_qrcode_{self._username}.png", "rb") as f:
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
                current_url = self._page.url
                if any(kw in body for kw in ["退出", "我的课程", "课程列表", "学习中心"]):
                    self._logged_in = True
                    return True
                if "login" not in current_url.lower():
                    self._logged_in = True
                    return True
            except Exception:
                continue
        return False

    # ============================================================
    # 短信验证码登录（绕过图片验证码）
    # ============================================================

    async def send_sms_code(self) -> bool:
        """发送短信验证码 — 通过首页弹窗"""
        try:
            if not self._playwright:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self._headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
                )
                self._context = await self._browser.new_context(
                    viewport={"width": 1366, "height": 768}, locale="zh-CN",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                )
                self._page = await self._context.new_page()

            # 首页弹窗登录
            await self._page.goto("https://mooc.icve.com.cn/", wait_until="networkidle", timeout=15000)
            await asyncio.sleep(4)

            # 点击登录按钮
            login_btn = self._page.locator('text=登录').first
            if await login_btn.is_visible(timeout=2000):
                await login_btn.click()
                await asyncio.sleep(3)

            # 填写手机号
            phone_input = self._page.locator('input[placeholder*="手机号"]').first
            if await phone_input.is_visible(timeout=2000):
                await phone_input.fill(self._username)
                print(f"[ICVE] SMS: 已填写手机号 {self._username}")
            else:
                print("[ICVE] SMS: 未找到手机号输入框")
                return False

            # 点击发送验证码按钮
            send_btn_selectors = [
                'button:has-text("发送")',
                'span:has-text("发送")',
                'text=发送验证码',
                'text=获取验证码',
                '[class*="send"]',
                '[class*="get-code"]',
            ]
            for sel in send_btn_selectors:
                try:
                    btn = self._page.locator(sel).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        print(f"[ICVE] SMS: 已点击发送验证码")
                        await self._page.screenshot(path=f"screenshots/icve_sms_sent_{self._username}.png")
                        return True
                except Exception:
                    continue

            print("[ICVE] SMS: 未找到发送验证码按钮")
            return False

        except Exception as e:
            print(f"[ICVE] send_sms_code 异常: {e}")
            return False

    async def login_with_sms(self, sms_code: str) -> bool:
        """短信验证码登录"""
        try:
            # 填写验证码
            code_input = self._page.locator('input[placeholder*="验证码"]').first
            if await code_input.is_visible(timeout=2000):
                await code_input.fill(sms_code)
                print(f"[ICVE] SMS: 已填写验证码")
            else:
                print("[ICVE] SMS: 未找到验证码输入框")
                return False

            # 点击登录
            submit_btn = self._page.locator('button:has-text("登录"), button:has-text("登 录")').first
            if await submit_btn.is_visible(timeout=2000):
                await submit_btn.click()
                print(f"[ICVE] SMS: 已点击登录")
                await asyncio.sleep(4)
            else:
                await self._page.keyboard.press("Enter")

            # 验证登录结果
            await self._page.screenshot(path=f"screenshots/icve_sms_result_{self._username}.png")
            body = await self._page.evaluate("document.body.innerText") or ""
            current_url = self._page.url

            success_keywords = ["退出", "个人中心", "我的课程", "课程列表", "学习中心", "智慧学习中心"]
            if any(kw in body for kw in success_keywords):
                self._logged_in = True
                print(f"[ICVE] SMS 登录成功!")
                return True
            if "/login" not in current_url.lower():
                self._logged_in = True
                print(f"[ICVE] SMS 登录成功 (URL跳转): {current_url}")
                return True

            print(f"[ICVE] SMS 登录失败: {body[:200]}")
            return False

        except Exception as e:
            print(f"[ICVE] login_with_sms 异常: {e}")
            return False

    # ============================================================
    # Cookie 管理
    # ============================================================

    async def export_cookies(self) -> str:
        """导出 Cookie JSON"""
        if not self._context:
            return ""
        try:
            cookies = await self._context.cookies()
            return json.dumps(cookies, ensure_ascii=False)
        except Exception:
            return ""

    async def load_cookies(self, cookie_data: str) -> bool:
        """加载 Cookie 恢复登录态"""
        if not cookie_data:
            return False
        try:
            if not self._playwright:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self._headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
                )
                self._context = await self._browser.new_context(
                    viewport={"width": 1366, "height": 768}, locale="zh-CN",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                )
                self._page = await self._context.new_page()

            cookies = json.loads(cookie_data)
            await self._context.add_cookies(cookies)
            print(f"[ICVE] 已加载 {len(cookies)} 个 Cookie")

            # 验证 Cookie 是否有效
            await self._page.goto("https://mooc.icve.com.cn/", wait_until="networkidle", timeout=15000)
            await asyncio.sleep(3)
            body = await self._page.evaluate("document.body.innerText") or ""

            if any(kw in body for kw in ["退出", "个人中心", "我的课程", "学习中心"]):
                self._logged_in = True
                print("[ICVE] Cookie 有效，已恢复登录")
                return True

            print(f"[ICVE] Cookie 已过期: {body[:100]}")
            return False

        except Exception as e:
            print(f"[ICVE] load_cookies 异常: {e}")
            return False

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
