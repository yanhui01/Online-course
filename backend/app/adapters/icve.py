"""智慧职教 (icve.com.cn) 平台适配器"""

from typing import AsyncIterator, List, Optional

from app.adapters.base import (
    BasePlatformAdapter,
    CourseInfo,
    ProgressInfo,
    QuizInfo,
    SectionInfo,
)


class IcveAdapter(BasePlatformAdapter):
    platform_name = "icve"

    async def login(self) -> bool:
        """TODO: 实现智慧职教登录逻辑"""
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def get_courses(self) -> List[CourseInfo]:
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def play_section(
        self, course_id: str, section_id: str
    ) -> AsyncIterator[ProgressInfo]:
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def detect_quiz(self) -> Optional[QuizInfo]:
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def submit_answer(self, answer: str) -> bool:
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def get_course_progress(self, course_id: str) -> float:
        raise NotImplementedError("智慧职教适配器尚未实现")

    async def close(self):
        pass
