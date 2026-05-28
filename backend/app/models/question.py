"""题库模型"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    platform: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="平台专用 or NULL=通用"
    )
    course_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="single_choice/multi_choice/judge/fill_blank"
    )
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), default="manual", comment="manual/ai/import"
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PendingQuestion(Base):
    __tablename__ = "pending_questions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("auto_tasks.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    course_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending/answered"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
