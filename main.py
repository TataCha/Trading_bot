import asyncio
import signal
import sys
import logging
import pandas as pd
from typing import Dict

from config.settings import get_settings
from src.monitoring.logger import setup_logger
from src.monitoring.notifier import NotificationEngine
from src.monitoring.health import HealthMonitor
from src.data.collector import MarketDataCollector
from src.data.resampler import CandleResampler
from src.data.indicators import add_all_indicators
from src.strategy.swing_trend import SwingTrendPullbackStrategy, SwingBreakoutStrategy
from src.strategy.vwap_breakout import VWAPBreakoutStrategy
from src.strategy.rsi_reversion import RSIReversionStrategy
from src.strategy.ma_crossover import MovingAverageCrossoverStrategy
from src.risk.risk_manager import RiskManager
from src.risk.eod_flusher import EODFlusher
from src.execution.order_controller import OrderController
from src.utils.time_utils import is_market_open, get_est_now

logger = setup_logger("TradingBot", level="INFO")

# Multi-Strategy Symbol Router: Optimized for Multi-Day / Weekly Swing Trend Trading
DEFAULT_SYMBOL_STRATEGY_MAP: Dict[str, StrategyBase] = {
    "SOXL": SwingBreakoutStrategy(),
    "AMD": SwingBreakoutStrategy(),
    "TSM": SwingBreakoutStrategy(),
    "TQQQ": SwingBreakoutStrategy(),
    "NVDA": SwingTrendPullbackStrategy(),
    "AAPL": SwingTrendPullbackStrategy(),
    "MSFT": SwingBreakoutStrategy(),
    "DRAM": SwingTrendPullbackStrategy()
}

class TradingBotEngine:
    """
    Main Algorithmic Trading Engine Orchestrator.
    Supports Multi-Day / Weekly Swing Trading (1-Hour/Daily) and Intraday Day Trading.
    Maps each stock to its highest performing strategy with ATR Trailing Stops.
    """

    def __init__(self, symbol_strategy_map: Dict[str, StrategyBase] = None):
        self.settings = get_settings()
        self.notifier = NotificationEngine(settings=self.settings)
        self.order_controller = OrderController(settings=self.settings)
        self.risk_manager = RiskManager(settings=self.settings)
        self.eod_flusher = EODFlusher(settings=self.settings)
        self.collector = MarketDataCollector(settings=self.settings)

        # Resample timeframe (e.g., '1h' for swing, '15min' for daytrade)
        tf = "1h" if "1h" in self.settings.TIMEFRAME.lower() else "15min"
        self.resampler = CandleResampler(target_tf=tf)

        # Set symbol strategy map
        self.strategy_map = symbol_strategy_map or DEFAULT_SYMBOL_STRATEGY_MAP
        # Fallback default strategy
        self.default_strategy = SwingBreakoutStrategy() if self.settings.TRADING_STYLE == "swing" else VWAPBreakoutStrategy()

        self.health_monitor = HealthMonitor(
            settings=self.settings,
            callback=self._send_heartbeat
        )
        self.is_running = False

    def get_strategy_for_symbol(self, symbol: str) -> StrategyBase:
        return self.strategy_map.get(symbol, self.default_strategy)

    def _send_heartbeat(self):
        equity = self.order_controller.get_equity()
        positions = self.order_controller.get_positions()
        self.notifier.notify_heartbeat(equity=equity, active_positions=len(positions))

    async def initialize(self):
        logger.info("Initializing Algorithmic Day Trading Engine (Multi-Strategy Asset Router)...")
        logger.info(f"Mode: {self.settings.TRADING_MODE.upper()} | Base URL: {self.settings.ALPACA_BASE_URL}")

        for sym in self.settings.SYMBOLS:
            strat = self.get_strategy_for_symbol(sym)
            logger.info(f"Symbol Routing: {sym} -> Strategy [{strat.name}]")

        # Fetch initial account equity
        equity = self.order_controller.get_equity()
        if equity > 0:
            logger.info(f"Connected to Alpaca Account. Equity: ${equity:,.2f}")
            self.risk_manager.update_account_equity(equity)
        else:
            logger.warning("Could not fetch valid Alpaca equity. Assuming paper mode default ($100,000.00).")
            self.risk_manager.update_account_equity(100000.0)

        # Pre-fetch warm-up historical candles based on configured timeframe
        warmup_tf = "1Hour" if "1h" in self.settings.TIMEFRAME.lower() else "15Min"
        days_back = 45 if "1h" in self.settings.TIMEFRAME.lower() else 10

        for symbol in self.settings.SYMBOLS:
            df_hist = self.collector.fetch_historical_bars(symbol, timeframe=warmup_tf, days_back=days_back)
            if not df_hist.empty:
                self.resampler.load_historical(symbol, df_hist)

        logger.info(f"Warm-up historical candles ({warmup_tf}) loaded successfully.")

    def on_bar_received(self, symbol: str, timestamp: pd.Timestamp, open_: float, high: float, low: float, close: float, volume: float):
        """
        Real-time callback invoked whenever a new 1-minute streaming bar is received.
        """
        # 1. EOD Flush Check (Only if enabled, e.g. Day Trading mode)
        if self.eod_flusher.should_flush():
            open_positions = self.order_controller.get_positions()
            if open_positions:
                logger.warning("EOD Flush Triggered! Closing all open positions...")
                self.order_controller.close_all_positions()
                self.notifier.notify_eod_flush(len(open_positions))
            return

        # 2. Market Open Guard
        if not is_market_open():
            return

        # 3. Append to Candle Resampler (1H for Swing, 15m for Day Trading)
        df_candles = self.resampler.append_bar(symbol, timestamp, open_, high, low, close, volume)
        if df_candles.empty or len(df_candles) < 20:
            return

        # 4. Add technical indicators (ATR, Donchian, EMA, VWAP, RSI, MACD)
        df_candles = add_all_indicators(df_candles)

        # 5. Evaluate Symbol-Specific Strategy Signal
        strategy = self.get_strategy_for_symbol(symbol)
        signal = strategy.evaluate(symbol, df_candles)
        logger.debug(f"Evaluated {symbol} with [{strategy.name}]: {signal}")

        if signal.signal_type.value == "BUY":
            logger.info(f"BUY Signal Triggered for {symbol} using [{strategy.name}]! {signal.reason}")

            # Fetch active position symbols to prevent duplicate re-entries
            positions = self.order_controller.get_positions()
            active_symbols = [p.get('symbol') for p in positions] if isinstance(positions, list) else []

            # 6. Validate Risk Guardrails (Circuit Breaker, PDT Rule, Duplicate Check)
            can_trade, reason = self.risk_manager.can_open_position(symbol, active_positions=active_symbols)
            if not can_trade:
                logger.warning(f"Trade blocked by Risk Manager for {symbol}: {reason}")
                return

            # 7. Calculate 2% Risk Position Sizing
            equity = self.order_controller.get_equity() or 100000.0
            shares = self.risk_manager.calculate_position_size(
                entry_price=signal.price,
                stop_loss_price=signal.stop_loss,
                account_equity=equity
            )

            if shares <= 0:
                logger.warning(f"Position sizing calculated 0 shares for {symbol}. Skipping order.")
                return

            # 8. Submit Alpaca Bracket Order
            order_res = self.order_controller.submit_bracket_order(
                symbol=symbol,
                qty=shares,
                side="buy",
                stop_loss_price=signal.stop_loss,
                take_profit_price=signal.take_profit
            )

            if "error" not in order_res:
                self.risk_manager.record_day_trade()
                self.notifier.notify_trade_entry(
                    symbol=symbol,
                    side="buy",
                    qty=shares,
                    price=signal.price,
                    sl=signal.stop_loss,
                    tp=signal.take_profit,
                    reason=f"[{strategy.name}] {signal.reason}"
                )

    async def start(self):
        self.is_running = True
        await self.initialize()

        # Start health monitor background task
        asyncio.create_task(self.health_monitor.start())

        # Start real-time stream / polling loop
        logger.info("Starting live market data stream subscriber...")
        await self.collector.start_stream(
            symbols=self.settings.SYMBOLS,
            on_bar_callback=self.on_bar_received
        )

    def shutdown(self):
        logger.info("Shutting down Algorithmic Day Trading Engine...")
        self.is_running = False
        self.health_monitor.stop()

async def main_async():
    engine = TradingBotEngine()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, engine.shutdown)

    try:
        await engine.start()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.critical(f"Engine encountered unhandled exception: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot manually terminated by user.")
        sys.exit(0)
