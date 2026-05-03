# Trading Bot — Manual

A paper trading bot wired to Alpaca's paper trading API. Runs two built-in strategies — a trailing stop and a congressional disclosure copier — on a scheduler during market hours. Fully extensible: new strategies are single Python files.

---

## Table of Contents

1. [Requirements](#1-requirements)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Running the Bot](#4-running-the-bot)
5. [CLI Reference](#5-cli-reference)
6. [Menu Interface](#6-menu-interface)
7. [Architecture Overview](#7-architecture-overview)
8. [Built-in Strategies](#8-built-in-strategies)
9. [Risk Guardrails](#9-risk-guardrails)
10. [Backtesting](#10-backtesting)
11. [Email Notifications](#11-email-notifications)
12. [Building a New Strategy](#12-building-a-new-strategy)
13. [Known Limitations](#13-known-limitations)

---

## 1. Requirements

- Python 3.10+
- Alpaca paper trading account (free at alpaca.markets)
- Alpaca API key and secret key

Optional:
- Ollama running locally or on a remote host (used for EOD summary only)
- SMTP credentials (used for email alerts)

---

## 2. Installation

```bash
git clone https://github.com/ku5e/trading-bot.git
cd trading-bot
pip install -r requirements.txt
```

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
```

---

## 3. Configuration

All configuration lives in `.env`. The bot reads it at startup via `config.py`.

### Required

```env
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

Use the paper trading URL until you are ready for live money.

### Optional — Ollama (EOD summary)

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

If `OLLAMA_HOST` is not set, the EOD summary job is skipped silently.

### Optional — Email alerts

```env
EMAIL_SMTP=smtp.mailjet.com
EMAIL_PORT=587
EMAIL_USER=your_smtp_user
EMAIL_PASS=your_smtp_pass
EMAIL_FROM=trader-bot@yourdomain.com
EMAIL_TO=you@yourdomain.com
```

If `EMAIL_SMTP` or `EMAIL_TO` are not set, email is skipped silently. All other bot functions work without it.

### Risk guardrails (in `config.py`)

These are not in `.env` — they are constants in code so they cannot be accidentally overridden at runtime.

| Setting | Default | Meaning |
|---|---|---|
| `MAX_POSITION_SIZE_USD` | $5,000 | Max dollars in any single order |
| `MAX_ACCOUNT_RISK_PCT` | 10% | Max % of account equity per trade |
| `TRAILING_STOP_DROP_PCT` | 10% | Initial stop floor below entry |
| `TRAILING_STOP_RAISE_TRIGGER` | 10% | Gain required before floor ratchets up |
| `TRAILING_STOP_FLOOR_OFFSET` | 5% | New floor = current price - 5% |

---

## 4. Running the Bot

### Scheduler (automated, market hours)

```bash
python scheduler.py
```

The scheduler runs all registered strategies on a cron cadence:

| Time (ET) | Job |
|---|---|
| 9:30 AM Mon–Fri | Morning brief email |
| 9:31 AM Mon–Fri | Execute any pending (queued) orders |
| Every 5 min, 9:30–4:00 PM Mon–Fri | Run `check_and_manage()` on all strategies |
| 9:35 AM Mon–Fri | Politician copy check |
| 3:55 PM Mon–Fri | EOD summary via Ollama + email |

If the scheduler starts after any of these trigger times, it runs a catchup pass immediately.

Use tmux to keep the scheduler running in the background:

```bash
tmux new-session -d -s trading 'python scheduler.py'
tmux attach -t trading      # view logs
Ctrl+B, D                   # detach (leaves bot running)
```

### One-off commands

```bash
python main.py status
python main.py positions
```

See [CLI Reference](#5-cli-reference) for all commands.

---

## 5. CLI Reference

```
python main.py <command> [options]
```

| Command | Description | Example |
|---|---|---|
| `status` | Account equity, cash, buying power | `python main.py status` |
| `positions` | All open positions with P&L | `python main.py positions` |
| `strategies` | List registered strategies | `python main.py strategies` |
| `price` | Current price for a symbol | `python main.py price --symbol TSLA` |
| `enter` | Buy immediately + register with strategy | `python main.py enter --symbol TSLA --qty 10 --strategy trailing_stop` |
| `queue` | Queue a buy for next 9:31 AM open | `python main.py queue --symbol TSLA --qty 10 --strategy trailing_stop` |
| `pending` | Show queued orders not yet executed | `python main.py pending` |
| `cancel` | Remove a symbol from the queue | `python main.py cancel --symbol TSLA` |
| `backtest` | Run trailing stop backtest | `python main.py backtest --symbol TSLA --days 365` |

**Notes:**
- `--strategy` defaults to `trailing_stop` if omitted.
- `queue` stores orders in `paper_results/pending_orders.json`. The scheduler executes them at 9:31 AM the next market day.
- `cancel` removes by symbol. If the same symbol is queued twice, both entries are removed.

---

## 6. Menu Interface

```bash
python menu.py
```

A DOS-style interactive menu. Green on black, double-box borders. All CLI commands are available through numbered options. Enter a number, the menu prompts for any required inputs, runs the command, and displays the result. Press Enter to return to the main menu. `0` exits.

---

## 7. Architecture Overview

```
trading-bot/
├── main.py                  CLI entry point
├── menu.py                  Interactive DOS-style menu
├── scheduler.py             APScheduler — runs all jobs during market hours
├── config.py                Settings and risk guardrails (reads .env)
├── alpaca_client.py         Alpaca API wrapper (all order + data calls go here)
├── notifier.py              Email alert sender
├── ollama_client.py         Ollama wrapper (EOD summary only)
├── strategies/
│   ├── __init__.py          REGISTRY — maps strategy names to modules
│   ├── trailing_stop.py     Built-in trailing stop strategy
│   ├── politician_copy.py   Built-in congressional disclosure copier
│   └── example_strategy.py  Template — copy this to build a new strategy
├── backtester/
│   └── backtest.py          Historical simulation for trailing stop
└── paper_results/
    ├── trailing_stop_state.json     Live state for trailing stop positions
    ├── pending_orders.json          Orders queued for next market open
    ├── politician_tracked.csv       Disclosures already copied (dedup log)
    └── scheduler.log                Scheduler output log
```

### How strategies are registered

`strategies/__init__.py` holds the REGISTRY:

```python
from strategies import trailing_stop

REGISTRY = {
    "trailing_stop": trailing_stop,
}
```

The scheduler calls `check_and_manage()` on every registered strategy every 5 minutes. `main.py` routes `enter` and `queue` commands to the right module via `REGISTRY[strategy_name]`.

Adding a new strategy requires:
1. A Python file in `strategies/`
2. One line in `REGISTRY`

Nothing else changes.

---

## 8. Built-in Strategies

### Trailing Stop (`trailing_stop`)

**Entry:** Manual. Use `enter` or `queue` from the CLI or menu.

**Exit logic:**
- Sets an initial floor at `entry_price * (1 - TRAILING_STOP_DROP_PCT)` (default: 10% below entry).
- Checks price every 5 minutes during market hours.
- When price rises 10% above entry, raises the floor to `current_price * (1 - TRAILING_STOP_FLOOR_OFFSET)` (default: 5% below current). Floor only ever moves up.
- Sells when price drops to or below the floor.

**State file:** `paper_results/trailing_stop_state.json`

**Example:**
- Buy at $100. Floor set at $90.
- Price rises to $115 (+15%). Floor raises to $109.25 (5% below $115).
- Price drops to $108. Stop triggers. Sell at $108. P&L: +8%.

**Production note:** The stop fires on the next 5-minute check, not instantly. A gap-down at open or a news spike can blow through the floor before the bot wakes up. For live money, submit a stop-limit order to Alpaca at entry and update it when the floor ratchets. Alpaca's stop sits on their servers and fires immediately regardless of whether this bot is running.

---

### Politician Copy (`politician_copy`)

**Entry:** Automatic. Runs once daily at 9:35 AM ET.

Scrapes Capitol Trades for recent purchase disclosures from a target politician (default: `gil-cisneros`). For each new purchase not yet copied:
- Looks up current price.
- Calculates qty: `floor(COPY_MAX_POSITION_USD / price)` (capped at $5,000).
- Places a market buy.
- Logs the symbol to `paper_results/politician_tracked.csv` to prevent duplicate entries.

**Exit:** Configurable. Set `POLITICIAN_EXIT_STRATEGY` in `config.py` to any registered strategy name to hand off exit management automatically. Default is `None` — manual exit via CLI or Alpaca dashboard.

When `POLITICIAN_EXIT_STRATEGY` is set, after each buy the bot:
1. Waits for the fill price via `get_fill_price()`
2. Calls `strategy.add_position()` to register the position in that strategy's state file
3. The exit strategy's `check_and_manage()` picks it up on the next 5-minute tick

Example — auto-manage politician copy exits with trailing stop:

```python
# config.py
POLITICIAN_EXIT_STRATEGY = "trailing_stop"
```

For a new strategy to support this, implement `add_position(symbol, entry_price, qty, strategy)` in the strategy module. See the commented template in `strategies/example_strategy.py`.

**To follow a different politician:** Change `TARGET_POLITICIAN` in `strategies/politician_copy.py` to any Capitol Trades URL slug (the name as it appears in the URL at capitoltrades.com/politicians/).

**State file:** `paper_results/politician_tracked.csv` (dedup log only — not position state)

---

## 9. Risk Guardrails

Every order passes through `alpaca_client.place_market_order()` before hitting the API. Two hard checks run regardless of which strategy places the order:

1. **Position size cap:** Order cost estimate must not exceed `MAX_POSITION_SIZE_USD` ($5,000). Raises `ValueError` if exceeded.
2. **Account risk cap:** Order cost must not exceed `MAX_ACCOUNT_RISK_PCT` (10%) of current account equity. Raises `ValueError` if exceeded.

These are constants in `config.py`, not `.env` settings. They cannot be overridden by environment variables or runtime arguments. Change them only by editing the source file.

---

## 10. Backtesting

```bash
python main.py backtest --symbol TSLA --days 365 --strategy trailing_stop
```

`--strategy` defaults to `trailing_stop` if omitted. Any registered strategy that implements a `backtest(df)` function can be backtested this way.

Pulls `days` of daily OHLCV data from Alpaca's IEX feed, passes the dataframe to `strategy.backtest(df)`, and prints:

- Total return %
- Max drawdown %
- Win rate %
- Number of trades (exits)

**Which strategies support backtesting?**

| Strategy | Backtestable | Reason |
|---|---|---|
| `trailing_stop` | Yes | Deterministic exit logic on OHLCV data |
| `politician_copy` | No | Entry depends on real-time disclosure events — no historical dataset |

Strategies without a `backtest(df)` function raise `NotImplementedError` with a clear message.

**Adding backtest support to a new strategy:** implement `backtest(df)` in your strategy module. The function receives a pandas DataFrame (daily OHLCV) and must return `{total_return_pct, max_drawdown_pct, win_rate_pct, num_trades, trades}`. See the commented template in `strategies/example_strategy.py`.

**Data feed note:** The backtester uses Alpaca's IEX feed (`feed="iex"`), available on free paper accounts. SIP data requires a paid subscription. IEX is reliable for liquid large-caps (S&P 500, Nasdaq 100). For small-cap or low-volume tickers, IEX data can be incomplete or stale.

**Backtest limitations:**
- Single entry at the first close. No re-entry after a stop.
- No slippage or commission modeling.
- No intraday simulation — only daily close prices.

---

## 11. Email Notifications

The bot sends three types of emails when SMTP is configured:

| Trigger | Subject |
|---|---|
| Scheduler start, 9:30 AM | `Trading Bot — Morning Brief [date]` |
| Any buy order filled | `[BOT ACTION] BUY {symbol} — {strategy}` |
| Any sell order filled | `[BOT ACTION] SELL {symbol} — {strategy} ({reason})` |
| 3:55 PM EOD | `Trading Bot — EOD Summary [date]` |

All email is optional. Set `EMAIL_SMTP` and `EMAIL_TO` in `.env` to enable. If either is missing, the notifier skips silently and the bot continues normally.

---

## 12. Building a New Strategy

Copy the template and rename it:

```bash
cp strategies/example_strategy.py strategies/my_strategy.py
```

Open `strategies/my_strategy.py` and make three changes:

### Step 1 — Set the strategy name

```python
STRATEGY_NAME = "my_strategy"   # must match the key you add to REGISTRY
```

The state file name derives from this automatically:
```python
STATE_FILE = os.path.join(..., f"{STRATEGY_NAME}_state.json")
```

### Step 2 — Implement `enter_position()`

This runs once at entry — when you call `enter` or when a `queue` order executes at 9:31 AM.

Required steps:
1. Place the buy order via `alpaca_client.place_market_order(symbol, qty, "buy")`
2. Get the actual fill price via `alpaca_client.get_fill_price(order.id)`
3. Record the position in state. The `"strategy": strategy` key is required — it is how `check_and_manage()` filters to only its own positions.
4. Send a buy notification via `notifier.action()`

Add any strategy-specific fields to the state record. Examples:

```python
state[symbol] = {
    "entry_price": fill_price,
    "qty": qty,
    "strategy": strategy,           # REQUIRED
    "entered_at": datetime.now().isoformat(),
    "target_price": fill_price * 1.15,   # 15% profit target
    "stop_price": fill_price * 0.92,     # 8% hard stop
}
```

### Step 3 — Implement `check_and_manage()`

This runs every 5 minutes during market hours for every position tagged with your strategy name.

Required pattern:

```python
def check_and_manage():
    state = load_state()
    if not state:
        return

    for symbol, data in list(state.items()):

        # REQUIRED: skip positions owned by other strategies
        if data.get("strategy", "trailing_stop") != STRATEGY_NAME:
            continue

        price = alpaca_client.get_current_price(symbol)
        if price is None:
            continue

        # Your exit logic here
        sell_signal = ...

        if sell_signal:
            order = alpaca_client.place_market_order(symbol, data["qty"], "sell")
            notifier.action(...)
            del state[symbol]

    save_state(state)
```

Never skip the strategy filter. Without it, your strategy will read and potentially sell positions belonging to other strategies.

### Step 4 — Register it

Open `strategies/__init__.py` and add one line:

```python
from strategies import trailing_stop, my_strategy

REGISTRY = {
    "trailing_stop": trailing_stop,
    "my_strategy":   my_strategy,
}
```

That is the entire integration. The scheduler picks it up automatically. The CLI and menu expose it immediately.

### Use it

```bash
python main.py enter --symbol TSLA --qty 10 --strategy my_strategy
python main.py queue --symbol TSLA --qty 10 --strategy my_strategy
```

### Exit logic patterns

Three common patterns shown in the template comments:

**Fixed target and stop:**
```python
sell_signal = price >= data["target_price"] or price <= data["stop_price"]
```

**Time-based hold:**
```python
entered = datetime.fromisoformat(data["entered_at"])
days_held = (datetime.now() - entered).days
sell_signal = days_held >= data["hold_days"]
```

**Momentum indicator (example: RSI):**
```python
rsi = compute_rsi(symbol, period=3)   # implement separately
sell_signal = rsi < 40
```

---

## 13. Known Limitations

**Stop execution delay.** The trailing stop fires on the next 5-minute check. Gap-downs at open or fast intraday moves can blow through the floor before the bot wakes up. For live money, submit native stop orders to Alpaca on entry and update them as the floor ratchets.

**IEX data for small caps.** The backtester and price lookups use Alpaca's IEX feed, available on free paper accounts. IEX data for low-volume or small-cap tickers is often incomplete or delayed. Use liquid large-caps for reliable backtest results.

**Politician copy — no exit strategy.** The congressional disclosure copier places buys but has no automated sell logic. Positions must be closed manually.

**Single-position backtester.** The backtest simulates one buy at the first bar with no re-entry after exit. It does not model a portfolio, slippage, commissions, or intraday price action.

**Paper trading only.** `ALPACA_BASE_URL` defaults to `https://paper-api.alpaca.markets`. Change to `https://api.alpaca.markets` for live trading only after you understand the risks and have tested thoroughly.
