"""
Role-based access control.
ISO 27001 A.9.2 — User access management.
ISO 27001 A.9.4 — System and application access control.
"""
from enum import StrEnum
from functools import wraps
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.security.auth import decode_token

_bearer = HTTPBearer(auto_error=True)


class Role(StrEnum):
    VIEWER = "viewer"    # read-only market data
    TRADER = "trader"    # can submit orders
    ADMIN  = "admin"     # full access + user management


_ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.TRADER: 1,
    Role.ADMIN:  2,
}


class TokenData:
    def __init__(self, subject: str, role: Role) -> None:
        self.subject = subject
        self.role = role


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
) -> TokenData:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise exc
        sub  = payload.get("sub")
        role = payload.get("role", Role.VIEWER)
        if not sub:
            raise exc
        return TokenData(subject=sub, role=Role(role))
    except (JWTError, ValueError):
        raise exc


def require_role(minimum: Role):
    """Dependency factory — enforces a minimum role level."""
    async def _dep(user: Annotated[TokenData, Depends(get_current_user)]) -> TokenData:
        if _ROLE_HIERARCHY[user.role] < _ROLE_HIERARCHY[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum}' or higher",
            )
        return user
    return _dep
