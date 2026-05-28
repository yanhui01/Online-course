"""任务日志模型"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("auto_tasks.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(
        String(10), default="INFO", comment="INFO/WARNING/ERROR/DEBUG"
    )
    section_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
