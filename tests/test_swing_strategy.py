import pytest
import pandas as pd
import numpy as np
from src.strategy.swing_trend import SwingTrendPullbackStrategy, SwingBreakoutStrategy
from src.strategy.base import SignalType
from src.data.indicators import add_all_indicators

def generate_mock_swing_data(num_bars=100, trend="up"):
    dates = pd.date_range("2026-01-01", periods=num_bars, freq="1h")
    np.random.seed(42)

    base = 100.0
    prices = [base]
    for _ in range(num_bars - 1):
        step = np.random.normal(0.5 if trend == "up" else -0.5, 1.0)
        prices.append(prices[-1] + step)

    prices = np.array(prices)
    highs = prices + np.random.uniform(0.5, 1.5, num_bars)
    lows = prices - np.random.uniform(0.5, 1.5, num_bars)
    opens = prices + np.random.uniform(-0.5, 0.5, num_bars)
    closes = prices
    volumes = np.random.uniform(10000, 50000, num_bars)

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return add_all_indicators(df)

def test_swing_trend_pullback_evaluation():
    df = generate_mock_swing_data(num_bars=120, trend="up")
    strategy = SwingTrendPullbackStrategy()
    signal = strategy.evaluate("NVDA", df)
    assert signal.signal_type in [SignalType.BUY, SignalType.HOLD]
    assert signal.symbol == "NVDA"
    if signal.signal_type == SignalType.BUY:
        assert signal.stop_loss < signal.price
        assert signal.take_profit > signal.price

def test_swing_breakout_evaluation():
    df = generate_mock_swing_data(num_bars=120, trend="up")
    strategy = SwingBreakoutStrategy()
    signal = strategy.evaluate("TQQQ", df)
    assert signal.signal_type in [SignalType.BUY, SignalType.HOLD]
    assert signal.symbol == "TQQQ"
    if signal.signal_type == SignalType.BUY:
        assert signal.stop_loss < signal.price
        assert signal.take_profit > signal.price
