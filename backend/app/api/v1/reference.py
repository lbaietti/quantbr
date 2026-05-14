"""
Reference data endpoints — live B3 indices, DI futures, PTAX, SELIC.
Data is fetched by MarketDataFetcher every 30 s and cached in Redis.
ISO 27001 A.9.4 — viewer role required.
"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.security.rbac import Role, TokenData, require_role

router = APIRouter()
_viewer = Depends(require_role(Role.VIEWER))


async def _get(redis, key: str) -> JSONResponse:
    raw = await redis.get(key)
    if not raw:
        return JSONResponse({"error": "Data not yet available — fetcher starting up"}, status_code=503)
    return JSONResponse(json.loads(raw))


@router.get("/indices")
async def get_indices(request: Request, _: Annotated[TokenData, _viewer]) -> JSONResponse:
    return await _get(request.app.state.redis, "ref:indices")


@router.get("/di-futures")
async def get_di_futures(request: Request, _: Annotated[TokenData, _viewer]) -> JSONResponse:
    return await _get(request.app.state.redis, "ref:di_futures")


@router.get("/ptax")
async def get_ptax(request: Request, _: Annotated[TokenData, _viewer]) -> JSONResponse:
    return await _get(request.app.state.redis, "ref:ptax")


@router.get("/selic")
async def get_selic(request: Request, _: Annotated[TokenData, _viewer]) -> JSONResponse:
    return await _get(request.app.state.redis, "ref:selic")


@router.get("/all")
async def get_all_reference(request: Request, _: Annotated[TokenData, _viewer]) -> JSONResponse:
    redis = request.app.state.redis
    keys  = ["ref:indices", "ref:di_futures", "ref:ptax", "ref:selic"]
    vals  = await redis.mget(*keys)
    return JSONResponse({
        "indices":    json.loads(vals[0]) if vals[0] else [],
        "di_futures": json.loads(vals[1]) if vals[1] else [],
        "ptax":       json.loads(vals[2]) if vals[2] else None,
        "selic":      json.loads(vals[3]) if vals[3] else None,
    })
