"""
WebSocket endpoint for real-time market data streaming.
ISO 25010 — Performance Efficiency: Redis pub/sub fanout, no polling.
ISO 27001 A.9.4 — Token validated on handshake before any data is sent.
"""
import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from app.security.auth import decode_token

router = APIRouter()


@router.websocket("/ws/market/{symbol}")
async def ws_market(
    websocket: WebSocket,
    symbol: str,
    token: str = Query(...),
) -> None:
    # Validate JWT before accepting — ISO 27001 A.9.4
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    redis = websocket.app.state.redis
    sym   = symbol.upper()

    # Subscribe to both snapshot and trade channels for this symbol
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"market:snapshot:{sym}", f"market:trade:{sym}", f"signal:{sym}")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                await websocket.send_text(message["data"])
            except WebSocketDisconnect:
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()


@router.websocket("/ws/market")
async def ws_market_all(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """Subscribe to all symbols at once (dashboard overview)."""
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
    await pubsub.psubscribe("market:snapshot:*", "market:trade:*", "signal:*")

    try:
        async for message in pubsub.listen():
            if message["type"] not in ("message", "pmessage"):
                continue
            try:
                await websocket.send_text(message["data"])
            except WebSocketDisconnect:
                break
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        await pubsub.punsubscribe()
        await pubsub.close()
