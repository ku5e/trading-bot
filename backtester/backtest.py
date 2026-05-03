"""
Backtester — simulates any strategy's exit logic against Alpaca historical data.
No LLM involved. Pure pandas simulation.

Each strategy module may optionally implement backtest(df) -> dict.
Strategies that cannot be simulated (e.g. politician_copy) raise NotImplementedError.

Usage:
    python main.py backtest --symbol TSLA --days 365 --strategy trailing_stop
"""

import argparse
import alpaca_client


def run(symbol, days, strategy):
    from strategies import REGISTRY

    strat = REGISTRY.get(strategy)
    if strat is None:
        raise ValueError(
            f"Unknown strategy: {strategy!r}. Available: {list(REGISTRY.keys())}"
        )
    if not hasattr(strat, "backtest"):
        raise NotImplementedError(
            f"Strategy {strategy!r} does not support backtesting. "
            f"Add a backtest(df) function to strategies/{strategy}.py to enable it."
        )

    print(f"Fetching {days}d of data for {symbol}...")
    df = alpaca_client.get_historical_bars(symbol, days=days)

    results = strat.backtest(df)

    print(f"\n--- Backtest: {symbol} {strategy} ({days}d) ---")
    print(f"Total return:  {results['total_return_pct']}%")
    print(f"Max drawdown:  {results['max_drawdown_pct']}%")
    print(f"Win rate:      {results['win_rate_pct']}%")
    print(f"Trades:        {results['num_trades']}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol",   required=True)
    parser.add_argument("--days",     type=int, default=365)
    parser.add_argument("--strategy", default="trailing_stop")
    args = parser.parse_args()
    run(args.symbol.upper(), args.days, args.strategy)
