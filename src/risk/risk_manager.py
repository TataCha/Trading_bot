import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from config.settings import Settings, get_settings
from src.utils.time_utils import get_est_now, get_rolling_business_days_start

logger = logging.getLogger("TradingBot.RiskManager")

class RiskManager:
    """
    Core Risk Management Subsystem:
    - Sizes positions based on fixed risk per trade (e.g. 2% equity) and stop-loss distance.
    - Enforces Daily Drawdown Circuit Breaker (halts trading if loss >= 5%).
    - Enforces Pattern Day Trader (PDT) safeguards (< $25k equity => max 3 day trades per rolling 5 business days).
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.max_risk_pct = self.settings.MAX_RISK_PER_TRADE_PCT
        self.daily_drawdown_limit = self.settings.DAILY_DRAWDOWN_LIMIT_PCT
        self.pdt_threshold = self.settings.PDT_ACCOUNT_THRESHOLD
        self.enforce_pdt = self.settings.ENFORCE_PDT_RULE

        self.starting_daily_equity: float = 0.0
        self.current_equity: float = 0.0
        self.circuit_breaker_tripped: bool = False

        # Day trade history log: list of datetimes when day trades occurred
        self.day_trade_timestamps: List[datetime] = []

    def update_account_equity(self, equity: float):
        """Updates internal equity values and checks circuit breaker."""
        if self.starting_daily_equity == 0.0:
            self.starting_daily_equity = equity

        self.current_equity = equity
        self.check_circuit_breaker()

    def check_circuit_breaker(self) -> bool:
        """
        Calculates current daily drawdown. If daily loss exceeds limit, trips the circuit breaker.
        """
        if self.starting_daily_equity <= 0:
            return False

        drawdown = (self.starting_daily_equity - self.current_equity) / self.starting_daily_equity
        if drawdown >= self.daily_drawdown_limit:
            if not self.circuit_breaker_tripped:
                logger.critical(f"CIRCUIT BREAKER TRIPPED! Daily drawdown ({drawdown:.2%}) exceeded limit ({self.daily_drawdown_limit:.2%}). Halting trading.")
                self.circuit_breaker_tripped = True
            return True

        return False

    def get_rolling_day_trade_count(self) -> int:
        """
        Counts number of day trades executed in the rolling 5-business-day window.
        """
        cutoff_dt = get_rolling_business_days_start(days=5)
        recent_trades = [ts for ts in self.day_trade_timestamps if ts >= cutoff_dt]
        return len(recent_trades)

    def record_day_trade(self, timestamp: Optional[datetime] = None):
        """Records a new day trade execution timestamp."""
        ts = timestamp or get_est_now()
        self.day_trade_timestamps.append(ts)
        logger.info(f"Recorded day trade at {ts.strftime('%Y-%m-%d %H:%M:%S EST')}. Rolling count: {self.get_rolling_day_trade_count()}")

    def can_open_position(self, symbol: str, active_positions: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Validates whether a new position can be legally and safely opened under risk guardrails.
        """
        # 0. Duplicate position check
        if active_positions and symbol in active_positions:
            return False, f"Position already open for {symbol}."

        # 1. Circuit Breaker check
        if self.circuit_breaker_tripped:
            return False, "Trading halted by Daily Drawdown Circuit Breaker."

        # 2. PDT Rule check
        if self.enforce_pdt and self.current_equity < self.pdt_threshold:
            rolling_count = self.get_rolling_day_trade_count()
            if rolling_count >= 3:
                return False, f"PDT Limit reached! Equity (${self.current_equity:,.2f}) < $25,000 and rolling day trades ({rolling_count}) >= 3."

        return True, "Approved"

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        account_equity: float
    ) -> int:
        """
        Calculates position size (shares) strictly based on fixed account equity risk (e.g., 2%).
        Shares = (Account Equity * Risk %) / (Entry Price - Stop Loss Price)
        """
        if entry_price <= 0 or stop_loss_price >= entry_price or account_equity <= 0:
            return 0

        risk_amount = account_equity * self.max_risk_pct
        price_risk_per_share = entry_price - stop_loss_price

        shares = int(risk_amount / price_risk_per_share)

        # Cap max position value to 15% of account equity to avoid concentration risk
        max_allowed_shares = int((account_equity * 0.15) / entry_price)
        final_shares = max(1, min(shares, max_allowed_shares))

        logger.info(f"Position Sizing: Risk=${risk_amount:.2f} | Risk/Share=${price_risk_per_share:.2f} -> Sized Shares: {final_shares} (${final_shares * entry_price:,.2f})")
        return final_shares
