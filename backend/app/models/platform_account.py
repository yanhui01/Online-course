"""平台账号模型 - 用户绑定的第三方平台账号"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="icve / zhihuishu / xuetangx"
    )
    login_type: Mapped[str] = mapped_column(
        String(20), default="password", comment="password / sms"
    )
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="平台账号/手机号")
    encrypted_password: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="AES加密密码（短信登录可为空）"
    )
    cookie_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="持久化Cookie(加密)")
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, comment="账号是否有效")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
