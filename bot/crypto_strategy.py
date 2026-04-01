"""
crypto_strategy.py — Aggressive crypto strategy.
Uses fast RSI(7) for mean reversion + 24-bar high breakout for momentum.
Runs on daily bars, executed every 4 hours to catch signals quickly.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Literal

Signal = Literal['BUY', 'SELL', 'HOLD']


@dataclass
class CryptoSignal:
    symbol: str          # yfinance format (SOL-USD)
    alpaca_symbol: str   # Alpaca format (SOLUSD)
    signal: Signal
    price: float
    rsi: float
    reason: str


def compute_rsi(closes: pd.Series, period: int = 7) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_crypto_signal(df: pd.DataFrame, symbol: str,
                          alpaca_symbol: str) -> CryptoSignal:
    def hold(reason):
        return CryptoSignal(symbol, alpaca_symbol, 'HOLD',
                            round(float(df['Close'].iloc[-1]), 6), 0.0, reason)

    if len(df) < 30:
        return hold('Insufficient data')

    closes = df['Close']
    price = float(closes.iloc[-1])
    rsi = compute_rsi(closes, period=7)
    current_rsi = float(rsi.iloc[-1])

    # 24-bar (day) high breakout — momentum entry
    high_24 = float(df['High'].iloc[-25:-1].max())

    # BUY: oversold OR momentum breakout
    if current_rsi < 35:
        return CryptoSignal(symbol, alpaca_symbol, 'BUY', round(price, 6),
                            round(current_rsi, 2),
                            f'RSI(7)={current_rsi:.1f} oversold')
    if price > high_24:
        return CryptoSignal(symbol, alpaca_symbol, 'BUY', round(price, 6),
                            round(current_rsi, 2),
                            f'Breakout above 24-bar high ${high_24:.4f}')

    # SELL: overbought
    if current_rsi > 65:
        return CryptoSignal(symbol, alpaca_symbol, 'SELL', round(price, 6),
                            round(current_rsi, 2),
                            f'RSI(7)={current_rsi:.1f} overbought')

    return CryptoSignal(symbol, alpaca_symbol, 'HOLD', round(price, 6),
                        round(current_rsi, 2), f'RSI(7)={current_rsi:.1f}')
