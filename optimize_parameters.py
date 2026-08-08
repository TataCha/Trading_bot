import pandas as pd
from tabulate import tabulate
from backtest.engine import BacktestEngine
from backtest.performance import calculate_performance_metrics
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.rsi_reversion import RSIReversionStrategy
from src.strategy.ma_crossover import MovingAverageCrossoverStrategy
from src.data.collector import MarketDataCollector
from config.settings import get_settings

def run_optimization():
    settings = get_settings()
    collector = MarketDataCollector(settings=settings)
    days_back = 60
    initial_capital = 100000.0

    print(f"\n=======================================================")
    print(f"🎯 STRATEGY OPTIMIZATION ENGINE (TARGET: >= 10% PROFIT)")
    print(f"=======================================================")
    print(f"Testing 60-Day Historical Data across Tech Stock Universe...")

    # Fetch 60-day historical data
    symbols = ["AAPL", "NVDA", "MSFT", "AMD", "TSM"]
    data_cache = {}
    for sym in symbols:
        df = collector.fetch_historical_bars(symbol=sym, timeframe="15Min", days_back=days_back)
        if not df.empty:
            data_cache[sym] = df

    # Test parameter configurations:
    # 1. Conservative (Standard 1:2 R/R): SL 1.5%, TP 3.0%
    # 2. Growth (1:3 R/R): SL 1.5%, TP 4.5%
    # 3. High-Yield Momentum (1:4 R/R): SL 1.5%, TP 6.0%
    # 4. Aggressive Runner (1:5 R/R): SL 1.8%, TP 9.0%

    configs = [
        {"name": "Standard (1:2 R/R)", "sl": 0.015, "tp": 0.030, "risk_pct": 0.02},
        {"name": "Growth (1:3 R/R)", "sl": 0.015, "tp": 0.045, "risk_pct": 0.025},
        {"name": "High-Yield (1:4 R/R)", "sl": 0.015, "tp": 0.060, "risk_pct": 0.03},
        {"name": "Aggressive Trend Runner", "sl": 0.018, "tp": 0.090, "risk_pct": 0.035}
    ]

    opt_results = []

    for cfg in configs:
        portfolio_trades = []
        for sym, df in data_cache.items():
            # Test MA Crossover & VWAP Breakout with config params
            strat_cls = MovingAverageCrossoverStrategy if sym in ["MSFT", "AMD", "NVDA"] else VWAPBreakoutStrategy
            strat = strat_cls(params={
                "stop_loss_pct": cfg["sl"],
                "take_profit_pct": cfg["tp"]
            })

            engine = BacktestEngine(
                strategy_class=strat_cls,
                strategy_params=strat.get_parameters(),
                initial_capital=initial_capital,
                slippage_pct=0.0005
            )
            engine.risk_manager.max_risk_pct = cfg["risk_pct"]

            res = engine.run(symbol=sym, df_historical=df)
            portfolio_trades.extend(res['trades'])

        # Aggregate portfolio equity curve
        if portfolio_trades:
            df_trades = pd.DataFrame(portfolio_trades).sort_values(by="entry_time")
            cap = initial_capital
            eq_list = [cap]
            for pnl in df_trades['pnl']:
                cap += pnl
                eq_list.append(cap)

            eq_series = pd.Series(eq_list)
            metrics = calculate_performance_metrics(portfolio_trades, eq_series, initial_capital)

            opt_results.append({
                "Configuration": cfg["name"],
                "Take-Profit": f"{cfg['tp']*100:.1f}%",
                "Stop-Loss": f"{cfg['sl']*100:.1f}%",
                "Risk/Trade": f"{cfg['risk_pct']*100:.1f}%",
                "Total Return (%)": f"+{metrics['Total Return (%)']:.2f}%",
                "Win Rate (%)": f"{metrics['Win Rate (%)']:.1f}%",
                "Profit Factor": f"{metrics['Profit Factor']:.2f}",
                "Max DD (%)": f"{metrics['Max Drawdown (%)']:.2f}%",
                "Final Capital ($)": f"${metrics['Final Equity ($)']:,.2f}"
            })

    print("\n🏆 PARAMETER OPTIMIZATION MATRIX (60-DAY MULTI-STOCK PORTFOLIO):")
    print(tabulate(opt_results, headers='keys', tablefmt='fancy_grid', showindex=False))

if __name__ == "__main__":
    run_optimization()
