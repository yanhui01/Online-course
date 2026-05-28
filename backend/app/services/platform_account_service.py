"""平台账号服务"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_adapter
from app.core.crypto import decrypt, encrypt, encrypt_optional
from app.models.platform_account import PlatformAccount
from app.schemas.platform_account import (
    PlatformAccountCreate,
    PlatformAccountResponse,
    PlatformAccountUpdate,
)

VALID_PLATFORMS = {"icve", "zhihuishu", "xuetangx"}
PLATFORM_LABELS = {"icve": "智慧职教", "zhihuishu": "知到/智慧树", "xuetangx": "学堂在线"}


async def create_account(
    db: AsyncSession, user_id: str, data: PlatformAccountCreate
) -> PlatformAccountResponse:
    if data.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的平台: {data.platform}，可选: {', '.join(VALID_PLATFORMS)}",
        )

    if data.login_type not in ("password", "sms"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="login_type 只能是 password 或 sms",
        )

    # 检查重复
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.user_id == user_id,
            PlatformAccount.platform == data.platform,
            PlatformAccount.account_name == data.account_name,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该平台账号已存在")

    account = PlatformAccount(
        user_id=user_id,
        platform=data.platform,
        login_type=data.login_type,
        account_name=data.account_name,
        encrypted_password=encrypt_optional(data.password) if data.password else None,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return PlatformAccountResponse.model_validate(account)


async def get_accounts(
    db: AsyncSession, user_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[PlatformAccountResponse], int]:
    base_query = select(PlatformAccount).where(PlatformAccount.user_id == user_id)
    count_query = select(func.count()).select_from(PlatformAccount).where(
        PlatformAccount.user_id == user_id
    )

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        base_query.order_by(PlatformAccount.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    accounts = result.scalars().all()
    return [PlatformAccountResponse.model_validate(a) for a in accounts], total


async def get_account(db: AsyncSession, user_id: str, account_id: str) -> PlatformAccountResponse:
    account = await _get_owned_account(db, user_id, account_id)
    return PlatformAccountResponse.model_validate(account)


async def update_account(
    db: AsyncSession, user_id: str, account_id: str, data: PlatformAccountUpdate
) -> PlatformAccountResponse:
    account = await _get_owned_account(db, user_id, account_id)

    if data.account_name is not None:
        account.account_name = data.account_name
    if data.password is not None:
        account.encrypted_password = encrypt(data.password)
    if data.login_type is not None:
        account.login_type = data.login_type
    if data.is_valid is not None:
        account.is_valid = data.is_valid

    await db.flush()
    await db.refresh(account)
    return PlatformAccountResponse.model_validate(account)


async def delete_account(db: AsyncSession, user_id: str, account_id: str):
    account = await _get_owned_account(db, user_id, account_id)
    await db.delete(account)
    await db.flush()


async def get_decrypted_password(db: AsyncSession, user_id: str, account_id: str) -> str | None:
    """获取解密后的平台密码"""
    account = await _get_owned_account(db, user_id, account_id)
    if account.encrypted_password is None:
        return None
    return decrypt(account.encrypted_password)


async def send_sms_code(db: AsyncSession, user_id: str, account_id: str) -> dict:
    """
    触发平台发送短信验证码（支持学堂在线等）
    通过 Playwright 打开登录页，点击"发送验证码"按钮
    """
    account = await _get_owned_account(db, user_id, account_id)

    adapter = get_adapter(
        platform=account.platform,
        username=account.account_name,
        password="",
        headless=True,
    )
    try:
        success = await adapter.send_sms_code()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="发送验证码失败，请确认手机号正确且平台可访问",
            )
    finally:
        try:
            await adapter.close()
        except Exception:
            pass

    return {
        "message": "验证码已发送，请查收手机短信",
        "phone": account.account_name,
    }


async def verify_sms_login(
    db: AsyncSession, user_id: str, account_id: str, sms_code: str
) -> dict:
    """
    验证短信验证码并登录，保存 cookie 和登录态
    """
    account = await _get_owned_account(db, user_id, account_id)

    adapter = get_adapter(
        platform=account.platform,
        username=account.account_name,
        password="",
        headless=True,
    )
    try:
        # 先发送验证码（如果还没发送）- 这里直接验证
        success = await adapter.login_with_sms(sms_code)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误或已过期",
            )

        # 保存 cookie 供后续同步课程使用
        cookie_data = await adapter.export_cookies()
        if cookie_data:
            account.cookie_data = encrypt(cookie_data)
        account.is_valid = True
        account.last_login_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "message": "短信验证成功，已保存登录态",
            "account_id": account_id,
        }
    finally:
        try:
            await adapter.close()
        except Exception:
            pass


async def _get_owned_account(
    db: AsyncSession, user_id: str, account_id: str
) -> PlatformAccount:
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == account_id,
            PlatformAccount.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台账号不存在")
    return account
