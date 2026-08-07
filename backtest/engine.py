import logging
import pandas as pd
from typing import Dict, Any, List, Type
from src.strategy.base import StrategyBase, SignalType
from src.data.indicators import add_all_indicators
from src.risk.risk_manager import RiskManager
from .performance import calculate_performance_metrics

logger = logging.getLogger("Backtester")

class BacktestEngine:
    """
    Event-driven Historical Backtesting Engine:
    - Simulates 15-minute candlestick strategy signals.
    - Incorporates realistic 0.05% slippage and bid-ask spread buffers per order.
    - Evaluates Risk Management (2% fixed risk sizing, SL/TP execution, EOD position flushing).
    """

    def __init__(
        self,
        strategy_class: Type[StrategyBase],
        strategy_params: Dict[str, Any] = None,
        initial_capital: float = 100000.0,
        slippage_pct: float = 0.0005,  # 0.05% slippage buffer
        commission_per_share: float = 0.0
    ):
        self.strategy = strategy_class(params=strategy_params)
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.slippage_pct = slippage_pct
        self.commission_per_share = commission_per_share
        self.risk_manager = RiskManager()

    def run(self, symbol: str, df_historical: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes backtest over historical 15-minute bar DataFrame.
        """
        logger.info(f"Starting Backtest for {symbol} with strategy {self.strategy.name} ({len(df_historical)} bars)...")

        # 1. Prepare indicators
        df = add_all_indicators(df_historical.copy())

        trades: List[Dict[str, Any]] = []
        equity_series = []
        timestamps = []

        position: Optional[Dict[str, Any]] = None

        # Iterate over bars (starting at index 30 for indicator warm-up)
        for i in range(30, len(df)):
            df_slice = df.iloc[:i+1]
            current_bar = df_slice.iloc[-1]
            current_time = df_slice.index[-1]

            close_price = float(current_bar['close'])
            high_price = float(current_bar['high'])
            low_price = float(current_bar['low'])

            # 2. Check open position for Stop Loss / Take Profit / EOD exit
            if position is not None:
                qty = position['qty']
                entry_price = position['entry_price']
                sl_price = position['sl_price']
                tp_price = position['tp_price']

                exit_price = None
                exit_reason = ""

                # Check Stop Loss hit
                if low_price <= sl_price:
                    exit_price = sl_price * (1.0 - self.slippage_pct)
                    exit_reason = "Stop Loss Hit"
                # Check Take Profit hit
                elif high_price >= tp_price:
                    exit_price = tp_price * (1.0 - self.slippage_pct)
                    exit_reason = "Take Profit Hit"
                # Check EOD flush (3:45 PM EST)
                elif hasattr(current_time, "hour") and (current_time.hour == 15 and current_time.minute >= 45):
                    exit_price = close_price * (1.0 - self.slippage_pct)
                    exit_reason = "EOD Flush"

                if exit_price is not None:
                    pnl = (exit_price - entry_price) * qty
                    self.capital += (exit_price * qty) - (qty * self.commission_per_share)

                    trades.append({
                        "symbol": symbol,
                        "entry_time": position['entry_time'],
                        "exit_time": current_time,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "qty": qty,
                        "pnl": pnl,
                        "return_pct": ((exit_price - entry_price) / entry_price) * 100.0,
                        "exit_reason": exit_reason
                    })
                    position = None

            # 3. If no open position, evaluate strategy for BUY signal
            if position is None:
                signal = self.strategy.evaluate(symbol, df_slice)
                if signal.signal_type == SignalType.BUY:
                    # Apply buy slippage (+0.05%)
                    buy_price = close_price * (1.0 + self.slippage_pct)
                    sl = signal.stop_loss
                    tp = signal.take_profit

                    # Risk Sizing
                    qty = self.risk_manager.calculate_position_size(
                        entry_price=buy_price,
                        stop_loss_price=sl,
                        account_equity=self.capital
                    )

                    cost = (buy_price * qty) + (qty * self.commission_per_share)
                    if qty > 0 and self.capital >= cost:
                        self.capital -= cost
                        position = {
                            "symbol": symbol,
                            "entry_time": current_time,
                            "entry_price": buy_price,
                            "sl_price": sl,
                            "tp_price": tp,
                            "qty": qty
                        }

            # 4. Calculate mark-to-market total portfolio equity
            current_portfolio_value = self.capital
            if position is not None:
                current_portfolio_value += (close_price * position['qty'])

            equity_series.append(current_portfolio_value)
            timestamps.append(current_time)

        # Force liquidate any leftover position at end of historical dataset
        if position is not None:
            last_bar = df.iloc[-1]
            last_price = float(last_bar['close']) * (1.0 - self.slippage_pct)
            qty = position['qty']
            pnl = (last_price - position['entry_price']) * qty
            self.capital += (last_price * qty)
            trades.append({
                "symbol": symbol,
                "entry_time": position['entry_time'],
                "exit_time": df.index[-1],
                "entry_price": position['entry_price'],
                "exit_price": last_price,
                "qty": qty,
                "pnl": pnl,
                "return_pct": ((last_price - position['entry_price']) / position['entry_price']) * 100.0,
                "exit_reason": "End of Dataset"
            })
            position = None

        equity_curve = pd.Series(equity_series, index=timestamps)
        metrics = calculate_performance_metrics(trades, equity_curve, self.initial_capital)

        return {
            "symbol": symbol,
            "strategy": self.strategy.name,
            "metrics": metrics,
            "trades": trades,
            "equity_curve": equity_curve
        }
