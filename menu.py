"""
Trading Bot — DOS-style menu interface.
Run: python menu.py
"""

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.prompt import Prompt
from rich import box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main as bot
from strategies import REGISTRY

DOS = Theme({
    "hdr":   "bold bright_green on black",
    "txt":   "bright_green on black",
    "dim":   "green on black",
    "key":   "bold bright_green on black",
    "err":   "bold bright_red on black",
})

console = Console(theme=DOS, highlight=False)


def clear():
    console.clear()


def header():
    console.print(
        Panel(
            "[hdr]  KU5E SYSTEMS — TRADING BOT                            [Ver. 1.0][/hdr]",
            style="bright_green on black",
            box=box.DOUBLE,
            padding=(0, 1),
        )
    )


def draw_menu():
    clear()
    header()

    table = Table(
        box=None,
        show_header=False,
        style="bright_green on black",
        padding=(0, 3),
        expand=False,
    )
    table.add_column("key",  style="bold bright_green on black", width=5)
    table.add_column("cmd",  style="bold bright_green on black", width=14)
    table.add_column("desc", style="green on black")

    rows = [
        ("[ 1 ]", "STATUS",     "Account equity and cash"),
        ("[ 2 ]", "POSITIONS",  "Open positions with P&L"),
        ("[ 3 ]", "STRATEGIES", "List registered strategies"),
        ("[ 4 ]", "PRICE",      "Current price for a symbol"),
        ("[ 5 ]", "ENTER",      "Buy now + register with strategy"),
        ("[ 6 ]", "QUEUE",      "Queue buy for 9:31 AM open"),
        ("[ 7 ]", "PENDING",    "Show queued orders"),
        ("[ 8 ]", "CANCEL",     "Remove symbol from queue"),
        ("[ 9 ]", "BACKTEST",   "Run backtest on symbol"),
        ("[ 0 ]", "EXIT",       ""),
    ]

    for key, cmd, desc in rows:
        table.add_row(key, cmd, desc)

    console.print(
        Panel(
            table,
            box=box.DOUBLE,
            style="bright_green on black",
            title="[hdr][ COMMAND CENTER ][/hdr]",
            title_align="left",
            padding=(1, 2),
        )
    )
    console.print("[dim]  F10:EXIT   ENTER:SELECT[/dim]\n")


def ask(label, default=None):
    suffix = f" [dim](default: {default})[/dim]" if default else ""
    val = console.input(f"[txt]    {label}{suffix}:[/txt] ").strip()
    return val if val else default


def ask_int(label, default=None):
    raw = ask(label, str(default) if default is not None else None)
    try:
        return int(raw)
    except (TypeError, ValueError):
        console.print(f"[err]  INVALID — expected a number[/err]")
        return None


def pause():
    console.input("\n[dim]  Press ENTER to continue...[/dim]")


def section(title):
    console.print(f"\n[hdr]  ── {title} ──[/hdr]\n")


def run():
    strat_keys = " / ".join(REGISTRY.keys())

    while True:
        draw_menu()
        choice = console.input("[txt]C:\\>[/txt] ").strip()

        clear()
        header()

        if choice == "0":
            console.print("\n[txt]  GOODBYE.[/txt]\n")
            break

        elif choice == "1":
            section("ACCOUNT STATUS")
            bot.cmd_status()
            pause()

        elif choice == "2":
            section("OPEN POSITIONS")
            bot.cmd_positions()
            pause()

        elif choice == "3":
            section("REGISTERED STRATEGIES")
            bot.cmd_strategies()
            pause()

        elif choice == "4":
            section("PRICE LOOKUP")
            symbol = ask("SYMBOL")
            if symbol:
                console.print()
                bot.cmd_price(symbol)
            pause()

        elif choice == "5":
            section("ENTER POSITION")
            symbol  = ask("SYMBOL")
            qty     = ask_int("QTY")
            strategy = ask("STRATEGY", default="trailing_stop")
            if symbol and qty:
                console.print()
                try:
                    bot.cmd_enter(symbol, qty, strategy)
                except Exception as e:
                    console.print(f"[err]  ERROR: {e}[/err]")
            pause()

        elif choice == "6":
            section("QUEUE ORDER")
            symbol   = ask("SYMBOL")
            qty      = ask_int("QTY")
            strategy = ask("STRATEGY", default="trailing_stop")
            console.print(f"[dim]  Available: {strat_keys}[/dim]")
            if symbol and qty:
                console.print()
                try:
                    bot.cmd_queue(symbol, qty, strategy)
                except Exception as e:
                    console.print(f"[err]  ERROR: {e}[/err]")
            pause()

        elif choice == "7":
            section("PENDING ORDERS")
            bot.cmd_pending()
            pause()

        elif choice == "8":
            section("CANCEL ORDER")
            symbol = ask("SYMBOL")
            if symbol:
                console.print()
                bot.cmd_cancel(symbol)
            pause()

        elif choice == "9":
            section("BACKTEST")
            symbol = ask("SYMBOL")
            days   = ask_int("DAYS", default=365)
            if symbol and days:
                console.print()
                try:
                    bot.cmd_backtest(symbol, days)
                except Exception as e:
                    console.print(f"[err]  ERROR: {e}[/err]")
            pause()

        else:
            console.print("\n[err]  INVALID SELECTION[/err]")
            pause()


if __name__ == "__main__":
    run()
