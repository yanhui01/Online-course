"""扫码登录 API"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.factory import get_adapter
from app.core.crypto import encrypt
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.platform_account import PlatformAccount

router = APIRouter(prefix="/qrcode", tags=["扫码登录"])

_active_qr_adapters: dict[str, object] = {}


class QrcodeRequest(BaseModel):
    account_id: str
    timeout: int = 120


@router.post("/get")
async def get_qrcode(
    data: QrcodeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取登录二维码（base64图片）"""
    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == data.account_id,
            PlatformAccount.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")

    adapter = get_adapter(
        platform=account.platform,
        username=account.account_name,
        password="",
        headless=True,
    )

    try:
        qr_data = await adapter.get_qrcode()
        if not qr_data:
            raise HTTPException(status_code=502, detail="无法获取二维码，该平台可能不支持扫码登录")

        _active_qr_adapters[data.account_id] = adapter

        return {
            "qrcode": qr_data,
            "account_id": data.account_id,
            "message": "请用对应平台 APP 扫描二维码",
        }
    except NotImplementedError:
        await adapter.close()
        raise HTTPException(status_code=400, detail="该平台不支持扫码登录")
    except HTTPException:
        raise
    except Exception as e:
        await adapter.close()
        raise HTTPException(status_code=502, detail=f"获取二维码失败: {str(e)}")


@router.post("/wait")
async def wait_qrcode_scan(
    data: QrcodeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """等待扫码完成（阻塞最多 timeout 秒）"""
    adapter = _active_qr_adapters.get(data.account_id)
    if adapter is None:
        raise HTTPException(status_code=400, detail="请先获取二维码")

    try:
        success = await adapter.wait_qrcode_scan(timeout=data.timeout)

        if not success:
            del _active_qr_adapters[data.account_id]
            await adapter.close()
            raise HTTPException(status_code=408, detail="扫码超时，请重试")

        result = await db.execute(
            select(PlatformAccount).where(
                PlatformAccount.id == data.account_id,
                PlatformAccount.user_id == user_id,
            )
        )
        account = result.scalar_one_or_none()

        if account:
            cookie_data = await adapter.export_cookies()
            if cookie_data:
                account.cookie_data = encrypt(cookie_data)
            account.is_valid = True
            account.last_login_at = datetime.now(timezone.utc)
            await db.commit()

        del _active_qr_adapters[data.account_id]
        await adapter.close()

        return {"message": "扫码登录成功", "account_id": data.account_id}

    except HTTPException:
        raise
    except Exception as e:
        del _active_qr_adapters[data.account_id]
        try:
            await adapter.close()
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"扫码登录失败: {str(e)}")
