import logging
from typing import Optional
from config.settings import Settings, get_settings
from src.utils.time_utils import is_eod_flush_time, get_est_now

logger = logging.getLogger("TradingBot.EODFlusher")

class EODFlusher:
    """
    End-of-Day (EOD) Position Flusher:
    Automatically liquidates all open positions prior to US market close (default 3:45 PM EST)
    to eliminate overnight holding and gap risk.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.flush_time = self.settings.EOD_FLUSH_TIME_EST
        self.flushed_today = False
        self.last_flush_date = None

    def should_flush(self) -> bool:
        """
        Determines whether EOD liquidation should be triggered at current time.
        """
        if not getattr(self.settings, "ENABLE_EOD_FLUSH", False):
            return False

        now = get_est_now()
        today = now.date()

        if self.last_flush_date == today and self.flushed_today:
            return False

        if is_eod_flush_time(self.flush_time, now):
            self.flushed_today = True
            self.last_flush_date = today
            logger.warning(f"EOD Flush trigger activated at {now.strftime('%H:%M:%S EST')}! Target time: {self.flush_time}")
            return True

        return False

    def reset_daily_state(self):
        """Resets daily flush tracking state."""
        self.flushed_today = False
