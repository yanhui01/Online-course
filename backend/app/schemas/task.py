"""任务相关 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    course_id: str = Field(..., description="课程 ID")
    account_id: str = Field(..., description="平台账号 ID")
    max_retries: int = Field(3, ge=1, le=10, description="最大重试次数")


class TaskResponse(BaseModel):
    id: str
    course_id: str
    account_id: str
    platform: str
    status: str
    total_sections: int
    completed_sections: int
    progress: float
    current_section_id: str | None = None
    error_message: str | None = None
    retry_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskLogResponse(BaseModel):
    id: str
    level: str
    section_id: str | None = None
    message: str
    screenshot_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskDetailResponse(TaskResponse):
    logs: list[TaskLogResponse] = []
