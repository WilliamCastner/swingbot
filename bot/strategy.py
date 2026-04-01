"""
strategy.py — Mean reversion swing strategy
Signal logic:
  BUY  — RSI(14) < 35 AND price within 3% above 20-day MA (oversold dip)
  SELL — RSI(14) > 60 (momentum recovered)
  HOLD — everything else

Designed for liquid ETFs (SPY, QQQ, IWM) held 2-5 days.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Literal

Signal = Literal['BUY', 'SELL', 'HOLD']


@dataclass
class StrategyResult:
    symbol: str
    signal: Signal
    rsi: float
    price: float
    ma20: float
    price_vs_ma_pct: float   # how far price is from MA (negative = below)
    reason: str


def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_signals(df: pd.DataFrame, symbol: str,
                    rsi_period: int = 14,
                    ma_period: int = 20,
                    rsi_oversold: float = 40,
                    rsi_overbought: float = 70,
                    ma_tolerance: float = 0.06) -> StrategyResult:
    """
    Compute the current signal for a symbol given its OHLCV DataFrame.

    Parameters
    ----------
    df            : DataFrame with at least 'Close' column, daily bars
    symbol        : ticker string
    rsi_period    : RSI lookback (default 14)
    ma_period     : moving average period (default 20)
    rsi_oversold  : RSI threshold to trigger BUY (default 35)
    rsi_overbought: RSI threshold to trigger SELL (default 60)
    ma_tolerance  : how far below MA is still acceptable for BUY (default 3%)
    """
    if len(df) < max(rsi_period, ma_period) + 5:
        return StrategyResult(symbol, 'HOLD', 50.0,
                              float(df['Close'].iloc[-1]), 0.0, 0.0,
                              'Insufficient data')

    closes = df['Close']
    rsi = compute_rsi(closes, rsi_period)
    ma = closes.rolling(ma_period).mean()

    latest_rsi = float(rsi.iloc[-1])
    latest_price = float(closes.iloc[-1])
    latest_ma = float(ma.iloc[-1])
    price_vs_ma = (latest_price - latest_ma) / latest_ma

    # BUY: oversold AND price hasn't fallen catastrophically below MA
    # (price above MA * 0.97 means within 3% — avoids catching falling knives)
    if latest_rsi < rsi_oversold and price_vs_ma > -ma_tolerance:
        return StrategyResult(
            symbol=symbol, signal='BUY',
            rsi=round(latest_rsi, 2), price=round(latest_price, 2),
            ma20=round(latest_ma, 2),
            price_vs_ma_pct=round(price_vs_ma * 100, 2),
            reason=f'RSI={latest_rsi:.1f} < {rsi_oversold}, price near MA'
        )

    # SELL: RSI has recovered — take profit
    if latest_rsi > rsi_overbought:
        return StrategyResult(
            symbol=symbol, signal='SELL',
            rsi=round(latest_rsi, 2), price=round(latest_price, 2),
            ma20=round(latest_ma, 2),
            price_vs_ma_pct=round(price_vs_ma * 100, 2),
            reason=f'RSI={latest_rsi:.1f} > {rsi_overbought}, momentum recovered'
        )

    return StrategyResult(
        symbol=symbol, signal='HOLD',
        rsi=round(latest_rsi, 2), price=round(latest_price, 2),
        ma20=round(latest_ma, 2),
        price_vs_ma_pct=round(price_vs_ma * 100, 2),
        reason='No signal'
    )
