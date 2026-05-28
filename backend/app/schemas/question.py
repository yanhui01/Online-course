"""题库相关 Schema"""

from datetime import datetime

from pydantic import BaseModel


class QuestionCreate(BaseModel):
    platform: str | None = None
    course_name: str | None = None
    question_text: str
    question_type: str = "single_choice"  # single_choice / multi_choice / judge / fill_blank
    options: list[str] | None = None
    correct_answer: str


class QuestionResponse(BaseModel):
    id: str
    platform: str | None = None
    course_name: str | None = None
    question_text: str
    question_type: str
    options: list[str] | None = None
    correct_answer: str
    source: str
    confidence: float
    hit_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionSearchResponse(BaseModel):
    found: bool
    question_id: str | None = None
    correct_answer: str | None = None
    confidence: float = 0.0
    similar_questions: list[QuestionResponse] = []


class PendingQuestionResponse(BaseModel):
    id: str
    task_id: str
    platform: str
    course_name: str | None = None
    question_text: str
    question_type: str | None = None
    options: list[str] | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
