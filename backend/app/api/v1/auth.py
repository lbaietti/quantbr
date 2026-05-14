"""
ISO 27001 A.9.2 — User access management.
ISO 27001 A.9.4 — System and application access control.
ISO 27001 A.12.4 — Logging and monitoring (audit trail on every auth event).
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.security.auth import (
    create_access_token, create_refresh_token,
    decode_token, verify_password,
)
from app.security.audit import AuditEvent, audit_log
from app.config import get_settings

router = APIRouter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    ip = _client_ip(request)

    result = await session.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(body.password, user.hashed_password):
        audit_log(AuditEvent.LOGIN_FAILURE, subject=body.email, ip=ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user.last_login = datetime.now(timezone.utc)
    await session.commit()

    access  = create_access_token(str(user.id), user.role)
    refresh = create_refresh_token(str(user.id))
    settings = get_settings()

    audit_log(AuditEvent.LOGIN_SUCCESS, subject=user.email, ip=ip)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise exc
        user_id = payload.get("sub")
    except JWTError:
        raise exc

    result = await session.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise exc

    settings  = get_settings()
    access    = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id))

    audit_log(AuditEvent.TOKEN_REFRESH, subject=user.email)
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )
