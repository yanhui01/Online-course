"""平台适配器抽象基类 - 策略模式核心"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional


@dataclass
class CourseInfo:
    """平台课程信息"""
    platform_course_id: str
    name: str
    teacher: str = ""
    cover_url: str = ""
    total_sections: int = 0
    completed_sections: int = 0
    progress: float = 0.0  # 0.0 - 100.0


@dataclass
class SectionInfo:
    """课程章节信息"""
    platform_section_id: str
    name: str
    section_type: str = "video"  # video / document / quiz
    duration_minutes: int = 0
    sort_order: int = 0
    is_completed: bool = False


@dataclass
class QuizInfo:
    """题目信息"""
    question_text: str
    options: List[str] = field(default_factory=list)  # ["A.xxx", "B.xxx", ...]
    question_type: str = "single_choice"  # single_choice / multi_choice / judge


@dataclass
class ProgressInfo:
    """进度信息"""
    section_id: str
    section_name: str
    percentage: float  # 0.0 - 100.0
    message: str = ""


class BasePlatformAdapter(ABC):
    """所有平台适配器的抽象基类"""

    platform_name: str = "unknown"

    def __init__(self, username: str, password: str, headless: bool = True):
        self._username = username
        self._password = password
        self._headless = headless

    @abstractmethod
    async def login(self) -> bool:
        """登录平台，返回是否成功"""
        ...

    @abstractmethod
    async def get_courses(self) -> List[CourseInfo]:
        """获取当前账号已选课程列表"""
        ...

    @abstractmethod
    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        """获取课程章节列表"""
        ...

    @abstractmethod
    async def play_section(
        self, course_id: str, section_id: str
    ) -> AsyncIterator[ProgressInfo]:
        """播放指定章节的视频/课件，yield 进度更新"""
        ...

    @abstractmethod
    async def detect_quiz(self) -> Optional[QuizInfo]:
        """检测当前页面是否弹出题目"""
        ...

    @abstractmethod
    async def submit_answer(self, answer: str) -> bool:
        """提交答案"""
        ...

    @abstractmethod
    async def get_course_progress(self, course_id: str) -> float:
        """获取课程完成百分比"""
        ...

    async def send_sms_code(self) -> bool:
        """发送短信验证码（子类可选实现）"""
        raise NotImplementedError(f"{self.platform_name} 不支持短信验证码")

    async def login_with_sms(self, sms_code: str) -> bool:
        """短信验证码登录（子类可选实现）"""
        raise NotImplementedError(f"{self.platform_name} 不支持短信验证码")

    async def export_cookies(self) -> str:
        """导出 Cookie（JSON格式）"""
        return ""

    async def get_qrcode(self) -> str | None:
        """
        获取登录二维码（base64 图片）
        返回 base64 编码的 PNG 图片，失败返回 None
        """
        raise NotImplementedError(f"{self.platform_name} 不支持扫码登录")

    async def wait_qrcode_scan(self, timeout: int = 120) -> bool:
        """
        等待用户扫码登录（阻塞最多 timeout 秒）
        成功返回 True，超时返回 False
        """
        raise NotImplementedError(f"{self.platform_name} 不支持扫码登录")

    async def export_cookies(self) -> str:
        """导出 Cookie（JSON格式）"""
        return ""

    async def load_cookies(self, cookie_data: str) -> bool:
        """加载 Cookie 恢复登录态，成功返回 True"""
        return False

    @abstractmethod
    async def close(self):
        """关闭浏览器资源"""
        ...
