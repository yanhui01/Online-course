"""知到/智慧树 (zhihuishu.com) 平台适配器"""

from typing import AsyncIterator, List, Optional

from app.adapters.base import (
    BasePlatformAdapter,
    CourseInfo,
    ProgressInfo,
    QuizInfo,
    SectionInfo,
)


class ZhihuishuAdapter(BasePlatformAdapter):
    platform_name = "zhihuishu"

    async def login(self) -> bool:
        """TODO: 实现知到登录逻辑"""
        raise NotImplementedError("知到适配器尚未实现")

    async def get_courses(self) -> List[CourseInfo]:
        raise NotImplementedError("知到适配器尚未实现")

    async def get_sections(self, course_id: str) -> List[SectionInfo]:
        raise NotImplementedError("知到适配器尚未实现")

    async def play_section(
        self, course_id: str, section_id: str
    ) -> AsyncIterator[ProgressInfo]:
        raise NotImplementedError("知到适配器尚未实现")

    async def detect_quiz(self) -> Optional[QuizInfo]:
        raise NotImplementedError("知到适配器尚未实现")

    async def submit_answer(self, answer: str) -> bool:
        raise NotImplementedError("知到适配器尚未实现")

    async def get_course_progress(self, course_id: str) -> float:
        raise NotImplementedError("知到适配器尚未实现")

    async def close(self):
        pass
