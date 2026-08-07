import pandas as pd
from tabulate import tabulate
from backtest.engine import BacktestEngine
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.rsi_reversion import RSIReversionStrategy
from src.strategy.ma_crossover import MovingAverageCrossoverStrategy
from src.data.collector import MarketDataCollector
from config.settings import get_settings

STRATEGIES = {
    "VWAP Breakout": VWAPBreakoutStrategy,
    "RSI Reversion": RSIReversionStrategy,
    "MA Crossover": MovingAverageCrossoverStrategy
}

def main():
    settings = get_settings()
    collector = MarketDataCollector(settings=settings)
    symbols = settings.SYMBOLS  # ["AAPL", "NVDA", "MSFT", "AMD", "DRAM", "TSM"]
    days_back = 45

    print(f"\n=======================================================")
    print(f"📊 STRATEGY BENCHMARK & COMPARISON MATRIX ({days_back} DAYS)")
    print(f"=======================================================")
    print(f"Watchlist Symbols: {symbols}")
    print(f"Strategies Tested : {list(STRATEGIES.keys())}\n")

    # Pre-fetch historical data for all symbols
    data_cache = {}
    for sym in symbols:
        print(f"Fetching historical bars for {sym}...")
        df = collector.fetch_historical_bars(symbol=sym, timeframe="15Min", days_back=days_back)
        if not df.empty:
            data_cache[sym] = df

    results_list = []

    for strat_name, strat_cls in STRATEGIES.items():
        for sym, df in data_cache.items():
            engine = BacktestEngine(
                strategy_class=strat_cls,
                initial_capital=100000.0,
                slippage_pct=0.0005
            )
            res = engine.run(symbol=sym, df_historical=df)
            metrics = res['metrics']

            results_list.append({
                "Strategy": strat_name,
                "Symbol": sym,
                "Trades": metrics['Total Trades'],
                "Win Rate (%)": metrics['Win Rate (%)'],
                "Return (%)": metrics['Total Return (%)'],
                "Sharpe": metrics['Sharpe Ratio'],
                "Max DD (%)": metrics['Max Drawdown (%)'],
                "Profit Factor": metrics['Profit Factor'],
                "Final Equity ($)": metrics['Final Equity ($)']
            })

    df_results = pd.DataFrame(results_list)

    # Sort leaderboard by Return (%) descending
    df_leaderboard = df_results.sort_values(by="Return (%)", ascending=False)

    print("\n🏆 STRATEGY PERFORMANCE LEADERBOARD (RANKED BY RETURN):")
    print(tabulate(df_leaderboard, headers='keys', tablefmt='fancy_grid', showindex=False))

    # Calculate summary average per Strategy across all symbols
    summary = df_results.groupby("Strategy").agg({
        "Return (%)": "mean",
        "Win Rate (%)": "mean",
        "Sharpe": "mean",
        "Max DD (%)": "mean",
        "Profit Factor": "mean",
        "Trades": "sum"
    }).reset_index().sort_values(by="Return (%)", ascending=False)

    print("\n📈 OVERALL STRATEGY RANKINGS (AVERAGED ACROSS ALL WATCHLIST STOCKS):")
    print(tabulate(summary, headers='keys', tablefmt='psql', showindex=False))

if __name__ == "__main__":
    main()
