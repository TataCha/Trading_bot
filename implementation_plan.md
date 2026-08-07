# Implementation Plan - Algorithmic Day Trading Engine (US Tech Stocks)

This document outlines the implementation strategy for building an automated, low-latency day trading bot tailored for US technology stocks (e.g., AAPL, NVDA, MSFT) using Python and the Alpaca Brokerage API, following the 3-page System Design Document.

## User Review Required

> [!IMPORTANT]
> **Brokerage API & Trading Mode**: The initial code will target Alpaca Paper Trading API (`https://paper-api.alpaca.markets`) for safety. Live trading mode can be toggled via environment configuration (`TRADING_MODE=paper` vs `TRADING_MODE=live`).
> 
> **Dependencies**: The project will use standard financial Python packages (`alpaca-py` / `alpaca-trade-api`, `pandas`, `pandas-ta` / `ta`, `backtesting` or custom backtester, `pydantic`, `aiohttp`, `requests`).
>
> **Pattern Day Trader (PDT) Safeguard**: Enforced strictly by default. If account equity is under $25,000, trade limit is set to max 3 day trades per rolling 5-business-day window.

## Open Questions

> [!NOTE]
> 1. **Default Trading Symbols**: The default configuration will monitor `AAPL`, `NVDA`, and `MSFT` on 15-minute candles. Do you have any additional symbols to add to the default watchlist?
> 2. **Notification Webhook**: Discord and Telegram webhooks will be configurable via `.env`. Should we include pre-configured payload templates for both platforms?

---

## Proposed Changes

We will create a clean, decoupled modular Python package structure under `src/` (or package root) along with backtesting scripts, configuration templates, logging systems, and documentation.

```
Bot_daytrade/
├── config/
│   ├── settings.py           # Pydantic settings & env loader
│   └── .env.example          # Sample environment variables template
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── collector.py      # Alpaca WebSocket streaming & REST historical fetch
│   │   ├── resampler.py      # 15-min bar aggregation & data normalization
│   │   └── indicators.py     # TA calculations (VWAP, RSI, MACD, SMA/EMA)
│   ├── strategy/
│   │   ├── base.py           # Abstract Base Class (StrategyBase)
│   │   ├── vwap_breakout.py  # VWAP breakout strategy implementation
│   │   ├── rsi_reversion.py  # RSI mean-reversion strategy implementation
│   │   └── ma_crossover.py   # Moving Average crossover strategy
│   ├── risk/
│   │   ├── risk_manager.py   # Position sizing (2% equity risk), circuit breaker, PDT counter
│   │   └── eod_flusher.py    # Auto-liquidation prior to market close (3:45 PM EST)
│   ├── execution/
│   │   └── order_controller.py # Alpaca REST client wrapper for bracket order submission & position management
│   ├── monitoring/
│   │   ├── logger.py         # Structured JSON logging to file & stdout
│   │   ├── notifier.py       # Webhook alerts (Discord / Telegram)
│   │   └── health.py         # Hourly heartbeat ping monitor
│   └── utils/
│       └── time_utils.py     # EST/EDT market hours & 5-day rolling window helpers
├── backtest/
│   ├── engine.py             # Event-driven / Vectorized strategy backtesting engine
│   └── performance.py        # Metrics calculator (Sharpe ratio, Max Drawdown, Win Rate, Slippage/Spread modeling)
├── tests/
│   ├── test_risk.py          # Unit tests for PDT counter, risk sizing, circuit breaker
│   ├── test_indicators.py    # Unit tests for VWAP, RSI, MACD calculations
│   └── test_strategy.py      # Unit tests for strategy signal generation
├── main.py                   # Live/Paper trading bot runner entrypoint
├── run_backtest.py           # CLI command for running historical backtests
├── requirements.txt          # Dependency specifications
├── README.md                 # Complete documentation & quickstart guide
└── bot_daytrade.service      # Systemd Linux daemon file for cloud deployment (Phase 3)
```

### 1. Project Configuration & Setup

#### [NEW] [settings.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/config/settings.py)
- Pydantic-based configuration management loading Alpaca credentials, risk limits, trading mode (`paper`/`live`), Discord/Telegram webhooks, and default stock watchlist.

#### [NEW] [.env.example](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/config/.env.example)
- Template for Alpaca API key/secret, Webhook URLs, and risk thresholds.

---

### 2. Market Data Subsystem (`src/data/`)

#### [NEW] [collector.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/data/collector.py)
- Fetches historical OHLCV data on startup for warm-up indicator calculations using Alpaca REST API.
- Subscribes to live WebSocket bar updates and handles connection resilience & auto-reconnect.

#### [NEW] [resampler.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/data/resampler.py) & [indicators.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/data/indicators.py)
- Aggregates minute bars into 15-minute timeframe candles.
- Computes VWAP, RSI, MACD, and SMA/EMA using `pandas` and `pandas-ta` vector operations.

---

### 3. Modular Strategy Framework (`src/strategy/`)

#### [NEW] [base.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/strategy/base.py)
- Abstract Base Class `StrategyBase` defining standard methods: `on_bar(symbol, df_15m)`, `generate_signals()`, `get_parameters()`.

#### [NEW] [vwap_breakout.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/strategy/vwap_breakout.py), [rsi_reversion.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/strategy/rsi_reversion.py), [ma_crossover.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/strategy/ma_crossover.py)
- Implements 3 core strategies outlined in the system design doc with entry/exit signal conditions.

---

### 4. Risk Management & Order Subsystem (`src/risk/`, `src/execution/`)

#### [NEW] [risk_manager.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/risk/risk_manager.py)
- Position Sizing: Calculates shares based on account equity and fixed risk % per trade (e.g. 2%).
- Daily Drawdown Circuit Breaker: Halts automated trading if daily loss reaches threshold.
- PDT Rule Counter: Tracks day trades in rolling 5-business-day window; limits to 3 trades if equity < $25,000.

#### [NEW] [eod_flusher.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/risk/eod_flusher.py)
- Monitors market clock and forcibly liquidates all open positions at 3:45 PM EST to prevent overnight gap risk.

#### [NEW] [order_controller.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/execution/order_controller.py)
- Alpaca REST wrapper submitting automated Bracket Orders (Market/Limit Entry + simultaneous Stop-Loss & Take-Profit orders).
- Fetches active orders, open positions, and account balances.

---

### 5. Monitoring & Webhook Alerts (`src/monitoring/`)

#### [NEW] [logger.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/monitoring/logger.py)
- Structured logging configuration writing formatted logs to file (`logs/trading_bot.log`) and stdout with rotation.

#### [NEW] [notifier.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/monitoring/notifier.py)
- Formats and posts rich JSON cards/embeds to Discord and Telegram webhooks for trade entries, exits, circuit breaker triggers, and EOD summaries.

#### [NEW] [health.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/src/monitoring/health.py)
- Periodic heartbeat service sending status updates every hour.

---

### 6. Backtesting & Analysis Engine (`backtest/`)

#### [NEW] [engine.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/backtest/engine.py) & [performance.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/backtest/performance.py)
- Event-driven backtester supporting historical 15-min OHLCV data.
- Factors in 0.05% slippage and bid-ask spread buffers per order.
- Generates Sharpe ratio, Max Drawdown %, Win Rate, Profit Factor, and prints summary metrics.

---

### 7. Main Entrypoints & Support Files

#### [NEW] [main.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/main.py)
- Main bot runner uniting Data Collector -> Resampler -> Strategy -> Risk Manager -> Order Controller -> Notifier in an async execution loop with graceful shutdown handling.

#### [NEW] [run_backtest.py](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/run_backtest.py)
- CLI entrypoint for running strategy backtests with customizable date ranges and symbols.

#### [NEW] [requirements.txt](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/requirements.txt) & [README.md](file:///Users/chaichanasritrakul/Desktop/Bot_daytrade/README.md)
- Complete package dependencies and setup guide covering Phase 1 through Phase 4.

---

## Verification Plan

### Automated Tests
- Run unit test suite using `pytest`:
  ```bash
  pytest tests/
  ```
- Test risk calculations (position sizing, PDT limits, circuit breaker).
- Test technical indicator math against standard baseline calculations.
- Run backtesting engine CLI to verify execution without error:
  ```bash
  python run_backtest.py --strategy vwap_breakout --symbol AAPL --days 30
  ```

### Manual Verification
- Dry-run `main.py` in test mode to confirm configuration loading, logging initialization, and Alpaca Paper API connection authentication.
- Verify webhook payload formatting by dispatching test ping.
