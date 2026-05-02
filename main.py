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


def cmd_price(symbol):
    price = alpaca_client.get_current_price(symbol.upper())
    if price is None:
        print(f"Could not fetch price for {symbol.upper()}")
    else:
        print(f"{symbol.upper()}: ${price:.2f}")


def cmd_backtest(symbol, days):
    run_backtest(symbol.upper(), days, "trailing_stop")


def main():
    parser = argparse.ArgumentParser(
        description="Trading bot CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Commands:\n"
            "  status      Show account equity and cash\n"
            "              python main.py status\n\n"
            "  positions   Show all open positions with P&L\n"
            "              python main.py positions\n\n"
            "  price       Get current price for a symbol\n"
            "              python main.py price --symbol XNDU\n\n"
            "  enter       Buy immediately and register for trailing stop\n"
            "              python main.py enter --symbol XNDU --qty 100\n\n"
            "  queue       Queue a buy for next market open (9:31 AM ET)\n"
            "              python main.py queue --symbol XNDU --qty 100\n\n"
            "  pending     Show queued orders not yet executed\n"
            "              python main.py pending\n\n"
            "  backtest    Run trailing stop backtest on historical data\n"
            "              python main.py backtest --symbol XNDU --days 365\n"
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show account equity and cash  |  python main.py status")
    sub.add_parser("positions", help="Show all open positions  |  python main.py positions")

    price_p = sub.add_parser("price", help="Get current price  |  python main.py price --symbol XNDU")
    price_p.add_argument("--symbol", required=True)

    enter_p = sub.add_parser("enter", help="Buy now + trailing stop  |  python main.py enter --symbol XNDU --qty 100")
    enter_p.add_argument("--symbol", required=True)
    enter_p.add_argument("--qty", type=int, required=True)

    queue_p = sub.add_parser("queue", help="Queue buy for 9:31 AM open  |  python main.py queue --symbol XNDU --qty 100")
    queue_p.add_argument("--symbol", required=True)
    queue_p.add_argument("--qty", type=int, required=True)

    sub.add_parser("pending", help="Show queued orders  |  python main.py pending")

    bt_p = sub.add_parser("backtest", help="Backtest trailing stop  |  python main.py backtest --symbol XNDU --days 365")
    bt_p.add_argument("--symbol", required=True)
    bt_p.add_argument("--days", type=int, default=365)

    args = parser.parse_args()

    if args.command == "price":
        cmd_price(args.symbol)
    elif args.command == "status":
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
