import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.schemas.signal import SignalOut
from app.security.rbac import Role, TokenData, require_role

router = APIRouter()

_viewer = Depends(require_role(Role.VIEWER))


@router.get("/{symbol}", response_model=list[SignalOut])
async def get_signals(
    symbol: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
    limit: int = 20,
) -> list[SignalOut]:
    limit = max(1, min(limit, 100))
    redis = request.app.state.redis
    raw = await redis.lrange(f"signals:{symbol.upper()}", 0, limit - 1)
    results = []
    for item in raw:
        try:
            results.append(SignalOut(**json.loads(item)))
        except Exception:
            continue
    return results
