import pandas as pd
from typing import Dict, Any, Optional
from .base import StrategyBase, Signal, SignalType

class VWAPBreakoutStrategy(StrategyBase):
    """
    VWAP Breakout Strategy:
    Generates a BUY signal when the 15m candle close breaks above VWAP with above-average volume expansion
    and bullish RSI momentum (> 50).
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'volume_factor': 1.2,
            'min_rsi': 50.0,
            'stop_loss_pct': 0.015,   # 1.5% stop loss
            'take_profit_pct': 0.030   # 3.0% take profit (1:2 R/R)
        }
        if params:
            default_params.update(params)
        super().__init__(name="VWAP_Breakout", params=default_params)

    def evaluate(self, symbol: str, df_15m: pd.DataFrame) -> Signal:
        if df_15m is None or len(df_15m) < 20:
            return Signal(SignalType.HOLD, symbol, 0.0, 0.0, 0.0, "Insufficient historical data")

        latest = df_15m.iloc[-1]
        prev = df_15m.iloc[-2]

        close = float(latest['close'])
        vwap = float(latest.get('vwap', 0.0))
        rsi = float(latest.get('rsi', 50.0))
        volume = float(latest['volume'])

        # Calculate 20-period average volume
        avg_vol = df_15m['volume'].iloc[-20:].mean()

        prev_close = float(prev['close'])
        prev_vwap = float(prev.get('vwap', 0.0))

        # Condition 1: Bullish VWAP crossover (previous close <= VWAP, current close > VWAP)
        vwap_crossover = (prev_close <= prev_vwap) and (close > vwap)

        # Condition 2: Volume expansion
        vol_expansion = volume >= (avg_vol * self.params['volume_factor'])

        # Condition 3: RSI confirmation
        rsi_bullish = rsi >= self.params['min_rsi']

        if vwap_crossover and vol_expansion and rsi_bullish:
            sl_price = close * (1.0 - self.params['stop_loss_pct'])
            tp_price = close * (1.0 + self.params['take_profit_pct'])
            reason = f"VWAP Breakout detected (Close: ${close:.2f} > VWAP: ${vwap:.2f}, Vol: {volume:.0f} > Avg: {avg_vol:.0f}, RSI: {rsi:.1f})"
            return Signal(SignalType.BUY, symbol, close, sl_price, tp_price, reason)

        return Signal(SignalType.HOLD, symbol, close, 0.0, 0.0, "No breakout pattern met")
