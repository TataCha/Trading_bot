import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Callable, Dict, Optional
import requests

from config.settings import Settings, get_settings
from src.utils.time_utils import get_est_now

logger = logging.getLogger("TradingBot.DataCollector")

class MarketDataCollector:
    """
    Manages historical market data retrieval and real-time data streaming via Alpaca API.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.ALPACA_API_KEY
        self.secret_key = self.settings.ALPACA_SECRET_KEY
        self.data_url = self.settings.ALPACA_DATA_URL
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key
        }

    def fetch_historical_bars(
        self,
        symbol: str,
        timeframe: str = "15Min",
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Fetches historical OHLCV bars from Alpaca Data REST API for indicator warm-up or backtesting.
        """
        end_dt = get_est_now()
        start_dt = end_dt - timedelta(days=days_back)

        url = f"{self.data_url}/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "start": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": 10000,
            "adjustment": "all",
            "feed": "sip" if self.settings.TRADING_MODE.lower() == "live" else "iex"
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to fetch historical bars for {symbol}: {response.status_code} - {response.text}")
                return pd.DataFrame()

            data = response.json()
            bars = data.get("bars", [])
            if not bars:
                logger.warning(f"No historical bars returned for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(bars)
            df.rename(columns={
                't': 'timestamp',
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume'
            }, inplace=True)

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            logger.info(f"Fetched {len(df)} historical bars for {symbol} ({timeframe})")
            return df

        except Exception as e:
            logger.error(f"Error requesting historical data for {symbol}: {e}")
            return pd.DataFrame()

    async def start_stream(
        self,
        symbols: List[str],
        on_bar_callback: Callable[[str, pd.Timestamp, float, float, float, float, float], None]
    ):
        """
        Subscribes to real-time 1-minute streaming bars via WebSockets (or Polling fallback).
        """
        logger.info(f"Subscribing to real-time stream for symbols: {symbols}")
        # Try alpaca-py stream if available, otherwise use polling loop fallback for robust background execution
        try:
            from alpaca.data.live import StockDataStream
            stream = StockDataStream(self.api_key, self.secret_key)

            async def bar_handler(bar):
                on_bar_callback(
                    bar.symbol,
                    pd.to_datetime(bar.timestamp),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume
                )

            for sym in symbols:
                stream.subscribe_bars(bar_handler, sym)

            logger.info("Alpaca WebSocket stream connected.")
            await stream._run_forever()

        except Exception as e:
            logger.warning(f"WebSocket stream error ({e}). Switching to resilient polling fallback...")
            await self._run_polling_stream(symbols, on_bar_callback)

    async def _run_polling_stream(
        self,
        symbols: List[str],
        on_bar_callback: Callable[[str, pd.Timestamp, float, float, float, float, float], None]
    ):
        """
        Fallback polling loop fetching latest minute bar every 15 seconds.
        """
        logger.info("Started market data polling stream fallback.")
        last_seen_time: Dict[str, pd.Timestamp] = {}

        while True:
            try:
                for symbol in symbols:
                    url = f"{self.data_url}/v2/stocks/{symbol}/bars"
                    params = {
                        "timeframe": "1Min",
                        "limit": 2,
                        "feed": "sip" if self.settings.TRADING_MODE.lower() == "live" else "iex"
                    }
                    res = requests.get(url, headers=self.headers, params=params, timeout=10)
                    if res.status_code == 200:
                        bars = res.json().get("bars", [])
                        if bars:
                            latest = bars[-1]
                            ts = pd.to_datetime(latest["t"])
                            if last_seen_time.get(symbol) != ts:
                                last_seen_time[symbol] = ts
                                on_bar_callback(
                                    symbol,
                                    ts,
                                    float(latest["o"]),
                                    float(latest["h"]),
                                    float(latest["l"]),
                                    float(latest["c"]),
                                    float(latest["v"])
                                )
            except Exception as ex:
                logger.error(f"Polling stream error: {ex}")

            await asyncio.sleep(15)
