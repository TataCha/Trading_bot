import pandas as pd
from typing import Dict, Any, Optional
from .base import StrategyBase, Signal, SignalType

class RSIReversionStrategy(StrategyBase):
    """
    RSI Mean Reversion Strategy:
    Generates a BUY signal when 14-period RSI dips below oversold threshold (< 30) and starts turning up,
    providing high probability pullback entries during intact trends.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'oversold_rsi': 32.0,
            'stop_loss_pct': 0.012,   # 1.2% stop loss
            'take_profit_pct': 0.024   # 2.4% take profit (1:2 R/R)
        }
        if params:
            default_params.update(params)
        super().__init__(name="RSI_MeanReversion", params=default_params)

    def evaluate(self, symbol: str, df_15m: pd.DataFrame) -> Signal:
        if df_15m is None or len(df_15m) < 20:
            return Signal(SignalType.HOLD, symbol, 0.0, 0.0, 0.0, "Insufficient data")

        latest = df_15m.iloc[-1]
        prev = df_15m.iloc[-2]

        close = float(latest['close'])
        rsi = float(latest.get('rsi', 50.0))
        prev_rsi = float(prev.get('rsi', 50.0))

        # Condition: Previous RSI was oversold, and current RSI crosses above oversold line (turning up)
        rsi_reversion = (prev_rsi <= self.params['oversold_rsi']) and (rsi > prev_rsi)

        if rsi_reversion:
            sl_price = close * (1.0 - self.params['stop_loss_pct'])
            tp_price = close * (1.0 + self.params['take_profit_pct'])
            reason = f"RSI Mean Reversion (RSI bounced from {prev_rsi:.1f} to {rsi:.1f} @ ${close:.2f})"
            return Signal(SignalType.BUY, symbol, close, sl_price, tp_price, reason)

        return Signal(SignalType.HOLD, symbol, close, 0.0, 0.0, "RSI neutral")
