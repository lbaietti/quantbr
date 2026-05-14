"""
Order book imbalance detection.
Detects when bid or ask side is significantly heavier — a leading indicator
used by Neologica BlackArrow and professional order flow traders.
"""
from dataclasses import dataclass


@dataclass
class ImbalanceResult:
    bid_vol: int
    ask_vol: int
    ratio: float          # bid/ask ratio (>1 = bid dominant)
    imbalance_pct: float  # absolute imbalance as % (0–100)
    side: str             # "BID" | "ASK" | "NEUTRAL"
    strong: bool          # True if imbalance_pct > threshold


class BookImbalance:
    """
    Computes bid/ask imbalance from the top N levels of an order book snapshot.
    """

    def __init__(self, threshold_pct: float = 60.0) -> None:
        self._threshold = threshold_pct

    def evaluate(
        self,
        bids: list[dict],   # [{"price":..., "qty":..., "orders":...}]
        asks: list[dict],
        levels: int = 5,
    ) -> ImbalanceResult | None:
        bid_vol = sum(b.get("qty", 0) for b in bids[:levels])
        ask_vol = sum(a.get("qty", 0) for a in asks[:levels])
        total   = bid_vol + ask_vol
        if total == 0:
            return None

        ratio  = bid_vol / ask_vol if ask_vol else float("inf")
        bid_pct = bid_vol / total * 100

        if bid_pct >= self._threshold:
            side   = "BID"
            imb    = bid_pct
        elif (100 - bid_pct) >= self._threshold:
            side   = "ASK"
            imb    = 100 - bid_pct
        else:
            side   = "NEUTRAL"
            imb    = max(bid_pct, 100 - bid_pct)

        return ImbalanceResult(
            bid_vol=bid_vol,
            ask_vol=ask_vol,
            ratio=round(ratio, 2),
            imbalance_pct=round(imb, 1),
            side=side,
            strong=imb >= self._threshold,
        )
