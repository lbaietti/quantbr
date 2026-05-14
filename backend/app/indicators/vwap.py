from app.indicators.base import Indicator


class SessionVWAP(Indicator):
    """Intraday VWAP — reset at each session open."""

    def __init__(self) -> None:
        self._sum_pq = 0.0   # sum(price * qty)
        self._sum_q  = 0.0   # sum(qty)

    def update(self, value: float) -> None:
        raise NotImplementedError("Use update_trade(price, qty) instead.")

    def update_trade(self, price: float, qty: int) -> None:
        self._sum_pq += price * qty
        self._sum_q  += qty

    def value(self) -> float | None:
        if self._sum_q == 0.0:
            return None
        return self._sum_pq / self._sum_q

    def reset(self) -> None:
        self._sum_pq = 0.0
        self._sum_q  = 0.0
