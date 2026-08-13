import logging
from datetime import datetime
from typing import Optional, Dict
from config.settings import Settings, get_settings
from src.utils.time_utils import is_eod_flush_time, is_weekly_flush_time, get_est_now, count_business_days_between

logger = logging.getLogger("TradingBot.HorizonFlusher")

class HorizonFlusher:
    """
    Position Horizon & Liquidation Manager:
    - Weekly Horizon Flushing: Automatically liquidates all open positions on Friday at 3:45 PM EST
      (15 mins before market close) to guarantee all operations stay within a 1-week timeframe and
      eliminate weekend holding risks.
    - Holding until Target Value: Positions are held across days/nights without premature daily liquidation
      until Target Value (Take Profit) or Stop Loss is reached.
    - Max Holding Duration: Safeguard to close individual positions that exceed MAX_HOLDING_DAYS (default: 5 days).
    - Daily EOD Flushing: Optional classic intraday mode (if ENABLE_EOD_FLUSH=True).
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.eod_flush_time = getattr(self.settings, "EOD_FLUSH_TIME_EST", "15:45")
        self.weekly_flush_time = getattr(self.settings, "WEEKLY_FLUSH_TIME_EST", "15:45")
        self.max_holding_days = getattr(self.settings, "MAX_HOLDING_DAYS", 5)

        self.flushed_today = False
        self.flushed_this_week = False
        self.last_flush_date = None
        self.last_flush_reason = ""

        # Track entry timestamps per symbol: {symbol: datetime}
        self.position_entry_times: Dict[str, datetime] = {}

    def record_position_entry(self, symbol: str, entry_dt: Optional[datetime] = None):
        """Records when a position is opened to track holding duration."""
        self.position_entry_times[symbol] = entry_dt or get_est_now()

    def record_position_closed(self, symbol: str):
        """Clears tracking when a position is closed."""
        self.position_entry_times.pop(symbol, None)

    def is_position_expired(self, symbol: str, now: Optional[datetime] = None) -> bool:
        """
        Checks if an individual position has exceeded the maximum holding business days (e.g. 5 days).
        """
        entry_dt = self.position_entry_times.get(symbol)
        if not entry_dt:
            return False

        now_dt = now or get_est_now()
        days_held = count_business_days_between(entry_dt, now_dt)
        return days_held > self.max_holding_days

    def should_flush(self, now: Optional[datetime] = None) -> bool:
        """
        Determines whether portfolio liquidation should be triggered at current time.
        Evaluates Weekly Friday Flush (1-Week Horizon) and optional Daily EOD Flush.
        """
        now_dt = now or get_est_now()
        today = now_dt.date()

        # Reset daily/weekly state if date changed
        if self.last_flush_date != today:
            self.flushed_today = False
            # Reset weekly flag on new calendar week (Monday: weekday 0)
            if now_dt.weekday() == 0:
                self.flushed_this_week = False

        # 1. Weekly Friday End-of-Week Cutoff (1-Week Horizon)
        if getattr(self.settings, "ENABLE_WEEKLY_FLUSH", True):
            if now_dt.weekday() == 4:  # Friday
                if not self.flushed_this_week and is_weekly_flush_time(self.weekly_flush_time, now_dt):
                    self.flushed_this_week = True
                    self.flushed_today = True
                    self.last_flush_date = today
                    self.last_flush_reason = "WEEKLY_HORIZON"
                    logger.warning(
                        f"⚡ 1-WEEK HORIZON FLUSH TRIGGERED on Friday at {now_dt.strftime('%H:%M:%S EST')}! "
                        f"Liquidating open positions before weekend market close."
                    )
                    return True

        # 2. Daily EOD Cutoff (Only if explicitly enabled for intraday mode)
        if getattr(self.settings, "ENABLE_EOD_FLUSH", False):
            if not self.flushed_today and is_eod_flush_time(self.eod_flush_time, now_dt):
                self.flushed_today = True
                self.last_flush_date = today
                self.last_flush_reason = "DAILY_EOD"
                logger.warning(
                    f"EOD Daily Flush Triggered at {now_dt.strftime('%H:%M:%S EST')}! "
                    f"Target time: {self.eod_flush_time}"
                )
                return True

        return False

    def reset_state(self):
        """Resets tracking state."""
        self.flushed_today = False
        self.flushed_this_week = False
        self.last_flush_reason = ""


# Backward compatibility aliases
EODFlusher = HorizonFlusher
WeeklyFlusher = HorizonFlusher
