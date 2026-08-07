import argparse
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tabulate import tabulate

from backtest.engine import BacktestEngine
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.rsi_reversion import RSIReversionStrategy
from src.strategy.ma_crossover import MovingAverageCrossoverStrategy
from src.data.collector import MarketDataCollector
from config.settings import get_settings

STRATEGIES = {
    "vwap_breakout": VWAPBreakoutStrategy,
    "rsi_reversion": RSIReversionStrategy,
    "ma_crossover": MovingAverageCrossoverStrategy
}

def generate_mock_15m_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """
    Generates synthetic 15-minute OHLCV candles with trend and volatility for offline backtesting.
    """
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)

    timestamps = pd.date_range(start=start_dt, end=end_dt, freq='15min')
    # Filter for market hours (9:30 AM to 4:00 PM)
    timestamps = [ts for ts in timestamps if ts.weekday() < 5 and (ts.hour > 9 or (ts.hour == 9 and ts.minute >= 30)) and ts.hour < 16]

    n = len(timestamps)
    np.random.seed(42)

    # Base price trajectory
    base_price = 150.0 if symbol == "AAPL" else (120.0 if symbol == "NVDA" else 400.0)
    returns = np.random.normal(0.0002, 0.004, size=n)
    price_path = base_price * np.exp(np.cumsum(returns))

    df = pd.DataFrame(index=timestamps)
    df['close'] = price_path
    df['open'] = df['close'].shift(1).fillna(base_price)
    df['high'] = df[['open', 'close']].max(axis=1) + np.abs(np.random.normal(0, 0.5, size=n))
    df['low'] = df[['open', 'close']].min(axis=1) - np.abs(np.random.normal(0, 0.5, size=n))
    df['volume'] = np.random.randint(10000, 500000, size=n)

    return df

def main():
    parser = argparse.ArgumentParser(description="Algorithmic Day Trading Bot - Strategy Backtesting CLI")
    parser.add_argument("--symbol", type=str, default="AAPL", help="Stock ticker symbol (e.g. AAPL, NVDA, MSFT, AMD, DRAM, TSM)")
    parser.add_argument("--strategy", type=str, default="vwap_breakout", choices=list(STRATEGIES.keys()), help="Strategy choice")
    parser.add_argument("--days", type=int, default=30, help="Days of historical data to backtest")
    parser.add_argument("--capital", type=float, default=100000.0, help="Initial account equity ($)")
    parser.add_argument("--slippage", type=float, default=0.0005, help="Slippage factor (0.0005 = 0.05 percent)")

    args = parser.parse_args()

    settings = get_settings()
    collector = MarketDataCollector(settings=settings)

    print(f"\n=======================================================")
    print(f"🚀 ALGORITHMIC DAY TRADING BOT - BACKTEST ENGINE")
    print(f"=======================================================")
    print(f"Symbol           : {args.symbol}")
    print(f"Strategy         : {args.strategy}")
    print(f"Historical Days  : {args.days}")
    print(f"Initial Capital  : ${args.capital:,.2f}")
    print(f"Slippage Model   : {args.slippage*100:.2f}%\n")

    # Fetch historical data or generate mock data
    df_data = pd.DataFrame()
    if settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY:
        print("Fetching historical 15-minute bars from Alpaca Data API...")
        df_data = collector.fetch_historical_bars(symbol=args.symbol, timeframe="15Min", days_back=args.days)

    if df_data.empty:
        print("⚠️ Alpaca credentials empty or request limit reached. Generating high-resolution synthetic 15-minute market data...")
        df_data = generate_mock_15m_data(symbol=args.symbol, days=args.days)

    strategy_cls = STRATEGIES[args.strategy]
    engine = BacktestEngine(
        strategy_class=strategy_cls,
        initial_capital=args.capital,
        slippage_pct=args.slippage
    )

    results = engine.run(symbol=args.symbol, df_historical=df_data)

    metrics = results['metrics']
    trades = results['trades']

    table_data = [[k, v] for k, v in metrics.items()]
    print(tabulate(table_data, headers=["Metric", "Value"], tablefmt="fancy_grid"))

    if trades:
        print(f"\n📋 Execution Summary (Total Trades: {len(trades)}) - Recent Trades:")
        trades_df = pd.DataFrame(trades)[['entry_time', 'exit_time', 'entry_price', 'exit_price', 'qty', 'pnl', 'exit_reason']].tail(10)
        print(tabulate(trades_df, headers='keys', tablefmt='psql', showindex=False))
    else:
        print("\nℹ️ No trades were triggered under current strategy rules.")

if __name__ == "__main__":
    main()
