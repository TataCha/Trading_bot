import pandas as pd
from tabulate import tabulate
from backtest.engine import BacktestEngine
from backtest.performance import calculate_performance_metrics
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.rsi_reversion import RSIReversionStrategy
from src.strategy.ma_crossover import MovingAverageCrossoverStrategy
from src.data.collector import MarketDataCollector
from config.settings import get_settings

# Symbol-to-Strategy Mapping based on quantitative backtest benchmark
PORTFOLIO_STRATEGY_MAP = {
    "NVDA": RSIReversionStrategy(),
    "AAPL": VWAPBreakoutStrategy(),
    "MSFT": MovingAverageCrossoverStrategy(),
    "AMD": MovingAverageCrossoverStrategy(),
    "DRAM": RSIReversionStrategy(),
    "TSM": RSIReversionStrategy()
}

def main():
    settings = get_settings()
    collector = MarketDataCollector(settings=settings)
    days_back = 45

    print(f"\n=======================================================")
    print(f"💼 MULTI-STRATEGY PORTFOLIO BACKTEST ({days_back} DAYS)")
    print(f"=======================================================")

    all_trades = []
    symbol_results = []
    initial_capital = 100000.0

    for symbol, strategy_inst in PORTFOLIO_STRATEGY_MAP.items():
        print(f"Fetching historical bars and testing {symbol} with [{strategy_inst.name}]...")
        df_hist = collector.fetch_historical_bars(symbol=symbol, timeframe="15Min", days_back=days_back)
        if df_hist.empty:
            continue

        engine = BacktestEngine(
            strategy_class=type(strategy_inst),
            strategy_params=strategy_inst.get_parameters(),
            initial_capital=initial_capital,
            slippage_pct=0.0005
        )
        res = engine.run(symbol=symbol, df_historical=df_hist)
        metrics = res['metrics']
        trades = res['trades']
        all_trades.extend(trades)

        symbol_results.append({
            "Symbol": symbol,
            "Strategy": strategy_inst.name,
            "Trades": metrics['Total Trades'],
            "Win Rate (%)": metrics['Win Rate (%)'],
            "Return (%)": metrics['Total Return (%)'],
            "Sharpe": metrics['Sharpe Ratio'],
            "Max DD (%)": metrics['Max Drawdown (%)'],
            "Profit Factor": metrics['Profit Factor']
        })

    # Portfolio combined performance
    if all_trades:
        df_all_trades = pd.DataFrame(all_trades).sort_values(by="entry_time")
        # Build portfolio equity curve
        capital = initial_capital
        equity_list = [capital]
        for pnl in df_all_trades['pnl']:
            capital += pnl
            equity_list.append(capital)

        equity_curve = pd.Series(equity_list)
        combined_metrics = calculate_performance_metrics(all_trades, equity_curve, initial_capital)

        print("\n📋 INDIVIDUAL SYMBOL STRATEGY ALLOCATION:")
        print(tabulate(symbol_results, headers='keys', tablefmt='fancy_grid', showindex=False))

        print("\n🏆 COMBINED MULTI-STRATEGY PORTFOLIO RESULTS:")
        table_combined = [[k, v] for k, v in combined_metrics.items()]
        print(tabulate(table_combined, headers=["Portfolio Metric", "Combined Value"], tablefmt="fancy_grid"))

if __name__ == "__main__":
    main()
