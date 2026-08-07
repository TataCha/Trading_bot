import asyncio
import logging
from typing import Optional, Callable
from config.settings import Settings, get_settings

logger = logging.getLogger("TradingBot.HealthMonitor")

class HealthMonitor:
    """
    Heartbeat and process health monitoring task.
    Dispatches regular status notifications every N minutes to ensure uninterrupted execution.
    """

    def __init__(self, settings: Optional[Settings] = None, callback: Optional[Callable[[], None]] = None):
        self.settings = settings or get_settings()
        self.interval_minutes = self.settings.HEARTBEAT_INTERVAL_MINUTES
        self.callback = callback
        self._running = False

    async def start(self):
        self._running = True
        logger.info(f"Health monitor service started (Interval: {self.interval_minutes} minutes)")

        while self._running:
            await asyncio.sleep(self.interval_minutes * 60)
            if self._running and self.callback:
                try:
                    self.callback()
                except Exception as e:
                    logger.error(f"Error in health monitor callback: {e}")

    def stop(self):
        self._running = False
        logger.info("Health monitor service stopped.")
