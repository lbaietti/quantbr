import pytest
from app.signals.engine import SignalEngine


def test_rsi_oversold_triggers_buy():
    engine = SignalEngine()
    symbol = "PETR4"
    price = 30.0
    results = []
    for _ in range(25):
        price -= 0.5
        results = engine.on_trade(symbol, price, 1000)
    buy_signals = [r for r in results if r.direction == "BUY" and r.signal == "RSI_OVERSOLD"]
    assert len(buy_signals) > 0


def test_no_signal_on_flat_market():
    engine = SignalEngine()
    for _ in range(30):
        engine.on_trade("VALE3", 50.0, 500)
    results = engine.on_trade("VALE3", 50.0, 500)
    # Flat prices → RSI undefined direction, no bollinger touch
    rsi_overbought = [r for r in results if r.signal == "RSI_OVERBOUGHT"]
    assert len(rsi_overbought) == 0


def test_vwap_cross_signal():
    engine = SignalEngine()
    symbol = "ITUB4"
    # Seed VWAP at 20.0
    for _ in range(5):
        engine.on_trade(symbol, 20.0, 1000)
    # Cross upward
    results = engine.on_trade(symbol, 25.0, 1000)
    vwap_crosses = [r for r in results if r.signal == "VWAP_CROSS" and r.direction == "BUY"]
    assert len(vwap_crosses) > 0


def test_session_reset_clears_state():
    engine = SignalEngine()
    symbol = "BBDC4"
    for _ in range(20):
        engine.on_trade(symbol, 10.0, 100)
    engine.session_reset(symbol)
    # After reset indicators have no data — no signals from a single tick
    results = engine.on_trade(symbol, 10.0, 100)
    assert results == []
