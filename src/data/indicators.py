import pandas as pd
import numpy as np

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculates Intraday Volume Weighted Average Price (VWAP).
    Requires 'high', 'low', 'close', and 'volume' columns. Resets daily.
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    tp_volume = typical_price * df['volume']

    # Group by date for intraday VWAP calculation
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
    else:
        dates = pd.to_datetime(df['timestamp']).dt.date

    cum_tp_volume = tp_volume.groupby(dates).cumsum()
    cum_volume = df['volume'].groupby(dates).cumsum()

    vwap = cum_tp_volume / cum_volume.replace(0, np.nan)
    return vwap.ffill()

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Relative Strength Index (RSI).
    """
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    # Exponential moving average formula for classic Wilder RSI
    gain_ema = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss_ema = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()

    rs = gain_ema / loss_ema.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates Moving Average Convergence Divergence (MACD).
    Returns DataFrame with 'macd', 'macd_signal', 'macd_hist'.
    """
    fast_ema = df['close'].ewm(span=fast, adjust=False).mean()
    slow_ema = df['close'].ewm(span=slow, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line

    return pd.DataFrame({
        'macd': macd_line,
        'macd_signal': signal_line,
        'macd_hist': macd_hist
    }, index=df.index)

def calculate_ma(df: pd.DataFrame, period: int = 20, ma_type: str = 'EMA') -> pd.Series:
    """
    Calculates Simple Moving Average (SMA) or Exponential Moving Average (EMA).
    """
    if ma_type.upper() == 'EMA':
        return df['close'].ewm(span=period, adjust=False).mean()
    else:
        return df['close'].rolling(window=period).mean()

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Average True Range (ATR) for dynamic volatility and trailing stop sizing.
    """
    high = df['high']
    low = df['low']
    close_prev = df['close'].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr.fillna(tr.rolling(period).mean()).fillna(tr)

def calculate_donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculates Donchian Channel breakout levels (High, Low, Mid).
    """
    upper = df['high'].rolling(window=period).max()
    lower = df['low'].rolling(window=period).min()
    mid = (upper + lower) / 2.0

    return pd.DataFrame({
        'donchian_high': upper,
        'donchian_low': lower,
        'donchian_mid': mid
    }, index=df.index)

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Appends VWAP, RSI, MACD, SMA, EMA, ATR, and Donchian indicators to candle DataFrame.
    """
    if df.empty or len(df) < 2:
        return df

    data = df.copy()
    data['vwap'] = calculate_vwap(data)
    data['rsi'] = calculate_rsi(data, period=14)

    macd_df = calculate_macd(data)
    data['macd'] = macd_df['macd']
    data['macd_signal'] = macd_df['macd_signal']
    data['macd_hist'] = macd_df['macd_hist']

    data['sma_20'] = calculate_ma(data, period=20, ma_type='SMA')
    data['ema_9'] = calculate_ma(data, period=9, ma_type='EMA')
    data['ema_21'] = calculate_ma(data, period=21, ma_type='EMA')
    data['ema_50'] = calculate_ma(data, period=50, ma_type='EMA')
    data['ema_200'] = calculate_ma(data, period=200, ma_type='EMA')

    data['atr'] = calculate_atr(data, period=14)

    donchian_df = calculate_donchian(data, period=20)
    data['donchian_high'] = donchian_df['donchian_high']
    data['donchian_low'] = donchian_df['donchian_low']
    data['donchian_mid'] = donchian_df['donchian_mid']

    return data

