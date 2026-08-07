# Algorithmic Day Trading Engine (US Tech Stocks Focus)

An automated, low-latency day trading bot built in Python and powered by the **Alpaca Brokerage API**. Designed specifically for 15-minute timeframe trading on US tech equities (`AAPL`, `NVDA`, `MSFT`, `AMD`, `DRAM`, `TSM`).

---

## 🌟 Key Subsystem Features

- **Market Data Collector**: Live WebSocket bar streaming & REST historical warm-up pipeline with resilient polling fallback.
- **15-Min Resampler & TA Engine**: Automatic candlestick aggregation computing VWAP, RSI, MACD, SMA, and EMA indicators.
- **Plug-and-Play Strategy Framework**: Includes `VWAP Breakout`, `RSI Mean Reversion`, and `Moving Average Crossover` strategies.
- **Risk Management & Order Guardrails**:
  - **Fixed 2% Risk Position Sizing**: Calculates exact shares based on stop loss distance.
  - **Daily Drawdown Circuit Breaker**: Automatically halts trading if daily equity drops by 5%.
  - **PDT Safeguard**: Enforces FINRA Pattern Day Trader limits (max 3 day trades / 5 days if equity < $25,000).
  - **3:45 PM EST EOD Flusher**: Auto-liquidates positions before 4:00 PM EST market close to prevent overnight gap risk.
- **Automated Bracket Orders**: Submits Entry orders with simultaneous Stop-Loss and Take-Profit limit orders attached via Alpaca REST API.
- **Monitoring & Alerts**: Discord and Telegram webhook notifications for trade entries/exits, circuit breaker alerts, and hourly heartbeat pings.
- **Slippage & Spread Backtesting**: Event-driven backtester featuring 0.05% slippage modeling, Sharpe ratio, and Max Drawdown profiling.

---

## 🛠️ Project Structure

```
Bot_daytrade/
├── config/
│   ├── settings.py           # Pydantic environment & config management
│   └── .env.example          # Environment variables template
├── src/
│   ├── data/
│   │   ├── collector.py      # Alpaca WebSocket streaming & REST historical pipeline
│   │   ├── resampler.py      # 15-min candle aggregation
│   │   └── indicators.py     # TA indicators (VWAP, RSI, MACD, SMA/EMA)
│   ├── strategy/
│   │   ├── base.py           # Abstract Base Class (StrategyBase) & Signal definition
│   │   ├── vwap_breakout.py  # VWAP breakout strategy
│   │   ├── rsi_reversion.py  # RSI mean-reversion strategy
│   │   └── ma_crossover.py   # Moving average crossover strategy
│   ├── risk/
│   │   ├── risk_manager.py   # Position sizing, circuit breaker, PDT tracker
│   │   └── eod_flusher.py    # Auto-liquidation prior to market close (3:45 PM EST)
│   ├── execution/
│   │   └── order_controller.py # Alpaca REST Bracket order client wrapper
│   ├── monitoring/
│   │   ├── logger.py         # Structured JSON & file logger
│   │   ├── notifier.py       # Discord & Telegram webhook alerts
│   │   └── health.py         # Hourly heartbeat ping monitor
│   └── utils/
│       └── time_utils.py     # EST market hours & rolling window calculations
├── backtest/
│   ├── engine.py             # Historical strategy simulation with slippage
│   └── performance.py        # Metrics calculator (Sharpe, Drawdown, Win Rate)
├── tests/                    # Pytest suite
│   ├── test_risk.py
│   ├── test_indicators.py
│   └── test_strategy.py
├── main.py                   # Live/Paper production trading runner
├── run_backtest.py           # CLI for historical backtesting
├── requirements.txt          # Package dependencies
└── bot_daytrade.service      # Systemd daemon config for AWS EC2 / VPS
```

---

## 🚀 Quick Start Guide

### 1. Installation & Environment Setup

Clone repository and install Python dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy `.env.example` to `.env` in the root workspace directory:
```bash
cp config/.env.example .env
```

Edit `.env` with your Alpaca API Keys:
```ini
ALPACA_API_KEY=your_alpaca_paper_api_key
ALPACA_SECRET_KEY=your_alpaca_paper_secret_key
TRADING_MODE=paper

DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 📊 Phase 1: Historical Backtesting

Run historical strategy backtest on 15-minute tech stock candles:

```bash
# Backtest VWAP Breakout on AAPL over 30 days
python run_backtest.py --symbol AAPL --strategy vwap_breakout --days 30

# Backtest RSI Mean Reversion on NVDA
python run_backtest.py --symbol NVDA --strategy rsi_reversion --days 45 --capital 50000

# Backtest MA Crossover on TSM with 0.05% slippage
python run_backtest.py --symbol TSM --strategy ma_crossover --days 60 --slippage 0.0005
```

---

## ⚡ Phase 2: Live / Paper Execution

Run the main bot execution engine:

```bash
python main.py
```

- In **Paper Trading Mode** (`TRADING_MODE=paper`), the bot connects to Alpaca Paper API, streams live 1-minute bars, resamples candles into 15m intervals, evaluates signals, enforces risk rules, places Bracket orders, and sends webhook alerts to Discord/Telegram.

---

## 🧪 Running Automated Tests

Run the `pytest` test suite:
```bash
pytest tests/ -v
```

---

## ☁️ Phase 3: Cloud VPS Deployment (24/7 Uptime)

1. Provision an AWS EC2 micro instance or Oracle Always Free VPS (Ubuntu 22.04 LTS).
2. Copy `bot_daytrade.service` to `/etc/systemd/system/bot_daytrade.service`.
3. Enable and start daemon:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bot_daytrade
sudo systemctl start bot_daytrade
sudo systemctl status bot_daytrade
```
