"""
QuantLab API — strategy submission, management and signal streaming.
ISO 27001 A.9.4 — trader role required to submit/manage strategies.
ISO 27001 A.14.2 — code execution is sandboxed; see quantlab/sandbox.py.
"""
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from jose import JWTError

from app.security.rbac import Role, TokenData, require_role
from app.security.auth import decode_token
from app.quantlab.sandbox import QuantLabSandbox

router = APIRouter()
_sandbox = QuantLabSandbox()

_viewer = Depends(require_role(Role.VIEWER))
_trader = Depends(require_role(Role.TRADER))


class StrategySubmit(BaseModel):
    source: str = Field(..., min_length=10, max_length=32_000)


class ValidateRequest(BaseModel):
    source: str = Field(..., min_length=10, max_length=32_000)


class StrategyPatch(BaseModel):
    active: bool


@router.post("/strategies", status_code=status.HTTP_201_CREATED)
async def submit_strategy(
    body: StrategySubmit,
    request: Request,
    user: Annotated[TokenData, _trader],
) -> dict:
    """Compile, safety-check, and register a user strategy."""
    cls, errors = _sandbox.run(body.source)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": errors},
        )

    registry = request.app.state.strategy_registry
    sid      = str(uuid.uuid4())
    name     = getattr(cls, "name", "Unnamed Strategy")
    record   = registry.add(
        strategy_id=sid,
        name=name,
        author=user.subject,
        source=body.source,
        cls=cls,
    )
    return {
        "id":     record.id,
        "name":   record.name,
        "active": record.enabled,
    }


@router.get("/strategies")
async def list_strategies(
    request: Request,
    _: Annotated[TokenData, _viewer],
) -> dict:
    registry = request.app.state.strategy_registry
    return {
        "strategies": [
            {
                "id":           r.id,
                "name":         r.name,
                "description":  getattr(r.instance, "description", ""),
                "symbols":      getattr(r.instance, "symbols", []),
                "author":       r.author,
                "active":       r.enabled,
                "signal_count": r.signal_count,
                "error_count":  r.error_count,
                "error":        r.last_error,
                "created_at":   r.created_at.isoformat(),
            }
            for r in registry.list_all()
        ]
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
) -> dict:
    registry = request.app.state.strategy_registry
    record = registry.get(strategy_id)
    if not record:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {
        "id":           record.id,
        "name":         record.name,
        "description":  getattr(record.instance, "description", ""),
        "symbols":      getattr(record.instance, "symbols", []),
        "author":       record.author,
        "source":       record.source,
        "active":       record.enabled,
        "signal_count": record.signal_count,
        "error_count":  record.error_count,
        "error":        record.last_error,
        "created_at":   record.created_at.isoformat(),
    }


@router.patch("/strategies/{strategy_id}")
async def patch_strategy(
    strategy_id: str,
    body: StrategyPatch,
    request: Request,
    _: Annotated[TokenData, _trader],
) -> dict:
    registry = request.app.state.strategy_registry
    record = registry.get(strategy_id)
    if not record:
        raise HTTPException(status_code=404, detail="Strategy not found")
    record.enabled = body.active
    return {"id": record.id, "active": record.enabled}


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: str,
    request: Request,
    _: Annotated[TokenData, _trader],
) -> None:
    registry = request.app.state.strategy_registry
    if not registry.remove(strategy_id):
        raise HTTPException(status_code=404, detail="Strategy not found")


@router.get("/strategies/{strategy_id}/signals")
async def get_strategy_signals(
    strategy_id: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
    limit: int = 50,
) -> list[dict]:
    limit = max(1, min(limit, 200))
    redis = request.app.state.redis
    raw = await redis.lrange(f"lab:signals:{strategy_id}", 0, limit - 1)
    results = []
    for item in raw:
        try:
            results.append(json.loads(item))
        except Exception:
            continue
    return results


@router.post("/validate")
async def validate_strategy(
    body: ValidateRequest,
    _: Annotated[TokenData, _trader],
) -> dict:
    """Dry-run: compile and safety-check without registering."""
    cls, errors = _sandbox.run(body.source)
    name = getattr(cls, "name", None) if cls else None
    return {
        "valid":         len(errors) == 0,
        "errors":        errors,
        "strategy_name": name,
    }


# ── WebSocket: real-time signal stream for a strategy ────────────────────────

@router.websocket("/ws/lab/{strategy_id}")
async def ws_lab_signals(
    websocket: WebSocket,
    strategy_id: str,
    token: str,
) -> None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    registry = websocket.app.state.strategy_registry
    if not registry.get(strategy_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    redis  = websocket.app.state.redis
    pubsub = redis.pubsub()
    # Subscribe to the broadcast channel the registry always publishes to
    await pubsub.subscribe("lab:signal:*")

    try:
        async for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            try:
                data = json.loads(msg["data"])
                if data.get("strategy_id") == strategy_id:
                    await websocket.send_text(msg["data"])
            except WebSocketDisconnect:
                break
            except Exception:
                continue
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
