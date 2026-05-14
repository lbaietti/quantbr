from datetime import datetime
from pydantic import BaseModel


class L2LevelOut(BaseModel):
    price: float
    qty: int
    orders: int


class SnapshotOut(BaseModel):
    security_id: int
    symbol: str
    ts: datetime
    best_bid: float | None
    best_ask: float | None
    bid_qty: int | None
    ask_qty: int | None
    spread: float | None
    mid: float | None
    last_trade_price: float | None
    last_trade_qty: int | None
    vwap: float | None
    total_traded_qty: int | None
    total_traded_value: float | None
    bids: list[L2LevelOut] = []
    asks: list[L2LevelOut] = []


class TradeOut(BaseModel):
    security_id: int
    symbol: str
    ts: datetime
    price: float
    qty: int
    aggressor_side: str


class InstrumentOut(BaseModel):
    security_id: int
    symbol: str
    security_type: str
    currency: str
    lot_size: int
    maturity_date: str | None = None
    strike_price: float | None = None
    put_or_call: str | None = None
