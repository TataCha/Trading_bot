from datetime import datetime, time, timedelta
import pytz

EST_TZ = pytz.timezone("America/New_York")

def get_est_now() -> datetime:
    """Returns the current datetime in US Eastern timezone (EST/EDT)."""
    return datetime.now(EST_TZ)

def is_market_open(dt: datetime = None) -> bool:
    """
    Checks if US stock market is currently open for standard session trading (9:30 AM - 4:00 PM EST, Mon-Fri).
    """
    if dt is None:
        dt = get_est_now()
    else:
        if dt.tzinfo is None:
            dt = EST_TZ.localize(dt)
        else:
            dt = dt.astimezone(EST_TZ)

    # Weekend check
    if dt.weekday() >= 5:
        return False

    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = dt.time()

    return market_open <= current_time < market_close

def is_eod_flush_time(flush_time_str: str = "15:45", dt: datetime = None) -> bool:
    """
    Checks if current EST time has reached or passed the End-of-Day liquidation cutoff (default 3:45 PM EST)
    and is before market close (4:00 PM EST).
    """
    if dt is None:
        dt = get_est_now()
    else:
        if dt.tzinfo is None:
            dt = EST_TZ.localize(dt)
        else:
            dt = dt.astimezone(EST_TZ)

    if dt.weekday() >= 5:
        return False

    hours, minutes = map(int, flush_time_str.split(":"))
    flush_time = time(hours, minutes)
    market_close = time(16, 0)
    current_time = dt.time()

    return flush_time <= current_time < market_close

def is_weekly_flush_time(flush_time_str: str = "15:45", dt: datetime = None) -> bool:
    """
    Checks if today is Friday (weekday 4) and current EST time has reached or passed
    the End-of-Week liquidation cutoff (default 3:45 PM EST on Friday) and is before market close (4:00 PM EST).
    This ensures all positions are closed within a 1-week timeframe and eliminates weekend risk.
    """
    if dt is None:
        dt = get_est_now()
    else:
        if dt.tzinfo is None:
            dt = EST_TZ.localize(dt)
        else:
            dt = dt.astimezone(EST_TZ)

    # Must be Friday (weekday == 4)
    if dt.weekday() != 4:
        return False

    hours, minutes = map(int, flush_time_str.split(":"))
    flush_time = time(hours, minutes)
    market_close = time(16, 0)
    current_time = dt.time()

    return flush_time <= current_time < market_close

def count_business_days_between(start_dt: datetime, end_dt: datetime = None) -> int:
    """
    Calculates number of trading/business days between start_dt and end_dt.
    """
    if end_dt is None:
        end_dt = get_est_now()

    if start_dt > end_dt:
        return 0

    curr = start_dt.date()
    end_date = end_dt.date()
    business_days = 0

    while curr <= end_date:
        if curr.weekday() < 5:
            business_days += 1
        curr += timedelta(days=1)

    return business_days

def get_rolling_business_days_start(days: int = 5, end_dt: datetime = None) -> datetime:
    """
    Returns the starting datetime for a rolling N-business-day window ending at end_dt.
    """
    if end_dt is None:
        end_dt = get_est_now()

    curr = end_dt
    count = 0
    while count < days:
        curr -= timedelta(days=1)
        if curr.weekday() < 5:  # Monday - Friday
            count += 1

    return curr.replace(hour=0, minute=0, second=0, microsecond=0)
