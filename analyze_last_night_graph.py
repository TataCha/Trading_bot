import pandas as pd
import numpy as np
from tabulate import tabulate
from datetime import datetime, timedelta
from config.settings import get_settings
from src.data.collector import MarketDataCollector
from src.data.indicators import add_all_indicators

def main():
    settings = get_settings()
    collector = MarketDataCollector(settings=settings)
    symbols = ["AAPL", "NVDA", "MSFT", "AMD", "DRAM", "TSM", "TQQQ", "SOXL"]

    print("\n==========================================================================")
    print("📈 INTRADAY GRAPH & INTER-MARKET RELATIONSHIP ANALYSIS (LAST NIGHT SESSION)")
    print("==========================================================================")

    data_by_sym = {}
    summary_rows = []
    close_series_dict = {}

    for sym in symbols:
        df = collector.fetch_historical_bars(symbol=sym, timeframe="15Min", days_back=2)
        if df.empty:
            continue

        # Filter for the last completed trading day session (9:30 to 16:00 EST)
        last_date = df.index.date[-1]
        df_session = df[df.index.date == last_date].copy()
        if len(df_session) < 5:
            # If latest date has few bars, use previous trading date
            dates = sorted(list(set(df.index.date)))
            if len(dates) >= 2:
                last_date = dates[-2]
                df_session = df[df.index.date == last_date].copy()

        if df_session.empty:
            continue

        df_session = add_all_indicators(df_session)
        data_by_sym[sym] = df_session
        close_series_dict[sym] = df_session['close']

        day_open = float(df_session.iloc[0]['open'])
        day_high = float(df_session['high'].max())
        day_low = float(df_session['low'].min())
        day_close = float(df_session.iloc[-1]['close'])
        day_volume = int(df_session['volume'].sum())

        net_change_pct = ((day_close - day_open) / day_open) * 100.0
        max_swing_range_pct = ((day_high - day_low) / day_low) * 100.0

        # Calculate Theoretical Best Possible Intraday Profit
        # 1. Low to High Single Perfect Swing Profit
        single_swing_gain_pct = ((day_high - day_low) / day_low) * 100.0

        # 2. Cumulative Multi-Swing Maximum Potential Profit (sum of all positive 15m candle legs)
        candle_gains = (df_session['high'] - df_session['low']) / df_session['low'] * 100.0
        max_possible_multi_swing_profit_pct = candle_gains.sum()

        summary_rows.append({
            "Symbol": sym,
            "Open ($)": f"${day_open:.2f}",
            "High ($)": f"${day_high:.2f}",
            "Low ($)": f"${day_low:.2f}",
            "Close ($)": f"${day_close:.2f}",
            "Net Change": f"{net_change_pct:+.2f}%",
            "Max Swing (Low->High)": f"+{single_swing_gain_pct:.2f}%",
            "Cumulative Multi-Swing Max Potential": f"+{max_possible_multi_swing_profit_pct:.2f}%"
        })

    print(f"\nSession Analyzed: Date {last_date} (Full 15m Candlestick Session)")
    print("\n📊 INTRADAY PRICE ACTION & MAXIMUM PROFIT POTENTIAL:")
    print(tabulate(summary_rows, headers='keys', tablefmt='fancy_grid'))

    # Inter-Market Correlation Matrix
    if len(close_series_dict) >= 2:
        df_corr = pd.DataFrame(close_series_dict).corr()
        print("\n🔗 INTER-MARKET CORRELATION MATRIX (HOW ASSETS MOVED TOGETHER):")
        print(tabulate(df_corr.round(2), headers='keys', tablefmt='psql'))

if __name__ == "__main__":
    main()
