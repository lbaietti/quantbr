"""
Volume Profile — volume distribution at each price level.
Used for POC (Point of Control), VAH (Value Area High), VAL (Value Area Low).
Standard in Neologica BlackArrow and Sierra Chart.
"""
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ProfileLevel:
    price: float
    buy_vol: int
    sell_vol: int

    @property
    def total(self) -> int:
        return self.buy_vol + self.sell_vol

    @property
    def delta(self) -> int:
        return self.buy_vol - self.sell_vol


@dataclass
class ProfileResult:
    levels: list[ProfileLevel]          # sorted by price ascending
    poc: float                           # Point of Control (max volume price)
    vah: float                           # Value Area High (70% of volume above)
    val: float                           # Value Area Low  (70% of volume below)
    total_volume: int
    total_delta: int


class VolumeProfile:
    """
    Session volume profile — tick size defines the price resolution.
    """

    def __init__(self, tick_size: float = 0.01) -> None:
        self._tick    = tick_size
        self._buy:  dict[int, int] = defaultdict(int)   # price_key → qty
        self._sell: dict[int, int] = defaultdict(int)

    def _key(self, price: float) -> int:
        return round(price / self._tick)

    def update(self, price: float, qty: int, aggressor: str) -> None:
        k = self._key(price)
        if aggressor == 'B':
            self._buy[k]  += qty
        else:
            self._sell[k] += qty

    def result(self) -> ProfileResult | None:
        all_keys = set(self._buy) | set(self._sell)
        if not all_keys:
            return None

        levels = [
            ProfileLevel(
                price=k * self._tick,
                buy_vol=self._buy.get(k, 0),
                sell_vol=self._sell.get(k, 0),
            )
            for k in sorted(all_keys)
        ]

        total = sum(l.total for l in levels)
        if total == 0:
            return None

        poc_level = max(levels, key=lambda l: l.total)
        poc = poc_level.price

        # Value Area: 70% of total volume centered on POC
        target = total * 0.70
        poc_idx = levels.index(poc_level)
        included = {poc_idx}
        vol_in_va = poc_level.total

        lo, hi = poc_idx, poc_idx
        while vol_in_va < target:
            expand_lo = lo > 0
            expand_hi = hi < len(levels) - 1
            if not expand_lo and not expand_hi:
                break
            add_lo = levels[lo - 1].total if expand_lo else -1
            add_hi = levels[hi + 1].total if expand_hi else -1
            if add_lo >= add_hi and expand_lo:
                lo -= 1
                vol_in_va += levels[lo].total
            elif expand_hi:
                hi += 1
                vol_in_va += levels[hi].total
            else:
                lo -= 1
                vol_in_va += levels[lo].total

        return ProfileResult(
            levels=levels,
            poc=poc,
            vah=levels[hi].price,
            val=levels[lo].price,
            total_volume=total,
            total_delta=sum(l.delta for l in levels),
        )

    def reset(self) -> None:
        self._buy.clear()
        self._sell.clear()
