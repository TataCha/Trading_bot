import logging
from typing import Optional, Dict, Any
import requests
from config.settings import Settings, get_settings
from src.utils.time_utils import get_est_now

logger = logging.getLogger("TradingBot.Notifier")

class NotificationEngine:
    """
    Dispatches real-time webhook alerts to Discord and Telegram channels
    for trade entries/exits, circuit breaker triggers, and daily balance summaries.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.discord_url = self.settings.DISCORD_WEBHOOK_URL
        self.telegram_token = self.settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = self.settings.TELEGRAM_CHAT_ID

    def send_notification(self, title: str, message: str, level: str = "INFO", color: int = 3447003):
        """
        Broadcasting helper method sending formatted JSON payloads to configured webhooks.
        """
        est_time = get_est_now().strftime("%Y-%m-%d %H:%M:%S EST")
        full_text = f"**[{title}]** ({est_time})\n{message}"

        # 1. Send Discord Webhook
        if self.discord_url:
            embed = {
                "title": f"🚨 Trading Bot Alert: {title}",
                "description": message,
                "color": color,  # 3447003 Blue, 15158332 Red, 3066993 Green
                "footer": {"text": f"US Tech Stock Day Trading Engine • {est_time}"}
            }
            try:
                requests.post(self.discord_url, json={"embeds": [embed]}, timeout=5)
            except Exception as e:
                logger.error(f"Failed to post to Discord webhook: {e}")

        # 2. Send Telegram Webhook
        if self.telegram_token and self.telegram_chat_id:
            tg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": full_text,
                "parse_mode": "Markdown"
            }
            try:
                requests.post(tg_url, json=payload, timeout=5)
            except Exception as e:
                logger.error(f"Failed to post to Telegram bot: {e}")

    def notify_trade_entry(self, symbol: str, side: str, qty: int, price: float, sl: float, tp: float, reason: str):
        title = f"ORDER EXECUTED - {side.upper()} {symbol}"
        msg = (
            f"📈 **Symbol**: `{symbol}`\n"
            f"🔢 **Quantity**: `{qty}` shares\n"
            f"💵 **Entry Price**: `${price:.2f}`\n"
            f"🛑 **Stop Loss**: `${sl:.2f}` ({(sl/price - 1)*100:.2f}%)\n"
            f"🎯 **Take Profit**: `${tp:.2f}` ({(tp/price - 1)*100:.2f}%)\n"
            f"💡 **Reason**: {reason}"
        )
        self.send_notification(title, msg, level="INFO", color=3066993)  # Green

    def notify_circuit_breaker(self, drawdown_pct: float, limit_pct: float):
        title = "⚡ CIRCUIT BREAKER ACTIVATED"
        msg = (
            f"⚠️ **Trading Halted!**\n"
            f"Current daily drawdown: `{drawdown_pct:.2%}`\n"
            f"Max daily threshold: `{limit_pct:.2%}`\n"
            f"All new trade signals will be blocked for the remainder of the session."
        )
        self.send_notification(title, msg, level="CRITICAL", color=15158332)  # Red

    def notify_eod_flush(self, positions_closed: int):
        title = "🌆 END-OF-DAY FLUSH COMPLETED"
        msg = f"Liquidation order dispatched for `{positions_closed}` open positions before market close."
        self.send_notification(title, msg, level="WARNING", color=15105570)  # Orange

    def notify_weekly_flush(self, positions_closed: int):
        title = "🗓️ 1-WEEK HORIZON FLUSH COMPLETED"
        msg = (
            f"End-of-Week Friday liquidation dispatched for `{positions_closed}` open positions.\n"
            f"🎯 1-week holding timeframe complete. Zero weekend exposure."
        )
        self.send_notification(title, msg, level="WARNING", color=15105570)  # Orange

    def notify_heartbeat(self, equity: float, active_positions: int):
        title = "💓 Heartbeat Ping"
        msg = f"System operating normally.\n💰 Account Equity: `${equity:,.2f}`\n📊 Open Positions: `{active_positions}`"
        self.send_notification(title, msg, level="INFO", color=3447003)
