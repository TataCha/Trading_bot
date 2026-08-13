import pytest
from datetime import datetime
import pytz
from config.settings import Settings
from src.risk.eod_flusher import HorizonFlusher
from src.utils.time_utils import is_weekly_flush_time, count_business_days_between

EST_TZ = pytz.timezone("America/New_York")

def test_holding_during_week():
    """Verify positions are held Monday-Thursday without premature flush."""
    settings = Settings(ENABLE_WEEKLY_FLUSH=True, ENABLE_EOD_FLUSH=False, WEEKLY_FLUSH_TIME_EST="15:45")
    flusher = HorizonFlusher(settings=settings)

    # Monday 10:00 AM EST
    mon_dt = EST_TZ.localize(datetime(2026, 8, 10, 10, 0, 0))
    assert flusher.should_flush(mon_dt) is False

    # Tuesday 3:45 PM EST (Should NOT flush in weekly mode)
    tue_dt = EST_TZ.localize(datetime(2026, 8, 11, 15, 45, 0))
    assert flusher.should_flush(tue_dt) is False

    # Thursday 3:55 PM EST (Should NOT flush)
    thu_dt = EST_TZ.localize(datetime(2026, 8, 13, 15, 55, 0))
    assert flusher.should_flush(thu_dt) is False

def test_weekly_flush_on_friday_afternoon():
    """Verify weekly liquidation triggers strictly on Friday at 15:45 EST."""
    settings = Settings(ENABLE_WEEKLY_FLUSH=True, ENABLE_EOD_FLUSH=False, WEEKLY_FLUSH_TIME_EST="15:45")
    flusher = HorizonFlusher(settings=settings)

    # Friday 2:00 PM EST (Too early)
    fri_early = EST_TZ.localize(datetime(2026, 8, 14, 14, 0, 0))
    assert flusher.should_flush(fri_early) is False

    # Friday 3:45 PM EST (Cutoff reached -> Must trigger)
    fri_cutoff = EST_TZ.localize(datetime(2026, 8, 14, 15, 45, 0))
    assert flusher.should_flush(fri_cutoff) is True
    assert flusher.last_flush_reason == "WEEKLY_HORIZON"

    # Subsequent check on same Friday should not re-trigger
    fri_later = EST_TZ.localize(datetime(2026, 8, 14, 15, 50, 0))
    assert flusher.should_flush(fri_later) is False

def test_monday_reset():
    """Verify tracking resets automatically when new week starts on Monday."""
    settings = Settings(ENABLE_WEEKLY_FLUSH=True, WEEKLY_FLUSH_TIME_EST="15:45")
    flusher = HorizonFlusher(settings=settings)

    # Trigger Friday flush
    fri_dt = EST_TZ.localize(datetime(2026, 8, 14, 15, 45, 0))
    assert flusher.should_flush(fri_dt) is True

    # Next Monday morning
    mon_dt = EST_TZ.localize(datetime(2026, 8, 17, 9, 35, 0))
    assert flusher.should_flush(mon_dt) is False
    assert flusher.flushed_this_week is False

def test_position_lifetime_expiration():
    """Verify individual position expiration when exceeding max holding days."""
    settings = Settings(MAX_HOLDING_DAYS=5)
    flusher = HorizonFlusher(settings=settings)

    entry_dt = EST_TZ.localize(datetime(2026, 8, 3, 10, 0, 0))
    flusher.record_position_entry("AAPL", entry_dt)

    # Day 3: Within holding period
    day3_dt = EST_TZ.localize(datetime(2026, 8, 6, 10, 0, 0))
    assert flusher.is_position_expired("AAPL", day3_dt) is False

    # Day 7 (exceeds 5 business days): Expired
    day7_dt = EST_TZ.localize(datetime(2026, 8, 11, 10, 0, 0))
    assert flusher.is_position_expired("AAPL", day7_dt) is True
