"""平台账号密码加解密 - 使用 Fernet (AES-128-CBC + HMAC)"""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet


def encrypt(data: str) -> str:
    """加密字符串，返回 base64 编码的密文"""
    return _get_fernet().encrypt(data.encode()).decode()


def decrypt(encrypted: str) -> str:
    """解密密文字符串，返回明文"""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        raise ValueError("解密失败：密钥不匹配或数据已损坏")


def encrypt_optional(data: str | None) -> str | None:
    """加密可选字段"""
    if data is None:
        return None
    return encrypt(data)


def decrypt_optional(encrypted: str | None) -> str | None:
    """解密可选字段"""
    if encrypted is None:
        return None
    return decrypt(encrypted)
