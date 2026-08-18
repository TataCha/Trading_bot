import os
import json
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from config.settings import Settings, get_settings
from src.utils.time_utils import get_est_now

class TradeJournal:
    """
    Automated Trade Journaling and Weekly Evaluation Manager.
    Logs daily account snapshots and round-trip trade statistics from Monday to Friday.
    """

    def __init__(self, log_dir: str = "logs", settings: Optional[Settings] = None):
        self.log_dir = log_dir
        self.settings = settings or get_settings()
        os.makedirs(self.log_dir, exist_ok=True)

        self.journal_file = os.path.join(self.log_dir, "trade_journal.json")
        self.daily_ledger_file = os.path.join(self.log_dir, "daily_ledger.json")
        self.csv_file = os.path.join(self.log_dir, "trades.csv")

        self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(self.journal_file):
            with open(self.journal_file, "w") as f:
                json.dump({"trades": []}, f, indent=2)

        if not os.path.exists(self.daily_ledger_file):
            with open(self.daily_ledger_file, "w") as f:
                json.dump({"daily_sessions": []}, f, indent=2)

        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Trade_ID", "Date", "Symbol", "Strategy", "Side", "Qty",
                    "Entry_Time", "Entry_Price", "Exit_Time", "Exit_Price",
                    "Stop_Loss", "Take_Profit", "Realized_PL", "Return_Pct",
                    "Holding_Duration", "Exit_Reason", "Status"
                ])

    def record_daily_session_snapshot(
        self,
        date_str: str,
        start_equity: float,
        end_equity: float,
        cash: float,
        stock_value: float,
        open_positions_count: int,
        realized_pnl: float = 0.0
    ):
        """Records end-of-day equity, cash, and P&L snapshots for weekly evaluation."""
        try:
            with open(self.daily_ledger_file, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"daily_sessions": []}

        day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
        daily_pnl = end_equity - start_equity
        daily_pnl_pct = (daily_pnl / start_equity * 100.0) if start_equity > 0 else 0.0

        snapshot = {
            "date": date_str,
            "day_of_week": day_name,
            "start_equity": start_equity,
            "end_equity": end_equity,
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "realized_pnl": round(realized_pnl, 2),
            "cash": round(cash, 2),
            "stock_value": round(stock_value, 2),
            "open_positions_count": open_positions_count,
            "recorded_at": get_est_now().isoformat()
        }

        # Update or append
        existing = [s for s in data["daily_sessions"] if s["date"] == date_str]
        if existing:
            idx = data["daily_sessions"].index(existing[0])
            data["daily_sessions"][idx] = snapshot
        else:
            data["daily_sessions"].append(snapshot)

        with open(self.daily_ledger_file, "w") as f:
            json.dump(data, f, indent=2)

    def log_trade_entry(
        self,
        trade_id: str,
        symbol: str,
        strategy: str,
        side: str,
        qty: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        reason: str = ""
    ):
        """Logs the initiation of a new trade position."""
        entry_time = get_est_now().strftime("%Y-%m-%d %H:%M:%S EST")
        date_str = get_est_now().strftime("%Y-%m-%d")

        trade_record = {
            "trade_id": trade_id,
            "date": date_str,
            "symbol": symbol,
            "strategy": strategy,
            "side": side.upper(),
            "qty": qty,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "exit_time": None,
            "exit_price": None,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "realized_pnl": None,
            "return_pct": None,
            "holding_duration": None,
            "exit_reason": None,
            "status": "OPEN",
            "entry_reason": reason
        }

        try:
            with open(self.journal_file, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"trades": []}

        data["trades"].append(trade_record)
        with open(self.journal_file, "w") as f:
            json.dump(data, f, indent=2)

        self._append_csv_row(trade_record)

    def log_trade_exit(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str,
        trade_id: Optional[str] = None
    ):
        """Logs the exit and computes round-trip performance."""
        exit_time = get_est_now().strftime("%Y-%m-%d %H:%M:%S EST")

        try:
            with open(self.journal_file, "r") as f:
                data = json.load(f)
        except Exception:
            return

        for trade in reversed(data["trades"]):
            if trade["symbol"] == symbol and trade["status"] == "OPEN":
                if trade_id and trade["trade_id"] != trade_id:
                    continue

                entry_price = trade["entry_price"]
                qty = trade["qty"]
                side = trade["side"]

                if side == "BUY":
                    pnl = (exit_price - entry_price) * qty
                    ret_pct = ((exit_price - entry_price) / entry_price) * 100.0
                else:
                    pnl = (entry_price - exit_price) * qty
                    ret_pct = ((entry_price - exit_price) / entry_price) * 100.0

                trade["exit_time"] = exit_time
                trade["exit_price"] = round(exit_price, 2)
                trade["realized_pnl"] = round(pnl, 2)
                trade["return_pct"] = round(ret_pct, 2)
                trade["exit_reason"] = exit_reason
                trade["status"] = "CLOSED"

                # Calculate holding duration
                try:
                    t_entry = datetime.strptime(trade["entry_time"].replace(" EST", ""), "%Y-%m-%d %H:%M:%S")
                    t_exit = datetime.strptime(exit_time.replace(" EST", ""), "%Y-%m-%d %H:%M:%S")
                    diff = t_exit - t_entry
                    trade["holding_duration"] = str(diff).split(".")[0]
                except Exception:
                    trade["holding_duration"] = "N/A"

                break

        with open(self.journal_file, "w") as f:
            json.dump(data, f, indent=2)

        self._rebuild_csv(data["trades"])

    def _append_csv_row(self, t: Dict[str, Any]):
        with open(self.csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                t["trade_id"], t["date"], t["symbol"], t["strategy"], t["side"], t["qty"],
                t["entry_time"], t["entry_price"], t["exit_time"] or "-", t["exit_price"] or "-",
                t["stop_loss"], t["take_profit"], t["realized_pnl"] or "-", t["return_pct"] or "-",
                t["holding_duration"] or "-", t["exit_reason"] or "-", t["status"]
            ])

    def _rebuild_csv(self, trades: List[Dict[str, Any]]):
        with open(self.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Trade_ID", "Date", "Symbol", "Strategy", "Side", "Qty",
                "Entry_Time", "Entry_Price", "Exit_Time", "Exit_Price",
                "Stop_Loss", "Take_Profit", "Realized_PL", "Return_Pct",
                "Holding_Duration", "Exit_Reason", "Status"
            ])
            for t in trades:
                writer.writerow([
                    t["trade_id"], t["date"], t["symbol"], t["strategy"], t["side"], t["qty"],
                    t["entry_time"], t["entry_price"], t["exit_time"] or "-", t["exit_price"] or "-",
                    t["stop_loss"], t["take_profit"], t["realized_pnl"] or "-", t["return_pct"] or "-",
                    t["holding_duration"] or "-", t["exit_reason"] or "-", t["status"]
                ])
