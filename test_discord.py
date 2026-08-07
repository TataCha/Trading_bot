import sys
from src.monitoring.notifier import NotificationEngine
from config.settings import get_settings

def test_webhook():
    settings = get_settings()
    if not settings.DISCORD_WEBHOOK_URL or "YOUR_DISCORD" in settings.DISCORD_WEBHOOK_URL:
        print("❌ Error: DISCORD_WEBHOOK_URL is not set in .env file.")
        print("Please edit .env and paste your Discord Webhook URL.")
        sys.exit(1)

    print(f"Sending test alert to Discord Webhook...")
    notifier = NotificationEngine(settings=settings)
    notifier.notify_trade_entry(
        symbol="AAPL",
        side="buy",
        qty=100,
        price=150.25,
        sl=148.00,
        tp=154.75,
        reason="Test webhook alert setup"
    )
    print("✅ Test alert sent! Please check your Discord channel.")

if __name__ == "__main__":
    test_webhook()
