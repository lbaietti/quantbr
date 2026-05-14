"""
Order flow delta — buy volume minus sell volume.
Core metric of Neologica BlackArrow / Sierra Chart footprint analysis.
"""
from dataclasses import dataclass, field
from collections import deque


@dataclass
class DeltaBar:
    price: float
    buy_vol: int
    sell_vol: int

    @property
    def delta(self) -> int:
        return self.buy_vol - self.sell_vol

    @property
    def total(self) -> int:
        return self.buy_vol + self.sell_vol


class OrderFlowDelta:
    """
    Tracks buy/sell volume and cumulative delta for a session.
    Also maintains a rolling window for delta divergence detection.
    """

    def __init__(self, window: int = 20) -> None:
        self._buy_vol: int  = 0
        self._sell_vol: int = 0
        self._cum_delta: int = 0
        self._delta_history: deque[int] = deque(maxlen=window)
        self._last_price: float = 0.0

    def update(self, price: float, qty: int, aggressor: str) -> None:
        """aggressor: 'B' = buyer initiated, 'S' = seller initiated."""
        self._last_price = price
        if aggressor == 'B':
            self._buy_vol  += qty
            self._cum_delta += qty
        else:
            self._sell_vol  += qty
            self._cum_delta -= qty
        self._delta_history.append(self._cum_delta)

    @property
    def buy_volume(self) -> int:
        return self._buy_vol

    @property
    def sell_volume(self) -> int:
        return self._sell_vol

    @property
    def delta(self) -> int:
        return self._buy_vol - self._sell_vol

    @property
    def cumulative_delta(self) -> int:
        return self._cum_delta

    @property
    def delta_history(self) -> list[int]:
        return list(self._delta_history)

    def buy_pct(self) -> float:
        total = self._buy_vol + self._sell_vol
        return (self._buy_vol / total * 100) if total else 50.0

    def reset(self) -> None:
        self._buy_vol   = 0
        self._sell_vol  = 0
        self._cum_delta = 0
        self._delta_history.clear()
        self._last_price = 0.0
