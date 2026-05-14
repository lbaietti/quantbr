from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    security_id: Mapped[int]  = mapped_column(Integer, nullable=False, index=True)
    symbol: Mapped[str]       = mapped_column(String(12), nullable=False)
    ts: Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[float]      = mapped_column(Float, nullable=False)
    qty: Mapped[int]          = mapped_column(BigInteger, nullable=False)
    aggressor_side: Mapped[str] = mapped_column(String(1), nullable=False)  # 'B' or 'S'
