import pandas as pd
import numpy as np
from src.data.indicators import add_all_indicators, calculate_vwap, calculate_rsi

def test_vwap_and_rsi_calculation():
    dates = pd.date_range("2026-08-07 09:30", periods=50, freq="15min")
    df = pd.DataFrame({
        'open': np.linspace(100, 110, 50),
        'high': np.linspace(101, 112, 50),
        'low': np.linspace(99, 109, 50),
        'close': np.linspace(100.5, 111, 50),
        'volume': np.full(50, 1000)
    }, index=dates)

    df_ind = add_all_indicators(df)

    assert 'vwap' in df_ind.columns
    assert 'rsi' in df_ind.columns
    assert 'macd' in df_ind.columns
    assert 'sma_20' in df_ind.columns
    assert 'ema_9' in df_ind.columns

    # Verify VWAP values are reasonable
    assert not df_ind['vwap'].isna().all()
    # Verify RSI values fall between 0 and 100
    assert (df_ind['rsi'] >= 0).all() and (df_ind['rsi'] <= 100).all()
