import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config import settings


def _build_fernet() -> Fernet:
    if settings.TOKEN_ENCRYPTION_KEY:
        raw_key = settings.TOKEN_ENCRYPTION_KEY.encode("utf-8")
    else:
        raw_key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.APP_SECRET_KEY.encode("utf-8")).digest()
        )
    return Fernet(raw_key)


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None

    try:
        return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Backward compatibility for any tokens stored before encryption was added.
        return value
