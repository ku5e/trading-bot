"""
Example Strategy — Template for building new strategies.

Copy this file, rename it (e.g. momentum_breakout.py), and implement the two
required functions: enter_position() and check_and_manage().

Then register it in strategies/__init__.py:

    from strategies import trailing_stop, momentum_breakout

    REGISTRY = {
        "trailing_stop": trailing_stop,
        "momentum_breakout": momentum_breakout,
    }

Once registered, use it from the CLI:

    python main.py enter --symbol KVYO --qty 50 --strategy momentum_breakout
    python main.py queue --symbol KVYO --qty 50 --strategy momentum_breakout

The scheduler will automatically call check_and_manage() every 5 minutes
during market hours for all positions tagged with your strategy name.
"""

import json
import os
from datetime import datetime
import alpaca_client
import config
import notifier

# ── State file ────────────────────────────────────────────────────────────────
# Each strategy uses the shared trailing_state.json. Positions are tagged with
# the strategy name so each strategy only touches its own positions.
# You can use a separate state file if your strategy needs different fields.

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "paper_results", "trailing_state.json")

STRATEGY_NAME = "example_strategy"  # must match the key in REGISTRY


# ── State helpers ─────────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Required: enter_position() ────────────────────────────────────────────────
# Called by: main.py enter, main.py queue (via scheduler at 9:31 AM)
# Must: place a buy order, record the position in state, send a buy notification.
# Must accept: symbol (str), qty (int), strategy (str) — always pass strategy
# through so the state tag is set correctly even if this function is called
# from outside the module.

def enter_position(symbol, qty, strategy=STRATEGY_NAME):
    """
    Buy the symbol and register it for management by this strategy.

    This function is called once — at entry. After this, check_and_manage()
    handles the position every 5 minutes until exit.
    """
    # 1. Place the buy order via Alpaca
    order = alpaca_client.place_market_order(symbol, qty, "buy")
    print(f"[{STRATEGY_NAME}] {symbol}: buy order placed — {order.id}")

    # 2. Wait for fill and get the actual fill price
    fill_price = alpaca_client.get_fill_price(order.id)
    print(f"[{STRATEGY_NAME}] {symbol}: filled at ${fill_price:.2f}")

    # 3. Record the position in state with whatever fields your strategy needs
    state = load_state()
    state[symbol] = {
        "entry_price": fill_price,
        "qty": qty,
        "strategy": strategy,           # REQUIRED — do not omit
        "entered_at": datetime.now().isoformat(),

        # Add any strategy-specific fields below.
        # Examples:
        # "target_price": fill_price * 1.15,   # 15% profit target
        # "stop_price": fill_price * 0.92,      # 8% hard stop
        # "hold_days": 5,                        # time-based exit
        # "highest_close": fill_price,           # for momentum tracking
    }
    save_state(state)

    # 4. Send buy notification email
    notifier.action(
        f"BUY {symbol} — {strategy}",
        f"Symbol: {symbol}\n"
        f"Qty: {qty}\n"
        f"Fill price: ${fill_price:.2f}\n"
        f"Position value: ${fill_price * qty:,.2f}\n"
        f"Order ID: {order.id}\n"
        f"Strategy: {strategy}",
    )

    return order


# ── Required: check_and_manage() ──────────────────────────────────────────────
# Called by: scheduler every 5 minutes during market hours (9:30–16:00 ET Mon–Fri)
# Must: load state, filter to your strategy's positions, apply exit logic,
#       sell when conditions are met, remove the position from state on exit.
# Must NOT touch positions tagged with a different strategy name.

def check_and_manage():
    """
    Run exit logic for all positions owned by this strategy.

    Called every 5 minutes during market hours. Keep this fast — it runs
    alongside all other registered strategies in the same scheduler tick.
    """
    state = load_state()
    if not state:
        return

    for symbol, data in list(state.items()):

        # REQUIRED: skip positions that belong to other strategies
        if data.get("strategy", "trailing_stop") != STRATEGY_NAME:
            continue

        # Fetch the current price
        price = alpaca_client.get_current_price(symbol)
        if price is None:
            print(f"[{STRATEGY_NAME}] {symbol}: could not fetch price, skipping")
            continue

        entry = data["entry_price"]
        qty = data["qty"]
        pnl_pct = (price - entry) / entry * 100

        print(f"[{STRATEGY_NAME}] {symbol}: ${price:.2f} | entry ${entry:.2f} | P&L {pnl_pct:+.1f}%")

        # ── Exit logic — implement your rules here ────────────────────────────
        #
        # Example A — Fixed profit target + hard stop:
        #   sell_signal = price >= data["target_price"] or price <= data["stop_price"]
        #
        # Example B — Time-based exit (hold N days):
        #   entered = datetime.fromisoformat(data["entered_at"])
        #   days_held = (datetime.now() - entered).days
        #   sell_signal = days_held >= data["hold_days"]
        #
        # Example C — Momentum fade (sell when 3-day RSI drops below 40):
        #   rsi = compute_rsi(symbol, period=3)   # you would implement this
        #   sell_signal = rsi < 40
        #
        # For this template, a simple 10% gain target or 5% stop is used:

        target = entry * 1.10   # sell if up 10%
        stop = entry * 0.95     # sell if down 5%
        sell_signal = price >= target or price <= stop

        # ─────────────────────────────────────────────────────────────────────

        if sell_signal:
            reason = "target hit" if price >= target else "stop hit"
            print(f"[{STRATEGY_NAME}] {symbol}: SELL — {reason} at ${price:.2f}")
            try:
                order = alpaca_client.place_market_order(symbol, qty, "sell")
                pnl_usd = (price - entry) * qty
                notifier.action(
                    f"SELL {symbol} — {STRATEGY_NAME} ({reason})",
                    f"Symbol: {symbol}\n"
                    f"Qty: {qty}\n"
                    f"Entry: ${entry:.2f}\n"
                    f"Exit: ${price:.2f}\n"
                    f"P&L: ${pnl_usd:+.2f} ({pnl_pct:+.1f}%)\n"
                    f"Reason: {reason}\n"
                    f"Order ID: {order.id}\n"
                    f"Strategy: {STRATEGY_NAME}",
                )
                del state[symbol]
            except Exception as e:
                print(f"[{STRATEGY_NAME}] {symbol}: sell failed — {e}")

    save_state(state)
