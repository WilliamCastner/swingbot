"""MACD Crossover — MACD line crosses signal line (12/26/9)."""
import pandas as pd
from .base import StrategyBase, SignalResult


class MACDCrossover(StrategyBase):
    name = 'MACD Crossover'
    description = 'MACD line crosses signal line (12/26/9)'
    min_periods = 35

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        closes = df['Close']
        price = float(closes.iloc[-1])
        macd = closes.ewm(span=12, adjust=False).mean() - closes.ewm(span=26, adjust=False).mean()
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        prev_hist = float(hist.iloc[-2])
        curr_hist = float(hist.iloc[-1])
        curr_macd = float(macd.iloc[-1])

        if prev_hist < 0 and curr_hist > 0:
            return self._result(symbol, 'BUY', price, curr_macd,
                                f'MACD crossed above signal (hist={curr_hist:.4f})')
        if prev_hist > 0 and curr_hist < 0:
            return self._result(symbol, 'SELL', price, curr_macd,
                                f'MACD crossed below signal (hist={curr_hist:.4f})')
        return self._result(symbol, 'HOLD', price, curr_macd,
                            f'MACD hist={curr_hist:.4f}')
