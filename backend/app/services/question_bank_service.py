"""题库服务"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.question import PendingQuestion, QuestionBank
from app.schemas.question import (
    PendingQuestionResponse,
    QuestionCreate,
    QuestionResponse,
    QuestionSearchResponse,
)
from app.utils.text_similarity import hash_question, similarity


async def search_answer(db: AsyncSession, question_text: str) -> QuestionSearchResponse:
    """
    搜索答案：先精确哈希匹配，再模糊相似度匹配
    """
    q_hash = hash_question(question_text)

    # 1. 精确哈希匹配
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.question_hash == q_hash)
    )
    exact_match = result.scalar_one_or_none()
    if exact_match is not None:
        exact_match.hit_count += 1
        await db.commit()
        return QuestionSearchResponse(
            found=True,
            question_id=exact_match.id,
            correct_answer=exact_match.correct_answer,
            confidence=1.0,
        )

    # 2. 模糊相似度匹配
    all_questions_result = await db.execute(select(QuestionBank).limit(1000))
    all_questions = all_questions_result.scalars().all()

    best_match = None
    best_score = 0.0
    similar_list = []

    for q in all_questions:
        sim = similarity(question_text, q.question_text)
        if sim >= settings.QUESTION_SIMILARITY_THRESHOLD:
            similar_list.append(q)
            if sim > best_score:
                best_score = sim
                best_match = q

    # 按相似度排序
    similar_list.sort(key=lambda q: similarity(question_text, q.question_text), reverse=True)

    if best_match and best_score >= 0.9:
        best_match.hit_count += 1
        await db.commit()
        return QuestionSearchResponse(
            found=True,
            question_id=best_match.id,
            correct_answer=best_match.correct_answer,
            confidence=best_score,
            similar_questions=[QuestionResponse.model_validate(q) for q in similar_list[:5]],
        )

    return QuestionSearchResponse(
        found=False,
        similar_questions=[QuestionResponse.model_validate(q) for q in similar_list[:5]],
    )


async def add_question(
    db: AsyncSession, data: QuestionCreate
) -> QuestionResponse:
    q_hash = hash_question(data.question_text)

    # 检查是否已存在
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.question_hash == q_hash)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该题目已存在于题库中")

    question = QuestionBank(
        platform=data.platform,
        course_name=data.course_name,
        question_hash=q_hash,
        question_text=data.question_text,
        question_type=data.question_type,
        options=data.options,
        correct_answer=data.correct_answer,
    )
    db.add(question)
    await db.flush()
    await db.refresh(question)
    return QuestionResponse.model_validate(question)


async def get_questions(
    db: AsyncSession, page: int = 1, page_size: int = 20, platform: str | None = None
) -> tuple[list[QuestionResponse], int]:
    base_q = select(QuestionBank)
    count_q = select(func.count()).select_from(QuestionBank)

    if platform:
        base_q = base_q.where(QuestionBank.platform == platform)
        count_q = count_q.where(QuestionBank.platform == platform)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        base_q.order_by(QuestionBank.hit_count.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    questions = result.scalars().all()
    return [QuestionResponse.model_validate(q) for q in questions], total


async def delete_question(db: AsyncSession, question_id: str):
    result = await db.execute(
        select(QuestionBank).where(QuestionBank.id == question_id)
    )
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    await db.delete(question)
    await db.commit()


async def get_pending_questions(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[PendingQuestionResponse], int]:
    base_q = select(PendingQuestion).where(PendingQuestion.status == "pending")
    count_q = (
        select(func.count())
        .select_from(PendingQuestion)
        .where(PendingQuestion.status == "pending")
    )

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        base_q.order_by(PendingQuestion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    return [PendingQuestionResponse.model_validate(item) for item in items], total


async def convert_pending_to_question(
    db: AsyncSession, pending_id: str, correct_answer: str
) -> QuestionResponse:
    """将待答题转化为题库条目"""
    result = await db.execute(
        select(PendingQuestion).where(PendingQuestion.id == pending_id)
    )
    pending = result.scalar_one_or_none()
    if pending is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待答题不存在")

    data = QuestionCreate(
        platform=pending.platform,
        course_name=pending.course_name,
        question_text=pending.question_text,
        question_type=pending.question_type or "single_choice",
        options=pending.options,
        correct_answer=correct_answer,
    )
    question = await add_question(db, data)

    pending.status = "answered"
    await db.commit()

    return question
