"""
Market data endpoints.
ISO 25010 — Performance Efficiency: snapshots served from Redis cache (sub-ms latency).
ISO 27001 A.9.4 — All endpoints require authentication.
"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.instrument import Instrument
from app.models.snapshot import MarketSnapshot
from app.models.trade import Trade
from app.schemas.market import InstrumentOut, SnapshotOut, TradeOut
from app.security.rbac import Role, TokenData, require_role

router = APIRouter()

_viewer = Depends(require_role(Role.VIEWER))


def _redis(request: Request):
    return request.app.state.redis


@router.get("/instruments", response_model=list[InstrumentOut])
async def list_instruments(
    _: Annotated[TokenData, _viewer],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[InstrumentOut]:
    result = await session.execute(select(Instrument).order_by(Instrument.symbol))
    rows = result.scalars().all()
    return [InstrumentOut(
        security_id=r.security_id, symbol=r.symbol,
        security_type=r.security_type, currency=r.currency,
        lot_size=r.lot_size, maturity_date=r.maturity_date,
        strike_price=r.strike_price, put_or_call=r.put_or_call,
    ) for r in rows]


@router.get("/snapshot/{symbol}", response_model=SnapshotOut)
async def get_snapshot(
    symbol: str,
    request: Request,
    _: Annotated[TokenData, _viewer],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SnapshotOut:
    # Try Redis cache first
    redis = _redis(request)
    cached = await redis.get(f"cache:snapshot:{symbol.upper()}")
    if cached:
        data = json.loads(cached)
        return _dict_to_snapshot(data)

    # Fall back to DB
    result = await session.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.ts.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found")

    return SnapshotOut(
        security_id=row.security_id, symbol=row.symbol, ts=row.ts,
        best_bid=row.best_bid, best_ask=row.best_ask,
        bid_qty=row.bid_qty, ask_qty=row.ask_qty,
        spread=(row.best_ask - row.best_bid) if row.best_bid and row.best_ask else None,
        mid=((row.best_bid + row.best_ask) / 2) if row.best_bid and row.best_ask else None,
        last_trade_price=row.last_trade_price, last_trade_qty=row.last_trade_qty,
        vwap=row.vwap, total_traded_qty=row.total_traded_qty,
        total_traded_value=row.total_traded_value,
    )


@router.get("/trades/{symbol}", response_model=list[TradeOut])
async def get_recent_trades(
    symbol: str,
    _: Annotated[TokenData, _viewer],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 50,
) -> list[TradeOut]:
    if limit > 500:
        limit = 500
    result = await session.execute(
        select(Trade)
        .where(Trade.symbol == symbol.upper())
        .order_by(Trade.ts.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [TradeOut(
        security_id=r.security_id, symbol=r.symbol, ts=r.ts,
        price=r.price, qty=r.qty, aggressor_side=r.aggressor_side,
    ) for r in rows]


def _dict_to_snapshot(data: dict) -> SnapshotOut:
    bids = data.get("bids", [])
    asks = data.get("asks", [])
    bb   = bids[0]["price"] if bids else None
    ba   = asks[0]["price"] if asks else None
    return SnapshotOut(
        security_id=data["security_id"],
        symbol=data["symbol"].strip("\x00"),
        ts=data["ts"],
        best_bid=bb, best_ask=ba,
        bid_qty=bids[0]["qty"] if bids else None,
        ask_qty=asks[0]["qty"] if asks else None,
        spread=(ba - bb) if bb and ba else None,
        mid=((bb + ba) / 2) if bb and ba else None,
        last_trade_price=data.get("last_px"),
        last_trade_qty=data.get("last_qty"),
        vwap=data.get("vwap"),
        total_traded_qty=data.get("total_qty"),
        total_traded_value=data.get("total_val"),
        bids=bids, asks=asks,
    )
