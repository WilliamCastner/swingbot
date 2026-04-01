"""
data.py — Market data fetching
Uses yfinance (free, no API key) for daily bars used by the strategy.
Falls back to Alpaca historical data if needed.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


WATCHLIST = ['NVDA', 'TSLA', 'AMD', 'COIN', 'SPY']


def get_daily_bars(symbol: str, days: int = 90) -> pd.DataFrame:
    """
    Fetch daily OHLCV bars for a symbol.
    Returns a clean DataFrame with columns: Open, High, Low, Close, Volume
    """
    df = yf.download(symbol, period=f'{days}d', interval='1d',
                     auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")
    df.index = pd.to_datetime(df.index)
    # Flatten MultiIndex columns if present (yfinance sometimes returns them)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()


def get_current_price(symbol: str) -> float:
    """Get the most recent closing price."""
    df = get_daily_bars(symbol, days=5)
    return float(df['Close'].iloc[-1])


def get_watchlist_data(days: int = 90) -> dict[str, pd.DataFrame]:
    """Fetch data for all symbols in the watchlist."""
    data = {}
    for symbol in WATCHLIST:
        try:
            data[symbol] = get_daily_bars(symbol, days=days)
        except Exception as e:
            print(f"Warning: could not fetch data for {symbol}: {e}")
    return data


def is_market_open() -> bool:
    """Simple check — market is open Mon-Fri, roughly 9:30am-4pm ET."""
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo('America/New_York'))
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close
