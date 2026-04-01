"""base.py — Shared types and base class for all strategies."""
from dataclasses import dataclass
from typing import Literal
import pandas as pd
import numpy as np

Signal = Literal['BUY', 'SELL', 'HOLD']


@dataclass
class SignalResult:
    symbol: str
    signal: Signal
    price: float
    indicator: float   # main indicator value for display
    reason: str


class StrategyBase:
    name: str = ''
    description: str = ''
    min_periods: int = 30

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        raise NotImplementedError

    def _insufficient(self, symbol: str, price: float) -> SignalResult:
        return SignalResult(symbol, 'HOLD', round(float(price), 2), 0.0, 'Insufficient data')

    def _result(self, symbol, signal, price, indicator, reason) -> SignalResult:
        return SignalResult(symbol, signal, round(float(price), 2),
                            round(float(indicator), 4), reason)
