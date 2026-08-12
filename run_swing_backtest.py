import argparse
import pandas as pd
from tabulate import tabulate
from datetime import datetime
from config.settings import get_settings
from src.data.collector import MarketDataCollector
from backtest.engine import BacktestEngine
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.rsi_reversion import RSIReversionStrategy
from src.strategy.ma_crossover import MovingAverageCrossoverStrategy
from src.strategy.swing_trend import SwingTrendPullbackStrategy, SwingBreakoutStrategy

def main():
    parser = argparse.ArgumentParser(description="Multi-Month Weekly/Swing vs Intraday Backtester")
    parser.add_argument("--days", type=int, default=180, help="Number of historical days to backtest (default: 180)")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial portfolio capital")
    args = parser.parse_args()

    settings = get_settings()
    collector = MarketDataCollector(settings=settings)
    symbols = ["NVDA", "AAPL", "MSFT", "AMD", "TSM", "TQQQ", "SOXL"]

    print(f"\n==========================================================================")
    print(f"📊 MULTI-MONTH STRATEGY COMPARISON: SWING (MULTI-DAY) VS INTRADAY (15M)")
    print(f"==========================================================================")
    print(f"Backtest Period   : Last {args.days} Days")
    print(f"Portfolio Capital : ${args.capital:,.2f}")
    print(f"Slippage Model    : 0.05% per order fill buffer")
    print(f"Assets Evaluated  : {symbols}\n")

    # 1. Fetch historical 1-Hour data for Swing and 15-Min data for Intraday
    data_1h = {}
    data_15m = {}

    for sym in symbols:
        print(f"Fetching historical bars for {sym}...")
        df_1h = collector.fetch_historical_bars(symbol=sym, timeframe="1Hour", days_back=args.days)
        df_15m = collector.fetch_historical_bars(symbol=sym, timeframe="15Min", days_back=min(args.days, 60))
        if not df_1h.empty:
            data_1h[sym] = df_1h
        if not df_15m.empty:
            data_15m[sym] = df_15m

    results = []

    # 2. Test Swing Trend Pullback Strategy (1-Hour candles, Multi-Day hold, ATR Trail)
    for sym, df in data_1h.items():
        engine = BacktestEngine(
            strategy_class=SwingTrendPullbackStrategy,
            initial_capital=args.capital,
            allow_overnight=True,
            enable_trailing_stop=True
        )
        res = engine.run(sym, df)
        m = res['metrics']
        results.append({
            "Strategy Type": "🟢 Swing (Pullback)",
            "Timeframe": "1-Hour",
            "Symbol": sym,
            "Trades": m['Total Trades'],
            "Win Rate (%)": f"{m['Win Rate (%)']:.1f}%",
            "Return (%)": f"{m['Total Return (%)']:+.2f}%",
            "Profit Factor": f"{m['Profit Factor']:.2f}",
            "Sharpe": f"{m['Sharpe Ratio']:.2f}",
            "Max DD (%)": f"{m['Max Drawdown (%)']:.2f}%",
            "Final Equity ($)": f"${m['Final Equity ($)']:,.2f}",
            "raw_return": m['Total Return (%)']
        })

    # 3. Test Swing Breakout Strategy (1-Hour candles, Multi-Day hold, ATR Trail)
    for sym, df in data_1h.items():
        engine = BacktestEngine(
            strategy_class=SwingBreakoutStrategy,
            initial_capital=args.capital,
            allow_overnight=True,
            enable_trailing_stop=True
        )
        res = engine.run(sym, df)
        m = res['metrics']
        results.append({
            "Strategy Type": "🟢 Swing (Breakout)",
            "Timeframe": "1-Hour",
            "Symbol": sym,
            "Trades": m['Total Trades'],
            "Win Rate (%)": f"{m['Win Rate (%)']:.1f}%",
            "Return (%)": f"{m['Total Return (%)']:+.2f}%",
            "Profit Factor": f"{m['Profit Factor']:.2f}",
            "Sharpe": f"{m['Sharpe Ratio']:.2f}",
            "Max DD (%)": f"{m['Max Drawdown (%)']:.2f}%",
            "Final Equity ($)": f"${m['Final Equity ($)']:,.2f}",
            "raw_return": m['Total Return (%)']
        })

    # 4. Test Intraday Day Trading Strategies for Comparison (15-Min candles, Forced 3:45 PM EOD Flush)
    for sym, df in data_15m.items():
        engine = BacktestEngine(
            strategy_class=VWAPBreakoutStrategy,
            initial_capital=args.capital,
            allow_overnight=False,
            enable_trailing_stop=False
        )
        res = engine.run(sym, df)
        m = res['metrics']
        results.append({
            "Strategy Type": "🔴 Intraday (VWAP)",
            "Timeframe": "15-Min",
            "Symbol": sym,
            "Trades": m['Total Trades'],
            "Win Rate (%)": f"{m['Win Rate (%)']:.1f}%",
            "Return (%)": f"{m['Total Return (%)']:+.2f}%",
            "Profit Factor": f"{m['Profit Factor']:.2f}",
            "Sharpe": f"{m['Sharpe Ratio']:.2f}",
            "Max DD (%)": f"{m['Max Drawdown (%)']:.2f}%",
            "Final Equity ($)": f"${m['Final Equity ($)']:,.2f}",
            "raw_return": m['Total Return (%)']
        })

    df_res = pd.DataFrame(results)
    df_sorted = df_res.sort_values(by="raw_return", ascending=False).drop(columns=["raw_return"])

    print("\n🏆 COMPREHENSIVE PERFORMANCE MATRIX (RANKED BY NET RETURN):")
    print(tabulate(df_sorted, headers="keys", tablefmt="fancy_grid", showindex=False))

    # Summary grouped by Strategy Type
    print("\n📈 MACRO STRATEGY AGGREGATE PERFORMANCE SUMMARY:")
    agg = df_res.groupby("Strategy Type").agg({
        "raw_return": ["mean", "median", "max", "min"],
        "Trades": "sum"
    }).reset_index()
    agg.columns = ["Strategy Type", "Avg Return (%)", "Median Return (%)", "Max Return (%)", "Min Return (%)", "Total Trades"]
    agg["Avg Return (%)"] = agg["Avg Return (%)"].apply(lambda x: f"{x:+.2f}%")
    agg["Median Return (%)"] = agg["Median Return (%)"].apply(lambda x: f"{x:+.2f}%")
    agg["Max Return (%)"] = agg["Max Return (%)"].apply(lambda x: f"{x:+.2f}%")
    agg["Min Return (%)"] = agg["Min Return (%)"].apply(lambda x: f"{x:+.2f}%")
    print(tabulate(agg, headers="keys", tablefmt="psql", showindex=False))

if __name__ == "__main__":
    main()
