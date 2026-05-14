from datetime import datetime
from pydantic import BaseModel


class SignalOut(BaseModel):
    symbol: str
    signal: str        # e.g. "RSI_OVERSOLD", "BB_BREAKOUT", "VWAP_CROSS"
    direction: str     # "BUY" | "SELL" | "NEUTRAL"
    strength: float    # 0.0 – 1.0
    ts: datetime
    detail: dict = {}
