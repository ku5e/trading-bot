"""
Politician copy trading strategy.
Scrapes Capitol Trades for recent congressional disclosures.
Filters to a target politician, copies their stock buys with a delay.
LLM is NOT used for trade decisions — only for summarizing findings.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import alpaca_client
import config

TARGET_POLITICIAN = "michael-mccaul"  # Capitol Trades URL slug — change to follow someone else
TRACKED_FILE = "paper_results/politician_tracked.csv"


def fetch_trades(politician_slug=TARGET_POLITICIAN, limit=20):
    """
    Scrape Capitol Trades for recent disclosures.
    Returns list of dicts: {symbol, trade_date, disclosed_date, type, size}
    """
    url = f"https://capitoltrades.com/politicians/{politician_slug}"
    headers = {"User-Agent": "Mozilla/5.0 (research/educational use)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table tbody tr")[:limit]
    trades = []
    for row in rows:
        cols = [c.get_text(strip=True) for c in row.select("td")]
        if len(cols) < 6:
            continue
        trades.append({
            "symbol": cols[1].upper(),
            "trade_date": cols[2],
            "disclosed_date": cols[3],
            "type": cols[4],      # "Purchase" or "Sale"
            "size": cols[5],      # "$1K-$15K" etc.
        })
    return trades


def parse_disclosed_date(date_str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def load_tracked():
    try:
        return pd.read_csv(TRACKED_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["symbol", "disclosed_date", "order_id"])


def save_tracked(df):
    df.to_csv(TRACKED_FILE, index=False)


def check_and_copy():
    """
    Run on schedule. Pull latest disclosures, enter any purchases
    that are past the delay window and not yet copied.
    """
    trades = fetch_trades()
    tracked = load_tracked()
    already_copied = set(tracked["symbol"].tolist())

    entered = []
    for trade in trades:
        if trade["type"].lower() != "purchase":
            continue
        if trade["symbol"] in already_copied:
            continue

        disclosed = parse_disclosed_date(trade["disclosed_date"])
        if disclosed is None:
            continue

        # Enforce delay: only act after COPY_TRADE_DELAY_DAYS past disclosure
        if datetime.now() < disclosed + timedelta(days=config.COPY_TRADE_DELAY_DAYS):
            print(f"[politician] {trade['symbol']}: disclosed {disclosed.date()}, waiting {config.COPY_TRADE_DELAY_DAYS}d")
            continue

        # Size bucket → qty (rough mapping, stays under MAX cap)
        price = alpaca_client.get_current_price(trade["symbol"])
        if price is None:
            continue
        qty = max(1, int(config.COPY_MAX_POSITION_USD / price))

        try:
            order = alpaca_client.place_market_order(trade["symbol"], qty, "buy")
            print(f"[politician] copied {trade['symbol']} x{qty} @ ~${price:.2f} — order {order.id}")
            new_row = pd.DataFrame([{
                "symbol": trade["symbol"],
                "disclosed_date": trade["disclosed_date"],
                "order_id": order.id,
            }])
            tracked = pd.concat([tracked, new_row], ignore_index=True)
            entered.append(trade["symbol"])
        except Exception as e:
            print(f"[politician] {trade['symbol']}: order failed — {e}")

    save_tracked(tracked)
    return entered
