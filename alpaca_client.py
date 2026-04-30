"""
Alpaca API wrapper. All trade execution and market data goes through here.
Uses alpaca-trade-api for paper trading and historical data pulls.
"""

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame
from datetime import datetime, timedelta
import pandas as pd
import config


def get_client():
    return tradeapi.REST(
        config.ALPACA_API_KEY,
        config.ALPACA_SECRET_KEY,
        config.ALPACA_BASE_URL,
        api_version="v2",
    )


def get_account():
    api = get_client()
    return api.get_account()


def get_position(symbol):
    api = get_client()
    try:
        return api.get_position(symbol)
    except Exception:
        return None


def get_all_positions():
    api = get_client()
    return api.list_positions()


def get_current_price(symbol):
    api = get_client()
    df = api.get_bars(symbol, TimeFrame.Minute, limit=1).df
    return float(df["close"].iloc[-1]) if not df.empty else None


def place_market_order(symbol, qty, side):
    """side: 'buy' or 'sell'"""
    api = get_client()
    account = api.get_account()
    equity = float(account.equity)

    cost_estimate = qty * (get_current_price(symbol) or 0)
    if cost_estimate > config.MAX_POSITION_SIZE_USD:
        raise ValueError(
            f"Order size ${cost_estimate:.2f} exceeds MAX_POSITION_SIZE_USD "
            f"${config.MAX_POSITION_SIZE_USD}"
        )
    if cost_estimate / equity > config.MAX_ACCOUNT_RISK_PCT:
        raise ValueError(
            f"Order is {cost_estimate/equity:.1%} of account — exceeds "
            f"MAX_ACCOUNT_RISK_PCT {config.MAX_ACCOUNT_RISK_PCT:.1%}"
        )

    order = api.submit_order(
        symbol=symbol,
        qty=qty,
        side=side,
        type="market",
        time_in_force="day",
    )
    return order


def get_historical_bars(symbol, days=365, timeframe=TimeFrame.Day):
    """Pull historical OHLCV for backtesting."""
    api = get_client()
    end = datetime.now()
    start = end - timedelta(days=days)
    bars = api.get_bars(
        symbol,
        timeframe,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        adjustment="raw",
    ).df
    return bars
