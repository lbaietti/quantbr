from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Instrument(Base):
    __tablename__ = "instruments"

    security_id: Mapped[int]    = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str]         = mapped_column(String(12), nullable=False, index=True)
    security_type: Mapped[str]  = mapped_column(String(8), nullable=False)   # CS, FUT, OPT
    currency: Mapped[str]       = mapped_column(String(4), nullable=False, default="BRL")
    lot_size: Mapped[int]       = mapped_column(Integer, nullable=False, default=100)
    min_trade_vol: Mapped[int]  = mapped_column(Integer, nullable=False, default=100)
    # For futures/options
    maturity_date: Mapped[str | None]  = mapped_column(String(10), nullable=True)
    strike_price: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)
    put_or_call: Mapped[str | None]    = mapped_column(String(2), nullable=True)
