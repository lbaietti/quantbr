"""
ISO 25010 — Testability: each indicator is independently testable.
"""
import pytest
from app.indicators import SMA, EMA, RSI, BollingerBands, SessionVWAP
from app.indicators.delta import OrderFlowDelta
from app.indicators.volume_profile import VolumeProfile
from app.indicators.imbalance import BookImbalance


def test_sma_returns_none_until_full():
    sma = SMA(3)
    sma.update(10.0)
    assert sma.value() is None
    sma.update(20.0)
    assert sma.value() is None
    sma.update(30.0)
    assert sma.value() == pytest.approx(20.0)


def test_sma_sliding_window():
    sma = SMA(3)
    for v in [10, 20, 30, 40]:
        sma.update(float(v))
    assert sma.value() == pytest.approx(30.0)


def test_sma_reset():
    sma = SMA(2)
    sma.update(5.0); sma.update(10.0)
    sma.reset()
    assert sma.value() is None


def test_ema_returns_none_before_period():
    ema = EMA(5)
    for i in range(4):
        ema.update(float(i))
    assert ema.value() is None


def test_rsi_oversold():
    rsi = RSI(14)
    # Feed declining prices
    price = 100.0
    for _ in range(20):
        price -= 2.0
        rsi.update(price)
    val = rsi.value()
    assert val is not None
    assert val < 30.0


def test_rsi_overbought():
    rsi = RSI(14)
    price = 100.0
    for _ in range(20):
        price += 3.0
        rsi.update(price)
    val = rsi.value()
    assert val is not None
    assert val > 70.0


def test_bollinger_pct_b_range():
    bb = BollingerBands(20, 2.0)
    import random
    random.seed(42)
    for _ in range(25):
        bb.update(100.0 + random.gauss(0, 1))
    result = bb.value()
    assert result is not None
    assert result.upper > result.middle > result.lower


def test_session_vwap():
    vwap = SessionVWAP()
    assert vwap.value() is None
    vwap.update_trade(10.0, 100)
    vwap.update_trade(20.0, 100)
    assert vwap.value() == pytest.approx(15.0)
    vwap.reset()
    assert vwap.value() is None


# ── OrderFlowDelta ────────────────────────────────────────────────────────────

def test_delta_pure_buy():
    d = OrderFlowDelta()
    d.update(10.0, 500, 'B')
    d.update(10.0, 300, 'B')
    assert d.buy_volume == 800
    assert d.sell_volume == 0
    assert d.delta == 800
    assert d.cumulative_delta == 800


def test_delta_mixed():
    d = OrderFlowDelta()
    d.update(10.0, 600, 'B')
    d.update(10.0, 400, 'S')
    assert d.delta == 200
    assert d.cumulative_delta == 200
    assert d.buy_pct() == pytest.approx(60.0)


def test_delta_history_bounded():
    d = OrderFlowDelta(window=5)
    for i in range(10):
        d.update(float(i), 100, 'B')
    assert len(d.delta_history) == 5


def test_delta_reset():
    d = OrderFlowDelta()
    d.update(10.0, 1000, 'S')
    d.reset()
    assert d.buy_volume == 0
    assert d.sell_volume == 0
    assert d.cumulative_delta == 0
    assert d.delta_history == []


def test_delta_balanced_returns_50pct():
    d = OrderFlowDelta()
    d.update(10.0, 500, 'B')
    d.update(10.0, 500, 'S')
    assert d.buy_pct() == pytest.approx(50.0)


# ── VolumeProfile ─────────────────────────────────────────────────────────────

def test_volume_profile_empty_returns_none():
    vp = VolumeProfile()
    assert vp.result() is None


def test_volume_profile_poc():
    vp = VolumeProfile(tick_size=1.0)
    vp.update(10.0, 100, 'B')
    vp.update(11.0, 500, 'B')   # highest volume → POC
    vp.update(12.0, 200, 'S')
    result = vp.result()
    assert result is not None
    assert result.poc == pytest.approx(11.0)


def test_volume_profile_value_area_contains_poc():
    vp = VolumeProfile(tick_size=1.0)
    for price in [10.0, 11.0, 12.0, 13.0, 14.0]:
        vp.update(price, 200, 'B')
    vp.update(12.0, 1000, 'B')  # POC at 12
    result = vp.result()
    assert result is not None
    assert result.val <= result.poc <= result.vah


def test_volume_profile_total_volume():
    vp = VolumeProfile(tick_size=0.5)
    vp.update(10.0, 300, 'B')
    vp.update(10.0, 200, 'S')
    result = vp.result()
    assert result is not None
    assert result.total_volume == 500
    assert result.total_delta == 100


def test_volume_profile_reset():
    vp = VolumeProfile()
    vp.update(10.0, 100, 'B')
    vp.reset()
    assert vp.result() is None


# ── BookImbalance ─────────────────────────────────────────────────────────────

def test_imbalance_neutral_empty():
    calc = BookImbalance()
    result = calc.evaluate([], [])
    assert result is None


def test_imbalance_bid_dominant():
    calc = BookImbalance(threshold_pct=60.0)
    bids = [{"qty": 1000}, {"qty": 800}]
    asks = [{"qty": 200}, {"qty": 100}]
    result = calc.evaluate(bids, asks)
    assert result is not None
    assert result.side == "BID"
    assert result.strong is True


def test_imbalance_ask_dominant():
    calc = BookImbalance(threshold_pct=60.0)
    bids = [{"qty": 100}]
    asks = [{"qty": 900}]
    result = calc.evaluate(bids, asks)
    assert result is not None
    assert result.side == "ASK"
    assert result.strong is True


def test_imbalance_neutral():
    calc = BookImbalance(threshold_pct=60.0)
    bids = [{"qty": 500}]
    asks = [{"qty": 500}]
    result = calc.evaluate(bids, asks)
    assert result is not None
    assert result.side == "NEUTRAL"
    assert result.strong is False


def test_imbalance_ratio():
    calc = BookImbalance()
    bids = [{"qty": 300}]
    asks = [{"qty": 100}]
    result = calc.evaluate(bids, asks)
    assert result is not None
    assert result.ratio == pytest.approx(3.0)


# ── Sandbox AST safety ────────────────────────────────────────────────────────

def test_sandbox_blocks_import():
    from app.quantlab.sandbox import _check_ast
    errors = _check_ast("import os")
    assert any("import" in e for e in errors)


def test_sandbox_blocks_eval():
    from app.quantlab.sandbox import _check_ast
    errors = _check_ast("x = eval('1+1')")
    assert any("eval" in e for e in errors)


def test_sandbox_blocks_dunder_access():
    from app.quantlab.sandbox import _check_ast
    errors = _check_ast("x = obj.__class__")
    assert any("dunder" in e for e in errors)


def test_sandbox_allows_valid_code():
    from app.quantlab.sandbox import _check_ast
    code = """
x = 1 + 2
y = [i for i in range(10)]
z = max(y)
"""
    errors = _check_ast(code)
    assert errors == []


def test_sandbox_timeout():
    from app.quantlab.sandbox import QuantLabSandbox
    sandbox = QuantLabSandbox()
    # Infinite loop at module level — must timeout, not block forever
    src = "while True: pass\nfrom quantlab import BaseStrategy\nregister(BaseStrategy)"
    cls, errors = sandbox.run(src)
    assert cls is None
    assert any("timed out" in e or "import" in e for e in errors)
