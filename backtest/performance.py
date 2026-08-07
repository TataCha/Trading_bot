import numpy as np
import pandas as pd
from typing import Dict, Any, List

def calculate_performance_metrics(
    trades: List[Dict[str, Any]],
    equity_curve: pd.Series,
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    Computes key performance indicators (KPIs) for strategy evaluation:
    Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor, Total Return %.
    """
    if not trades or equity_curve.empty:
        return {
            "Total Trades": 0,
            "Winning Trades": 0,
            "Losing Trades": 0,
            "Win Rate (%)": 0.0,
            "Total Return (%)": 0.0,
            "Sharpe Ratio": 0.0,
            "Max Drawdown (%)": 0.0,
            "Profit Factor": 0.0,
            "Final Equity ($)": initial_capital
        }

    df_trades = pd.DataFrame(trades)

    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['pnl'] > 0])
    losing_trades = len(df_trades[df_trades['pnl'] < 0])

    win_rate = (winning_trades / total_trades) * 100.0 if total_trades > 0 else 0.0

    gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)

    final_equity = equity_curve.iloc[-1]
    total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100.0

    # Calculate Drawdown
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown_pct = abs(drawdown.min()) * 100.0

    # Calculate Annualized Sharpe Ratio (assuming 252 trading days, 26 15-min bars/day ~ 6552 periods/year)
    returns = equity_curve.pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252 * 26)
    else:
        sharpe_ratio = 0.0

    return {
        "Total Trades": total_trades,
        "Winning Trades": winning_trades,
        "Losing Trades": losing_trades,
        "Win Rate (%)": round(win_rate, 2),
        "Total Return (%)": round(total_return_pct, 2),
        "Sharpe Ratio": round(sharpe_ratio, 2),
        "Max Drawdown (%)": round(max_drawdown_pct, 2),
        "Profit Factor": round(profit_factor, 2),
        "Final Equity ($)": round(final_equity, 2)
    }
