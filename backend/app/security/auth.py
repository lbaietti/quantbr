"""
JWT authentication helpers.
ISO 27001 A.9.4 — System and application access control.
ISO 27001 A.10.1 — Cryptographic controls.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def _make_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    settings = get_settings()
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    return _make_token(
        {"sub": subject, "role": role, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return _make_token(
        {"sub": subject, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError on invalid/expired token."""
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
