# Trading Bot

A paper trading bot wired to the Alpaca API. Runs multiple strategies on a scheduler during market hours. Fully extensible — new strategies are single Python files.

Built and maintained by [ku5e](https://ku5e.com).

---

## What It Does

- Executes buy orders manually (CLI or menu) or automatically (queue for next open)
- Runs registered strategies every 5 minutes during market hours (9:30–4:00 PM ET)
- Sends email alerts on every buy and sell
- Generates a morning brief and end-of-day summary
- Backtests any strategy against historical data

## Built-in Strategies

| Strategy | Entry | Exit |
|---|---|---|
| `trailing_stop` | Manual via CLI | Trailing floor — ratchets up as price rises, sells on drop |
| `politician_copy` | Automatic — scrapes Capitol Trades disclosures daily | Manual, or hand off to any strategy via `POLITICIAN_EXIT_STRATEGY` in config |

## Quick Start

```bash
git clone https://github.com/ku5e/trading-bot.git
cd trading-bot
pip install -r requirements.txt
cp .env.example .env
# fill in ALPACA_API_KEY and ALPACA_SECRET_KEY
```

Run the scheduler (keeps running during market hours):

```bash
python scheduler.py
```

Or use the interactive menu:

```bash
python menu.py
```

Or use the CLI directly:

```bash
python main.py status
python main.py enter --symbol TSLA --qty 10 --strategy trailing_stop
python main.py queue --symbol TSLA --qty 10 --strategy trailing_stop
python main.py backtest --symbol TSLA --days 365 --strategy trailing_stop
```

## CLI Commands

| Command | Example |
|---|---|
| `status` | `python main.py status` |
| `positions` | `python main.py positions` |
| `strategies` | `python main.py strategies` |
| `price` | `python main.py price --symbol TSLA` |
| `enter` | `python main.py enter --symbol TSLA --qty 10 --strategy trailing_stop` |
| `queue` | `python main.py queue --symbol TSLA --qty 10 --strategy trailing_stop` |
| `pending` | `python main.py pending` |
| `cancel` | `python main.py cancel --symbol TSLA` |
| `backtest` | `python main.py backtest --symbol TSLA --days 365 --strategy trailing_stop` |

## Adding a Strategy

Copy the template, rename it, implement two functions:

```bash
cp strategies/example_strategy.py strategies/my_strategy.py
```

1. Set `STRATEGY_NAME = "my_strategy"`
2. Implement `enter_position(symbol, qty, strategy)` — places buy, records state, sends notification
3. Implement `check_and_manage()` — runs every 5 min, applies exit logic, sells when triggered
4. Register in `strategies/__init__.py`:

```python
from strategies import trailing_stop, my_strategy

REGISTRY = {
    "trailing_stop": trailing_stop,
    "my_strategy":   my_strategy,
}
```

That's the full integration. Full documentation in [MANUAL.md](MANUAL.md).

## Configuration

All settings in `.env`. Risk guardrails (`MAX_POSITION_SIZE_USD`, `MAX_ACCOUNT_RISK_PCT`, stop percentages) are constants in `config.py` — not overridable at runtime.

Default: paper trading (`https://paper-api.alpaca.markets`). Change `ALPACA_BASE_URL` in `.env` only when ready for live money.

## Requirements

- Python 3.10+
- Alpaca paper trading account (free)
- Optional: Ollama (end-of-day summary), SMTP credentials (email alerts)

## License

MIT
