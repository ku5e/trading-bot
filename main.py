"""
CLI entry point. Manage positions and check status without touching Alpaca dashboard.

Usage:
    python main.py status
    python main.py positions
    python main.py enter --symbol TSLA --qty 4
    python main.py queue --symbol XNDU --qty 100
    python main.py pending
    python main.py backtest --symbol AAPL --days 365
"""

import argparse
import json
import os
from datetime import datetime
import alpaca_client
from strategies import trailing_stop
from backtester.backtest import run as run_backtest

PENDING_FILE = os.path.join(os.path.dirname(__file__), "paper_results", "pending_orders.json")


def cmd_status():
    account = alpaca_client.get_account()
    print(f"Equity:  ${float(account.equity):.2f}")
    print(f"Cash:    ${float(account.cash):.2f}")
    print(f"BP:      ${float(account.buying_power):.2f}")


def cmd_positions():
    positions = alpaca_client.get_all_positions()
    if not positions:
        print("No open positions.")
        return
    for p in positions:
        pnl = float(p.unrealized_pl)
        pnl_pct = float(p.unrealized_plpc) * 100
        print(
            f"{p.symbol}: {p.qty} shares @ avg ${float(p.avg_entry_price):.2f} | "
            f"current ${float(p.current_price):.2f} | P&L ${pnl:.2f} ({pnl_pct:.1f}%)"
        )


def cmd_enter(symbol, qty):
    order = trailing_stop.enter_position(symbol.upper(), qty)
    print(f"Order placed: {order.id}")


def cmd_queue(symbol, qty):
    os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
    orders = []
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE) as f:
            orders = json.load(f)
    orders.append({"symbol": symbol.upper(), "qty": qty, "queued_at": datetime.now().isoformat()})
    with open(PENDING_FILE, "w") as f:
        json.dump(orders, f, indent=2)
    print(f"Queued: {symbol.upper()} x{qty} — executes at tomorrow's open (9:31 AM ET)")


def cmd_pending():
    if not os.path.exists(PENDING_FILE):
        print("No pending orders.")
        return
    with open(PENDING_FILE) as f:
        orders = json.load(f)
    if not orders:
        print("No pending orders.")
        return
    for o in orders:
        print(f"{o['symbol']} x{o['qty']} — queued {o['queued_at']}")


def cmd_backtest(symbol, days):
    run_backtest(symbol.upper(), days, "trailing_stop")


def main():
    parser = argparse.ArgumentParser(description="Trading bot CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show account equity and cash")
    sub.add_parser("positions", help="Show all open positions")

    enter_p = sub.add_parser("enter", help="Buy now and register for trailing stop")
    enter_p.add_argument("--symbol", required=True)
    enter_p.add_argument("--qty", type=int, required=True)

    queue_p = sub.add_parser("queue", help="Queue a buy for next market open (9:31 AM ET)")
    queue_p.add_argument("--symbol", required=True)
    queue_p.add_argument("--qty", type=int, required=True)

    sub.add_parser("pending", help="Show queued orders not yet executed")

    bt_p = sub.add_parser("backtest", help="Run trailing stop backtest")
    bt_p.add_argument("--symbol", required=True)
    bt_p.add_argument("--days", type=int, default=365)

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "positions":
        cmd_positions()
    elif args.command == "enter":
        cmd_enter(args.symbol, args.qty)
    elif args.command == "queue":
        cmd_queue(args.symbol, args.qty)
    elif args.command == "pending":
        cmd_pending()
    elif args.command == "backtest":
        cmd_backtest(args.symbol, args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
