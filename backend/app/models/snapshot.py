from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketSnapshot(Base):
    """Persisted L2 order book snapshot (top-of-book for dashboarding)."""
    __tablename__ = "market_snapshots"

    id: Mapped[int]            = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    security_id: Mapped[int]   = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str]        = mapped_column(String(12), nullable=False)
    ts: Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    best_bid: Mapped[float | None]     = mapped_column(Float, nullable=True)
    best_ask: Mapped[float | None]     = mapped_column(Float, nullable=True)
    bid_qty: Mapped[int | None]        = mapped_column(BigInteger, nullable=True)
    ask_qty: Mapped[int | None]        = mapped_column(BigInteger, nullable=True)
    last_trade_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_trade_qty: Mapped[int | None]     = mapped_column(BigInteger, nullable=True)
    vwap: Mapped[float | None]         = mapped_column(Float, nullable=True)
    total_traded_qty: Mapped[int | None]   = mapped_column(BigInteger, nullable=True)
    total_traded_value: Mapped[float | None] = mapped_column(Float, nullable=True)
