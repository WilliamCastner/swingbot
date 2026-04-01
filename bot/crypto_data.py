"""
crypto_data.py — Crypto market data via yfinance.
Uses yfinance symbols (SOL-USD) internally; maps to Alpaca symbols (SOLUSD) for orders.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# yfinance format → Alpaca format
CRYPTO_MAP = {
    'SOL-USD':  'SOLUSD',
    'ETH-USD':  'ETHUSD',
    'DOGE-USD': 'DOGEUSD',
    'AVAX-USD': 'AVAXUSD',
}

CRYPTO_WATCHLIST = list(CRYPTO_MAP.keys())    # yfinance symbols for data
CRYPTO_ALPACA    = list(CRYPTO_MAP.values())  # Alpaca symbols for orders

def yf_to_alpaca(symbol: str) -> str:
    return CRYPTO_MAP.get(symbol, symbol.replace('-', ''))

def alpaca_to_yf(symbol: str) -> str:
    reverse = {v: k for k, v in CRYPTO_MAP.items()}
    return reverse.get(symbol, symbol)


def get_crypto_bars(symbol: str, days: int = 60) -> pd.DataFrame:
    """Fetch daily OHLCV bars for a crypto symbol (yfinance format, e.g. 'SOL-USD')."""
    df = yf.download(symbol, period=f'{days}d', interval='1d',
                     auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f'No data for {symbol}')
    df.index = pd.to_datetime(df.index)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()


def get_crypto_watchlist_data(days: int = 60) -> dict[str, pd.DataFrame]:
    data = {}
    for symbol in CRYPTO_WATCHLIST:
        try:
            data[symbol] = get_crypto_bars(symbol, days=days)
        except Exception as e:
            print(f'Warning: could not fetch {symbol}: {e}')
    return data
