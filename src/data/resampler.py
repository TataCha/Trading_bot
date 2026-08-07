import pandas as pd
from typing import Dict

class CandleResampler:
    """
    Resamples 1-minute OHLCV bar data into 15-minute candles.
    Maintains clean memory buffer per symbol.
    """

    def __init__(self, target_tf: str = "15min"):
        self.target_tf = target_tf
        self._buffers: Dict[str, pd.DataFrame] = {}

    def append_bar(self, symbol: str, timestamp: pd.Timestamp, open_: float, high: float, low: float, close: float, volume: float) -> pd.DataFrame:
        """
        Appends a 1-minute bar to the symbol buffer and returns the updated 15-minute candle DataFrame.
        """
        new_row = pd.DataFrame([{
            'timestamp': timestamp,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        }]).set_index('timestamp')

        if symbol not in self._buffers or self._buffers[symbol].empty:
            self._buffers[symbol] = new_row
        else:
            self._buffers[symbol] = pd.concat([self._buffers[symbol], new_row])
            # Retain up to 2000 bars for performance optimization
            if len(self._buffers[symbol]) > 2000:
                self._buffers[symbol] = self._buffers[symbol].iloc[-2000:]

        return self.resample(symbol)

    def resample(self, symbol: str) -> pd.DataFrame:
        """
        Resamples the buffered 1-minute bars into 15-minute standard OHLCV candles.
        """
        if symbol not in self._buffers or self._buffers[symbol].empty:
            return pd.DataFrame()

        df_1m = self._buffers[symbol]

        resampled = df_1m.resample(self.target_tf).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return resampled

    def load_historical(self, symbol: str, df_historical: pd.DataFrame):
        """
        Loads pre-fetched historical bars directly into buffer.
        """
        if 'timestamp' in df_historical.columns:
            df = df_historical.set_index('timestamp')
        else:
            df = df_historical

        self._buffers[symbol] = df
