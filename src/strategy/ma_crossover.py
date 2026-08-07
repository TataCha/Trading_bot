import pandas as pd
from typing import Dict, Any, Optional
from .base import StrategyBase, Signal, SignalType

class MovingAverageCrossoverStrategy(StrategyBase):
    """
    Moving Average Crossover Strategy:
    Generates a BUY signal when EMA 9 crosses above EMA 21 on the 15-minute timeframe while price is above VWAP.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'stop_loss_pct': 0.015,   # 1.5% stop loss
            'take_profit_pct': 0.030   # 3.0% take profit
        }
        if params:
            default_params.update(params)
        super().__init__(name="MA_Crossover", params=default_params)

    def evaluate(self, symbol: str, df_15m: pd.DataFrame) -> Signal:
        if df_15m is None or len(df_15m) < 25:
            return Signal(SignalType.HOLD, symbol, 0.0, 0.0, 0.0, "Insufficient data")

        latest = df_15m.iloc[-1]
        prev = df_15m.iloc[-2]

        close = float(latest['close'])
        vwap = float(latest.get('vwap', 0.0))
        ema_9 = float(latest.get('ema_9', 0.0))
        ema_21 = float(latest.get('ema_21', 0.0))

        prev_ema_9 = float(prev.get('ema_9', 0.0))
        prev_ema_21 = float(prev.get('ema_21', 0.0))

        # Condition 1: EMA 9 crosses above EMA 21
        golden_cross = (prev_ema_9 <= prev_ema_21) and (ema_9 > ema_21)

        # Condition 2: Trend filter - price above VWAP
        above_vwap = close > vwap

        if golden_cross and above_vwap:
            sl_price = close * (1.0 - self.params['stop_loss_pct'])
            tp_price = close * (1.0 + self.params['take_profit_pct'])
            reason = f"EMA 9/21 Golden Cross above VWAP (Close: ${close:.2f}, EMA9: ${ema_9:.2f} > EMA21: ${ema_21:.2f})"
            return Signal(SignalType.BUY, symbol, close, sl_price, tp_price, reason)

        return Signal(SignalType.HOLD, symbol, close, 0.0, 0.0, "No MA crossover signal")
