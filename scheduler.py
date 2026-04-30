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
import os
import sys

import alpaca_client
import ollama_client
from strategies import trailing_stop, politician_copy

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


def is_market_hours():
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    t = now.time()
    from datetime import time
    return time(9, 30) <= t <= time(16, 0)


def run_trailing_stop():
    if not is_market_hours():
        return
    log.info(f"[scheduler] trailing stop check — {datetime.now(ET).strftime('%H:%M:%S ET')}")
    trailing_stop.check_and_manage()


def run_politician_copy():
    if not is_market_hours():
        return
    log.info(f"[scheduler] politician copy check — {datetime.now(ET).strftime('%H:%M:%S ET')}")
    politician_copy.check_and_copy()


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
    except Exception as e:
        log.error(f"[scheduler] daily summary failed: {e}")


def start():
    sched = BlockingScheduler(timezone=ET)

    # Trailing stop: every 5 min, market hours
    sched.add_job(
        run_trailing_stop,
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

    log.info("[scheduler] started. Running trailing stop + politician copy.")
    log.info("Press Ctrl+C to stop.")
    sched.start()


if __name__ == "__main__":
    start()
