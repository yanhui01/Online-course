"""平台账号相关 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class PlatformAccountCreate(BaseModel):
    platform: str = Field(..., description="icve / zhihuishu / xuetangx")
    login_type: str = Field("password", description="password / sms")
    account_name: str = Field(..., description="平台账号/手机号")
    password: str | None = Field(None, description="登录密码（password 模式必填）")

    @model_validator(mode="after")
    def check_password(self):
        if self.login_type == "password" and not self.password:
            raise ValueError("密码登录模式下，密码不能为空")
        return self


class PlatformAccountUpdate(BaseModel):
    account_name: str | None = None
    password: str | None = None
    login_type: str | None = None
    is_valid: bool | None = None


class PlatformAccountResponse(BaseModel):
    id: str
    platform: str
    login_type: str
    account_name: str
    is_valid: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformAccountListResponse(BaseModel):
    items: list[PlatformAccountResponse]
    total: int


class SendSmsRequest(BaseModel):
    account_id: str = Field(..., description="平台账号 ID")


class VerifySmsRequest(BaseModel):
    account_id: str = Field(..., description="平台账号 ID")
    sms_code: str = Field(..., description="短信验证码")
