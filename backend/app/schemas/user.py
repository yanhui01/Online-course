"""用户相关 Schema"""

from datetime import datetime

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    email: str | None = None
