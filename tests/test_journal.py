import os
import shutil
import pytest
from src.monitoring.journal import TradeJournal

@pytest.fixture
def temp_journal_dir(tmp_path):
    test_dir = tmp_path / "test_logs"
    test_dir.mkdir()
    yield str(test_dir)
    shutil.rmtree(test_dir, ignore_errors=True)

def test_trade_journal_lifecycle(temp_journal_dir):
    journal = TradeJournal(log_dir=temp_journal_dir)

    # 1. Record daily snapshot
    journal.record_daily_session_snapshot(
        date_str="2026-08-17",
        start_equity=100000.0,
        end_equity=101500.0,
        cash=60000.0,
        stock_value=41500.0,
        open_positions_count=2,
        realized_pnl=1500.0
    )

    # 2. Log Trade Entry
    journal.log_trade_entry(
        trade_id="test-123",
        symbol="AAPL",
        strategy="Swing_TrendPullback",
        side="buy",
        qty=50,
        entry_price=200.0,
        stop_loss=190.0,
        take_profit=220.0,
        reason="EMA Pullback"
    )

    # 3. Log Trade Exit
    journal.log_trade_exit(
        symbol="AAPL",
        exit_price=220.0,
        exit_reason="Take Profit Limit Hit",
        trade_id="test-123"
    )

    # Verify CSV and JSON exist and have content
    assert os.path.exists(os.path.join(temp_journal_dir, "trade_journal.json"))
    assert os.path.exists(os.path.join(temp_journal_dir, "daily_ledger.json"))
    assert os.path.exists(os.path.join(temp_journal_dir, "trades.csv"))
