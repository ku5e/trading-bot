"""
Backtester — runs any strategy's rules against Alpaca historical data.
No LLM involved. Pure pandas simulation.

Usage:
    python backtest.py --symbol TSLA --days 365 --strategy trailing_stop
"""

import argparse
import pandas as pd
import alpaca_client
import config


def backtest_trailing_stop(df, drop_pct=None, raise_trigger=None, floor_offset=None):
    """
    Simulate trailing stop on OHLCV dataframe (daily bars).
    Assumes buy at first close, then manage from there.
    Returns metrics dict.
    """
    drop_pct = drop_pct or config.TRAILING_STOP_DROP_PCT
    raise_trigger = raise_trigger or config.TRAILING_STOP_RAISE_TRIGGER
    floor_offset = floor_offset or config.TRAILING_STOP_FLOOR_OFFSET

    entry_price = df["close"].iloc[0]
    floor = entry_price * (1 - drop_pct)
    peak = entry_price
    position = True
    trades = []
    equity_curve = [1.0]  # normalized to 1.0 at start

    for i, row in df.iterrows():
        if not position:
            equity_curve.append(equity_curve[-1])
            continue

        price = row["close"]

        if price > peak:
            peak = price
            gain_pct = (price - entry_price) / entry_price
            if gain_pct >= raise_trigger:
                new_floor = price * (1 - floor_offset)
                if new_floor > floor:
                    floor = new_floor

        if price <= floor:
            pnl_pct = (price - entry_price) / entry_price
            trades.append({"exit_price": price, "pnl_pct": pnl_pct, "exit_date": str(i)})
            position = False
            equity_curve.append(equity_curve[-1] * (1 + pnl_pct))
        else:
            equity_curve.append(equity_curve[-1] * (price / df["close"].iloc[max(0, df.index.get_loc(i) - 1)]))

    # Final close if still in position
    if position:
        final_price = df["close"].iloc[-1]
        pnl_pct = (final_price - entry_price) / entry_price
        trades.append({"exit_price": final_price, "pnl_pct": pnl_pct, "exit_date": "open"})

    total_return = equity_curve[-1] - 1.0
    max_drawdown = min(
        (v - max(equity_curve[: i + 1])) / max(equity_curve[: i + 1])
        for i, v in enumerate(equity_curve)
        if max(equity_curve[: i + 1]) > 0
    )
    win_rate = sum(1 for t in trades if t["pnl_pct"] > 0) / len(trades) if trades else 0

    return {
        "total_return_pct": round(total_return * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "win_rate_pct": round(win_rate * 100, 2),
        "num_trades": len(trades),
        "trades": trades,
    }


def run(symbol, days, strategy):
    print(f"Fetching {days}d of data for {symbol}...")
    df = alpaca_client.get_historical_bars(symbol, days=days)

    if strategy == "trailing_stop":
        results = backtest_trailing_stop(df)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    print(f"\n--- Backtest: {symbol} {strategy} ({days}d) ---")
    print(f"Total return:  {results['total_return_pct']}%")
    print(f"Max drawdown:  {results['max_drawdown_pct']}%")
    print(f"Win rate:      {results['win_rate_pct']}%")
    print(f"Trades:        {results['num_trades']}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--strategy", default="trailing_stop")
    args = parser.parse_args()
    run(args.symbol, args.days, args.strategy)
