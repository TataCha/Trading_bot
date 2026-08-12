import pandas as pd
from typing import Dict, Any, Optional
from .base import StrategyBase, Signal, SignalType

class SwingTrendPullbackStrategy(StrategyBase):
    """
    Multi-Day / Weekly Swing Trend Pullback Strategy:
    - Identifies sustained uptrends (Price > EMA 50, EMA 50 > EMA 200).
    - Catches healthy 1H/Daily pullbacks to EMA 21 with cooling RSI (35-55).
    - Enters on bullish reversal confirmation with dynamic ATR stop-loss and 2.5:1 R:R.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "ema_fast": 21,
            "ema_slow": 50,
            "ema_trend": 200,
            "rsi_pullback_min": 35,
            "rsi_pullback_max": 55,
            "atr_multiplier": 2.5,
            "risk_reward_ratio": 2.5
        }
        if params:
            default_params.update(params)
        super().__init__(name="Swing_TrendPullback", params=default_params)

    def evaluate(self, symbol: str, df: pd.DataFrame) -> Signal:
        if df.empty or len(df) < 50:
            return Signal(SignalType.HOLD, symbol, 0.0, 0.0, 0.0, "Insufficient bars for swing analysis")

        current = df.iloc[-1]
        prev = df.iloc[-2]

        close = float(current['close'])
        open_ = float(current['open'])
        low = float(current['low'])
        high = float(current['high'])

        ema_21 = float(current.get('ema_21', current.get('ema_9', close)))
        ema_50 = float(current.get('ema_50', close))
        ema_200 = float(current.get('ema_200', ema_50))
        rsi = float(current.get('rsi', 50))
        atr = float(current.get('atr', close * 0.02))

        # Fallback if ATR is 0 or NaN
        if atr <= 0 or pd.isna(atr):
            atr = close * 0.025

        # 1. Macro Trend Filter (Uptrend Structure)
        # Price > EMA 50, and EMA 50 trending above EMA 200 (if enough bars)
        is_uptrend = close > ema_50
        if 'ema_200' in current and not pd.isna(ema_200) and len(df) >= 200:
            is_uptrend = is_uptrend and (ema_50 >= ema_200 * 0.98)

        # 2. Pullback Zone Detection
        # Low touched near EMA 21 and RSI is in pullback zone (35 - 55)
        touched_support = low <= ema_21 * 1.015
        is_rsi_pullback = self.params["rsi_pullback_min"] <= rsi <= self.params["rsi_pullback_max"]

        # 3. Bullish Reversal Confirmation
        # Current bar is green (close > open) or bouncing off support
        is_bullish_bounce = close > open_ and close >= prev['close']

        if is_uptrend and touched_support and is_rsi_pullback and is_bullish_bounce:
            sl_distance = self.params["atr_multiplier"] * atr
            stop_loss = round(close - sl_distance, 2)
            take_profit = round(close + (sl_distance * self.params["risk_reward_ratio"]), 2)

            return Signal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                price=round(close, 2),
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Swing Pullback Bounce (Close: ${close:.2f} > EMA50: ${ema_50:.2f}, RSI: {rsi:.1f}, ATR: ${atr:.2f})"
            )

        return Signal(SignalType.HOLD, symbol, round(close, 2), 0.0, 0.0, "No swing pullback signal")


class SwingBreakoutStrategy(StrategyBase):
    """
    Multi-Day / Weekly Swing Momentum Breakout Strategy:
    - Enters when price breaks above the 20-period Donchian High with volume expansion.
    - Uses ATR-based trailing stop and 2.5:1 Risk-to-Reward.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            "donchian_period": 20,
            "volume_mult": 1.2,
            "atr_multiplier": 2.5,
            "risk_reward_ratio": 2.5
        }
        if params:
            default_params.update(params)
        super().__init__(name="Swing_Breakout", params=default_params)

    def evaluate(self, symbol: str, df: pd.DataFrame) -> Signal:
        if df.empty or len(df) < 30:
            return Signal(SignalType.HOLD, symbol, 0.0, 0.0, 0.0, "Insufficient bars for breakout analysis")

        current = df.iloc[-1]
        prev = df.iloc[-2]

        close = float(current['close'])
        open_ = float(current['open'])
        volume = float(current['volume'])
        atr = float(current.get('atr', close * 0.02))
        ema_50 = float(current.get('ema_50', close))

        # Donchian High of the previous bar (to detect breakout)
        prev_donchian_high = float(prev.get('donchian_high', prev['high']))
        prev_donchian_mid = float(prev.get('donchian_mid', ema_50))

        # Volume moving average
        avg_volume = float(df['volume'].iloc[-21:-1].mean()) if len(df) >= 21 else volume

        if atr <= 0 or pd.isna(atr):
            atr = close * 0.025

        # 1. Breakout condition: Close breaks above previous Donchian High
        is_breakout = close > prev_donchian_high and close > open_

        # 2. Trend & Volume Confirmation
        is_trend_aligned = close > ema_50
        is_volume_confirmed = volume >= avg_volume * self.params["volume_mult"] if avg_volume > 0 else True

        if is_breakout and is_trend_aligned and is_volume_confirmed:
            sl_distance = self.params["atr_multiplier"] * atr
            stop_loss = round(max(prev_donchian_mid, close - sl_distance), 2)
            take_profit = round(close + ((close - stop_loss) * self.params["risk_reward_ratio"]), 2)

            return Signal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                price=round(close, 2),
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Swing 20-Period High Breakout (Close: ${close:.2f} > Donchian: ${prev_donchian_high:.2f}, Vol: {int(volume)} > Avg: {int(avg_volume)})"
            )

        return Signal(SignalType.HOLD, symbol, round(close, 2), 0.0, 0.0, "No swing breakout signal")
