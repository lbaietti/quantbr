"""
News API — serves classified financial news from the aggregator.
ISO 27001 A.9.4 — viewer role required.
"""
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from jose import JWTError

from app.security.rbac import Role, TokenData, require_role
from app.security.auth import decode_token

router = APIRouter()
_viewer = Depends(require_role(Role.VIEWER))


@router.get("/")
async def get_news(
    request: Request,
    _: Annotated[TokenData, _viewer],
    impact: Literal["all", "hot", "warm", "cold"] = "all",
    limit: int = 50,
) -> JSONResponse:
    redis = request.app.state.redis
    key   = f"news:{impact}"
    raw   = await redis.get(key)
    if not raw:
        return JSONResponse({"items": [], "cached": False})
    items = json.loads(raw)[:min(limit, 200)]
    return JSONResponse({"items": items, "cached": True, "count": len(items)})


@router.websocket("/ws")
async def ws_news_hot(
    websocket: WebSocket,
    token: str,
) -> None:
    """Push HOT news items in real time as they are detected."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    redis  = websocket.app.state.redis
    pubsub = redis.pubsub()
    await pubsub.subscribe("news:hot")

    try:
        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            try:
                await websocket.send_text(msg["data"])
            except WebSocketDisconnect:
                break
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
