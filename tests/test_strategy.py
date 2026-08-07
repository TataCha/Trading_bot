import pandas as pd
import numpy as np
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.base import SignalType
from src.data.indicators import add_all_indicators

def test_vwap_breakout_strategy():
    strategy = VWAPBreakoutStrategy()
    dates = pd.date_range("2026-08-07 09:30", periods=25, freq="15min")

    df = pd.DataFrame({
        'open': [100.0] * 25,
        'high': [102.0] * 25,
        'low': [99.0] * 25,
        'close': [100.0] * 23 + [99.0, 105.0],  # Spike close on last bar
        'volume': [10000] * 24 + [50000]       # Big volume surge on last bar
    }, index=dates)

    df_ind = add_all_indicators(df)
    signal = strategy.evaluate("AAPL", df_ind)

    assert signal is not None
    assert hasattr(signal, 'signal_type')
    assert hasattr(signal, 'stop_loss')
    assert hasattr(signal, 'take_profit')
