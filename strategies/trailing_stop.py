"""
Trailing stop strategy.
Rules are deterministic Python — LLM never touches the math.

Entry: manual (you tell it what to buy via main.py or CLI).
Stop: sell if price drops TRAILING_STOP_DROP_PCT below entry.
Trail: when price rises TRAILING_STOP_RAISE_TRIGGER above entry,
       raise the floor to current_price * (1 - TRAILING_STOP_FLOOR_OFFSET).
       Floor only ever moves up.

PRODUCTION NOTE:
Current stop logic is software-only — fires on the next 5-minute check, not instantly.
A gap-down at open or a news spike can blow through the floor before the bot checks.
For live money: on enter_position, submit a stop order to Alpaca at the initial floor.
When the floor ratchets up, cancel the existing stop order and submit a new one at the
new floor. Alpaca's stop sits on their servers and fires immediately regardless of
whether this bot is running.
"""

import json
import os
from datetime import datetime
import alpaca_client
import config
import notifier

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "paper_results", "trailing_state.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def add_position(symbol, entry_price, qty, strategy="trailing_stop"):
    """Register a new position to be managed by trailing stop."""
    state = load_state()
    floor = entry_price * (1 - config.TRAILING_STOP_DROP_PCT)
    state[symbol] = {
        "entry_price": entry_price,
        "qty": qty,
        "floor": floor,
        "peak": entry_price,
        "entered_at": datetime.now().isoformat(),
        "strategy": strategy,
    }
    save_state(state)
    print(f"[trailing] {symbol} registered. Entry ${entry_price:.2f}, floor ${floor:.2f}")


def check_and_manage():
    """Run on schedule. Check all tracked positions, update floors, fire stops."""
    state = load_state()
    if not state:
        return

    for symbol, data in list(state.items()):
        if data.get("strategy", "trailing_stop") != "trailing_stop":
            continue
        price = alpaca_client.get_current_price(symbol)
        if price is None:
            print(f"[trailing] {symbol}: could not fetch price, skipping")
            continue

        floor = data["floor"]
        peak = data["peak"]
        entry = data["entry_price"]
        qty = data["qty"]

        # Update peak
        if price > peak:
            data["peak"] = price
            # Raise floor if we've gained enough
            gain_pct = (price - entry) / entry
            if gain_pct >= config.TRAILING_STOP_RAISE_TRIGGER:
                new_floor = price * (1 - config.TRAILING_STOP_FLOOR_OFFSET)
                if new_floor > floor:
                    data["floor"] = new_floor
                    print(f"[trailing] {symbol}: floor raised to ${new_floor:.2f} (price ${price:.2f})")

        # Check stop
        if price <= data["floor"]:
            print(f"[trailing] {symbol}: STOP triggered at ${price:.2f} (floor ${data['floor']:.2f})")
            try:
                order = alpaca_client.place_market_order(symbol, qty, "sell")
                print(f"[trailing] {symbol}: sell order placed — {order.id}")
                pnl = (price - data["entry_price"]) * qty
                notifier.action(
                    f"SELL {symbol} — trailing stop triggered",
                    f"Symbol: {symbol}\nQty: {qty}\nEntry: ${data['entry_price']:.2f}\n"
                    f"Exit: ${price:.2f}\nFloor: ${data['floor']:.2f}\n"
                    f"P&L: ${pnl:+.2f}\nOrder ID: {order.id}\nStrategy: trailing stop",
                )
                del state[symbol]
            except Exception as e:
                print(f"[trailing] {symbol}: sell failed — {e}")
        else:
            print(
                f"[trailing] {symbol}: ${price:.2f} | floor ${data['floor']:.2f} | "
                f"peak ${data['peak']:.2f} | P&L {((price - entry)/entry)*100:.1f}%"
            )

    save_state(state)


def enter_position(symbol, qty, strategy="trailing_stop"):
    """Buy and register for trailing stop management."""
    order = alpaca_client.place_market_order(symbol, qty, "buy")
    print(f"[trailing] {symbol}: buy order placed — {order.id}")
    fill_price = alpaca_client.get_fill_price(order.id)
    print(f"[trailing] {symbol}: filled at ${fill_price:.2f}")
    add_position(symbol, fill_price, qty, strategy=strategy)
    notifier.action(
        f"BUY {symbol} — position entered",
        f"Symbol: {symbol}\nQty: {qty}\nFill price: ${fill_price:.2f}\n"
        f"Position value: ${fill_price * qty:,.2f}\n"
        f"Initial floor: ${fill_price * (1 - config.TRAILING_STOP_DROP_PCT):.2f}\n"
        f"Order ID: {order.id}\nStrategy: {strategy}",
    )
    return order
