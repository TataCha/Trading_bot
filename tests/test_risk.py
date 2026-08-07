import pytest
from src.risk.risk_manager import RiskManager
from config.settings import Settings

def test_position_sizing():
    settings = Settings(MAX_RISK_PER_TRADE_PCT=0.02)
    rm = RiskManager(settings=settings)

    # $100,000 equity, 2% risk = $2,000
    # Entry: $100, Stop Loss: $98 -> Risk per share = $2
    # Sized shares = $2,000 / $2 = 1,000 shares
    # Capped at 15% account value = $15,000 / $100 = 150 shares
    shares = rm.calculate_position_size(entry_price=100.0, stop_loss_price=98.0, account_equity=100000.0)
    assert shares == 150  # Concentration cap applied

def test_circuit_breaker():
    settings = Settings(DAILY_DRAWDOWN_LIMIT_PCT=0.05)
    rm = RiskManager(settings=settings)

    rm.update_account_equity(100000.0)
    assert rm.circuit_breaker_tripped is False

    # Equity drops to $94,000 (6% drawdown > 5% limit)
    rm.update_account_equity(94000.0)
    assert rm.circuit_breaker_tripped is True

    can_trade, reason = rm.can_open_position("AAPL")
    assert can_trade is False
    assert "Circuit Breaker" in reason

def test_pdt_limit():
    settings = Settings(ENFORCE_PDT_RULE=True, PDT_ACCOUNT_THRESHOLD=25000.0)
    rm = RiskManager(settings=settings)

    rm.update_account_equity(20000.0)  # Under $25k equity threshold

    # Record 3 day trades
    for _ in range(3):
        rm.record_day_trade()

    can_trade, reason = rm.can_open_position("NVDA")
    assert can_trade is False
    assert "PDT Limit" in reason
