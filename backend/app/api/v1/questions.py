"""题库 API 路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.question import QuestionCreate, QuestionSearchResponse
from app.services import question_bank_service

router = APIRouter(prefix="/questions", tags=["题库"])


@router.get("/search", response_model=QuestionSearchResponse)
async def search_question(
    q: str = Query(..., description="题目文本"),
    db: AsyncSession = Depends(get_db),
):
    """搜索答案"""
    return await question_bank_service.search_answer(db, q)


@router.post("", status_code=201)
async def add_question(data: QuestionCreate, db: AsyncSession = Depends(get_db)):
    """添加题目"""
    return await question_bank_service.add_question(db, data)


@router.get("")
async def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: str | None = Query(None, description="按平台筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取题库列表"""
    items, total = await question_bank_service.get_questions(db, page, page_size, platform)
    return {"items": items, "total": total}


@router.delete("/{question_id}")
async def delete_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """删除题目"""
    await question_bank_service.delete_question(db, question_id)
    return {"message": "删除成功"}


@router.get("/pending")
async def list_pending_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取待答题列表"""
    items, total = await question_bank_service.get_pending_questions(db, page, page_size)
    return {"items": items, "total": total}


@router.post("/pending/{pending_id}/answer")
async def answer_pending_question(
    pending_id: str,
    correct_answer: str = Query(..., description="正确答案"),
    db: AsyncSession = Depends(get_db),
):
    """将待答题录入题库"""
    return await question_bank_service.convert_pending_to_question(db, pending_id, correct_answer)
