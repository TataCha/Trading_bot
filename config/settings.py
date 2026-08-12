import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Alpaca API Credentials
    ALPACA_API_KEY: str = Field(default="")
    ALPACA_SECRET_KEY: str = Field(default="")
    TRADING_MODE: str = Field(default="paper")  # "paper" or "live"

    @property
    def ALPACA_BASE_URL(self) -> str:
        if self.TRADING_MODE.lower() == "live":
            return "https://api.alpaca.markets"
        return "https://paper-api.alpaca.markets"

    @property
    def ALPACA_DATA_URL(self) -> str:
        return "https://data.alpaca.markets"

    # Risk & Order Guardrails
    TRADING_STYLE: str = Field(default="swing")  # "swing" or "daytrade"
    MAX_RISK_PER_TRADE_PCT: float = Field(default=0.02)  # 2% per trade
    DAILY_DRAWDOWN_LIMIT_PCT: float = Field(default=0.05)  # 5% daily circuit breaker
    MAX_ACCOUNT_EQUITY_RISK_PCT: float = Field(default=0.10)
    MAX_CONCURRENT_POSITIONS: int = Field(default=3)  # Hold up to 3 different stocks simultaneously
    ENFORCE_PDT_RULE: bool = Field(default=False)  # Exempt in swing mode when holding overnight
    PDT_ACCOUNT_THRESHOLD: float = Field(default=25000.00)
    ENABLE_EOD_FLUSH: bool = Field(default=False)  # Allow overnight multi-day holds in swing mode
    EOD_FLUSH_TIME_EST: str = Field(default="15:45")
    ATR_MULTIPLIER: float = Field(default=2.5)

    # Timeframe & Watchlist (Tech Equities + 3x Leveraged Tech ETFs)
    TIMEFRAME: str = Field(default="1Hour")  # "1Hour" or "1Day" for swing trading
    SYMBOLS: List[str] = Field(
        default_factory=lambda: ["AAPL", "NVDA", "MSFT", "AMD", "DRAM", "TSM", "TQQQ", "SOXL"]
    )

    # Notifications
    DISCORD_WEBHOOK_URL: str = Field(default="")
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_CHAT_ID: str = Field(default="")

    # Monitoring
    HEARTBEAT_INTERVAL_MINUTES: int = Field(default=60)
    LOG_LEVEL: str = Field(default="INFO")

def get_settings() -> Settings:
    return Settings()
