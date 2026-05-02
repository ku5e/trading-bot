"""
Scheduler — runs both strategies on their respective cadences.
Trailing stop: every 5 min during market hours (Mon-Fri 9:30-16:00 ET).
Politician copy: once per day at market open.
Daily summary via Ollama at market close.
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime
import logging
import json
import os
import sys

import alpaca_client
import config
import ollama_client
import notifier
from strategies import trailing_stop, politician_copy, REGISTRY

PENDING_FILE = os.path.join(os.path.dirname(__file__), "paper_results", "pending_orders.json")

ET = pytz.timezone("US/Eastern")

os.makedirs("paper_results", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("paper_results/scheduler.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def send_email(subject, body):
    notifier.send_email(subject, body)


def is_market_hours():
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    t = now.time()
    from datetime import time
    return time(9, 30) <= t <= time(16, 0)


def run_pending_orders():
    if not os.path.exists(PENDING_FILE):
        return
    with open(PENDING_FILE) as f:
        orders = json.load(f)
    if not orders:
        return
    remaining = []
    for o in orders:
        symbol, qty = o["symbol"], o["qty"]
        strategy_name = o.get("strategy", "trailing_stop")
        try:
            strategy = REGISTRY[strategy_name]
            strategy.enter_position(symbol, qty, strategy=strategy_name)
            log.info(f"[pending] {symbol} x{qty} ({strategy_name}) executed at open")
        except Exception as e:
            log.error(f"[pending] {symbol} x{qty} failed: {e}")
            remaining.append(o)
    with open(PENDING_FILE, "w") as f:
        json.dump(remaining, f, indent=2)


def run_all_strategies():
    if not is_market_hours():
        return
    log.info(f"[scheduler] strategy check — {datetime.now(ET).strftime('%H:%M:%S ET')}")
    for name, strategy in REGISTRY.items():
        try:
            strategy.check_and_manage()
        except Exception as e:
            log.error(f"[scheduler] {name} check_and_manage failed: {e}")


def run_politician_copy():
    if not is_market_hours():
        return
    log.info(f"[scheduler] politician copy check — {datetime.now(ET).strftime('%H:%M:%S ET')}")
    politician_copy.check_and_copy()


def run_morning_brief():
    try:
        positions = alpaca_client.get_all_positions()
        account = alpaca_client.get_account()
        pending = []
        if os.path.exists(PENDING_FILE):
            with open(PENDING_FILE) as f:
                pending = json.load(f)

        lines = [f"Trading Bot — Morning Brief {datetime.now(ET).strftime('%Y-%m-%d')}"]
        lines.append(f"\nAccount: ${float(account.equity):,.2f} equity | ${float(account.buying_power):,.2f} buying power")

        if positions:
            lines.append(f"\nOpen Positions ({len(positions)}):")
            for p in positions:
                pnl = float(p.unrealized_pl)
                lines.append(f"  {p.symbol}: {p.qty} shares @ ${float(p.avg_entry_price):.2f} | P&L ${pnl:+.2f}")
        else:
            lines.append("\nNo open positions.")

        if pending:
            lines.append(f"\nPending Orders ({len(pending)}) — execute at 9:31:")
            for o in pending:
                lines.append(f"  {o['symbol']} x{o['qty']}")
        else:
            lines.append("\nNo pending orders.")

        lines.append(f"\nCopying: {politician_copy.TARGET_POLITICIAN}")

        body = "\n".join(lines)
        log.info(f"[morning brief]\n{body}")
        send_email(f"Trading Bot — Morning Brief {datetime.now(ET).date()}", body)
    except Exception as e:
        log.error(f"[scheduler] morning brief failed: {e}")


def run_daily_summary():
    if not is_market_hours():
        return
    try:
        positions = alpaca_client.get_all_positions()
        account = alpaca_client.get_account()
        summary = ollama_client.summarize_positions(positions, account)
        log.info(f"[daily summary]\n{summary}")
        with open("paper_results/daily_summary.txt", "a") as f:
            f.write(f"\n--- {datetime.now(ET).date()} ---\n{summary}\n")
        send_email(f"Trading Bot — EOD Summary {datetime.now(ET).date()}", summary)
    except Exception as e:
        log.error(f"[scheduler] daily summary failed: {e}")


def run_catchup():
    """Run jobs that fire once at open if the scheduler started after their trigger time."""
    now = datetime.now(ET)
    if not is_market_hours():
        return
    from datetime import time
    past_931 = now.time() >= time(9, 31)
    past_935 = now.time() >= time(9, 35)
    if past_931:
        log.info("[scheduler] late start — running pending orders now")
        run_pending_orders()
    if past_935:
        log.info("[scheduler] late start — running politician copy now")
        run_politician_copy()
        run_all_strategies()


def start():
    sched = BlockingScheduler(timezone=ET)

    # Morning brief: 9:30 AM ET (market open)
    sched.add_job(
        run_morning_brief,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=30, timezone=ET),
    )

    # Pending orders: execute at 9:31 AM ET (1 min after open)
    sched.add_job(
        run_pending_orders,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=31, timezone=ET),
    )

    # All strategies: every 5 min, market hours
    sched.add_job(
        run_all_strategies,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/5", timezone=ET),
    )

    # Politician copy: daily at 9:35 AM ET (after open settles)
    sched.add_job(
        run_politician_copy,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=35, timezone=ET),
    )

    # Daily summary: 3:55 PM ET (5 min before close)
    sched.add_job(
        run_daily_summary,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=55, timezone=ET),
    )

    run_catchup()

    log.info("[scheduler] started. Running trailing stop + politician copy.")
    log.info("Press Ctrl+C to stop.")
    sched.start()


if __name__ == "__main__":
    start()
