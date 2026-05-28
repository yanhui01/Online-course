"""课程相关 Schema"""

from datetime import datetime

from pydantic import BaseModel


class SectionResponse(BaseModel):
    id: str
    platform_section_id: str
    name: str
    section_type: str
    duration_minutes: int
    sort_order: int
    is_completed: bool
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class CourseResponse(BaseModel):
    id: str
    platform: str
    platform_course_id: str
    name: str
    teacher: str
    cover_url: str
    total_sections: int
    completed_sections: int
    progress: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CourseDetailResponse(CourseResponse):
    sections: list[SectionResponse] = []


class CourseSyncRequest(BaseModel):
    account_id: str
