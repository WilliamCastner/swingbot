"""EMA Crossover — 9/21 EMA fast trend signal."""
import pandas as pd
from .base import StrategyBase, SignalResult


class EMACrossover(StrategyBase):
    name = 'EMA Crossover 9/21'
    description = '9 EMA crosses above/below 21 EMA'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        closes = df['Close']
        price = float(closes.iloc[-1])
        ema9 = closes.ewm(span=9, adjust=False).mean()
        ema21 = closes.ewm(span=21, adjust=False).mean()

        prev_diff = float(ema9.iloc[-2]) - float(ema21.iloc[-2])
        curr_diff = float(ema9.iloc[-1]) - float(ema21.iloc[-1])

        if prev_diff < 0 and curr_diff > 0:
            return self._result(symbol, 'BUY', price, curr_diff,
                                '9EMA crossed above 21EMA')
        if prev_diff > 0 and curr_diff < 0:
            return self._result(symbol, 'SELL', price, curr_diff,
                                '9EMA crossed below 21EMA')
        return self._result(symbol, 'HOLD', price, curr_diff,
                            f'9EMA {">" if curr_diff > 0 else "<"} 21EMA')
