import requests
import json
import pandas as pd
from tabulate import tabulate
from datetime import datetime
from config.settings import get_settings

def check():
    settings = get_settings()
    headers = {
        "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY
    }

    # 1. Account Info
    res_acc = requests.get(f"{settings.ALPACA_BASE_URL}/v2/account", headers=headers)
    account = res_acc.json()
    equity = float(account.get("equity", 0))
    last_equity = float(account.get("last_equity", 0))
    cash = float(account.get("cash", 0))
    buying_power = float(account.get("buying_power", 0))

    print("==========================================================================")
    print("💼 ALPACA ACCOUNT BALANCE & EQUITY OVERVIEW")
    print("==========================================================================")
    print(f"Current Equity:     ${equity:,.2f}")
    print(f"Previous Equity:    ${last_equity:,.2f}")
    daily_change = equity - last_equity
    daily_change_pct = (daily_change / last_equity) * 100 if last_equity > 0 else 0
    print(f"Session P&L:        ${daily_change:+,.2f} ({daily_change_pct:+.2f}%)")
    print(f"Available Cash:     ${cash:,.2f}")
    print(f"Buying Power:       ${buying_power:,.2f}")

    # 2. Open Positions
    res_pos = requests.get(f"{settings.ALPACA_BASE_URL}/v2/positions", headers=headers)
    positions = res_pos.json()
    print("\n==========================================================================")
    print("📦 ACTIVE OPEN POSITIONS")
    print("==========================================================================")
    if not positions:
        print("✅ No open positions held (EOD Flusher successfully closed all positions).")
    else:
        pos_table = []
        for p in positions:
            pos_table.append({
                "Symbol": p.get("symbol"),
                "Qty": p.get("qty"),
                "Avg Entry": f"${float(p.get('avg_entry_price', 0)):.2f}",
                "Current Price": f"${float(p.get('current_price', 0)):.2f}",
                "Market Value": f"${float(p.get('market_value', 0)):,.2f}",
                "Unrealized P&L": f"${float(p.get('unrealized_pl', 0)):+,.2f} ({float(p.get('unrealized_plpc', 0))*100:+.2f}%)"
            })
        print(tabulate(pos_table, headers="keys", tablefmt="fancy_grid"))

    # 3. Fill Activities (Trades executed on 2026-08-12 / 2026-08-13)
    res_act = requests.get(
        f"{settings.ALPACA_BASE_URL}/v2/account/activities?activity_types=FILL&after=2026-08-12T00:00:00Z&direction=asc",
        headers=headers
    )
    activities = res_act.json()
    print("\n==========================================================================")
    print("⚡ COMPLETED TRADE FILLS (LAST NIGHT SESSION)")
    print("==========================================================================")
    
    if not activities or isinstance(activities, dict) and "message" in activities:
        print("No fills recorded for this session.")
    else:
        fills_table = []
        # Group fills by symbol to calculate round-trip P&L
        trades_by_sym = {}
        for a in activities:
            sym = a.get("symbol")
            side = a.get("side").upper()
            qty = float(a.get("qty", 0))
            price = float(a.get("price", 0))
            t_time = a.get("transaction_time")
            
            fills_table.append({
                "Time (UTC)": t_time[:19].replace("T", " "),
                "Symbol": sym,
                "Side": side,
                "Qty": int(qty),
                "Price": f"${price:.2f}",
                "Total Value": f"${qty * price:,.2f}"
            })

            if sym not in trades_by_sym:
                trades_by_sym[sym] = {"buy_qty": 0, "buy_val": 0.0, "sell_qty": 0, "sell_val": 0.0}
            if side == "BUY":
                trades_by_sym[sym]["buy_qty"] += qty
                trades_by_sym[sym]["buy_val"] += qty * price
            elif side == "SELL":
                trades_by_sym[sym]["sell_qty"] += qty
                trades_by_sym[sym]["sell_val"] += qty * price

        print(tabulate(fills_table, headers="keys", tablefmt="fancy_grid"))

        # 4. Round-Trip P&L per Trade
        print("\n==========================================================================")
        print("🎯 ROUND-TRIP TRADE P&L BREAKDOWN")
        print("==========================================================================")
        pnl_table = []
        total_realized_pl = 0.0
        for sym, t in trades_by_sym.items():
            if t["buy_qty"] > 0 and t["sell_qty"] > 0:
                avg_buy = t["buy_val"] / t["buy_qty"]
                avg_sell = t["sell_val"] / t["sell_qty"]
                closed_qty = min(t["buy_qty"], t["sell_qty"])
                pnl = (avg_sell - avg_buy) * closed_qty
                pnl_pct = ((avg_sell - avg_buy) / avg_buy) * 100
                total_realized_pl += pnl
                pnl_table.append({
                    "Symbol": sym,
                    "Shares": int(closed_qty),
                    "Avg Buy": f"${avg_buy:.2f}",
                    "Avg Sell": f"${avg_sell:.2f}",
                    "Net P&L ($)": f"${pnl:+,.2f}",
                    "Return (%)": f"{pnl_pct:+.2f}%",
                    "Result": "🟢 WIN" if pnl > 0 else ("🔴 LOSS" if pnl < 0 else "⚪ BREAKEVEN")
                })
            else:
                pnl_table.append({
                    "Symbol": sym,
                    "Shares": int(t['buy_qty'] or t['sell_qty']),
                    "Avg Buy": f"${(t['buy_val']/t['buy_qty']):.2f}" if t['buy_qty'] else "-",
                    "Avg Sell": f"${(t['sell_val']/t['sell_qty']):.2f}" if t['sell_qty'] else "-",
                    "Net P&L ($)": "Open",
                    "Return (%)": "Open",
                    "Result": "🟡 INCOMPLETE"
                })
        print(tabulate(pnl_table, headers="keys", tablefmt="fancy_grid"))
        print(f"\n👉 Total Realized P&L from Night Trades: ${total_realized_pl:+,.2f}")

if __name__ == "__main__":
    check()
