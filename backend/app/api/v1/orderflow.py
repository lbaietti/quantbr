"""
Order flow endpoints — delta, volume profile, imbalance, tape.
ISO 27001 A.9.4 — all require authentication.
"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.security.rbac import Role, TokenData, require_role
from app.indicators.imbalance import BookImbalance
from app.schemas.market import SnapshotOut

router = APIRouter()
_viewer = Depends(require_role(Role.VIEWER))
_imbalance_calc = BookImbalance(threshold_pct=60.0)


@router.get("/delta/{symbol}")
async def get_delta(
    symbol: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
) -> JSONResponse:
    redis = request.app.state.redis
    raw = await redis.get(f"orderflow:delta:{symbol.upper()}")
    if not raw:
        return JSONResponse({"error": "No data yet"}, status_code=status.HTTP_404_NOT_FOUND)
    return JSONResponse(json.loads(raw))


@router.get("/volume-profile/{symbol}")
async def get_volume_profile(
    symbol: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
) -> JSONResponse:
    redis = request.app.state.redis
    raw = await redis.get(f"orderflow:vprofile:{symbol.upper()}")
    if not raw:
        return JSONResponse({"error": "No data yet"}, status_code=status.HTTP_404_NOT_FOUND)
    return JSONResponse(json.loads(raw))


@router.get("/imbalance/{symbol}")
async def get_imbalance(
    symbol: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
) -> JSONResponse:
    redis = request.app.state.redis
    snap_raw = await redis.get(f"cache:snapshot:{symbol.upper()}")
    if not snap_raw:
        return JSONResponse({"error": "No snapshot yet"}, status_code=status.HTTP_404_NOT_FOUND)
    snap = json.loads(snap_raw)
    result = _imbalance_calc.evaluate(snap.get("bids", []), snap.get("asks", []))
    if not result:
        return JSONResponse({"error": "Insufficient book data"}, status_code=404)
    return JSONResponse({
        "symbol":         symbol.upper(),
        "bid_vol":        result.bid_vol,
        "ask_vol":        result.ask_vol,
        "ratio":          result.ratio,
        "imbalance_pct":  result.imbalance_pct,
        "side":           result.side,
        "strong":         result.strong,
    })


@router.get("/tape/{symbol}")
async def get_tape(
    symbol: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
    limit: int = 100,
    min_qty: int = 0,
) -> JSONResponse:
    """Recent trades tape, optionally filtered by minimum quantity."""
    redis = request.app.state.redis
    limit = min(limit, 500)
    raw_list = await redis.lrange(f"tape:{symbol.upper()}", 0, limit * 2 - 1)
    trades = []
    for item in raw_list:
        try:
            t = json.loads(item)
            if t.get("qty", 0) >= min_qty:
                trades.append(t)
                if len(trades) >= limit:
                    break
        except Exception:
            continue
    return JSONResponse({"symbol": symbol.upper(), "trades": trades})
