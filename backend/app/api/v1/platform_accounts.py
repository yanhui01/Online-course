"""平台账号 API 路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.schemas.platform_account import (
    PlatformAccountCreate,
    PlatformAccountResponse,
    PlatformAccountUpdate,
    SendSmsRequest,
    VerifySmsRequest,
)
from app.services import platform_account_service

router = APIRouter(prefix="/accounts", tags=["平台账号"])


@router.post("", response_model=PlatformAccountResponse, status_code=201)
async def create_account(
    data: PlatformAccountCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """添加平台账号"""
    return await platform_account_service.create_account(db, user_id, data)


@router.get("")
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取平台账号列表"""
    items, total = await platform_account_service.get_accounts(db, user_id, page, page_size)
    return {"items": items, "total": total}


@router.get("/{account_id}", response_model=PlatformAccountResponse)
async def get_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取单个平台账号"""
    return await platform_account_service.get_account(db, user_id, account_id)


@router.put("/{account_id}", response_model=PlatformAccountResponse)
async def update_account(
    account_id: str,
    data: PlatformAccountUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新平台账号"""
    return await platform_account_service.update_account(db, user_id, account_id, data)


@router.delete("/{account_id}")
async def delete_account(
    account_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """删除平台账号"""
    await platform_account_service.delete_account(db, user_id, account_id)
    return {"message": "删除成功"}


@router.post("/send-sms")
async def send_sms(
    data: SendSmsRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """发送短信验证码（学堂在线）"""
    return await platform_account_service.send_sms_code(db, user_id, data.account_id)


@router.post("/verify-sms")
async def verify_sms(
    data: VerifySmsRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """验证短信验证码并登录（学堂在线）"""
    return await platform_account_service.verify_sms_login(
        db, user_id, data.account_id, data.sms_code
    )
