"""20-Day Breakout — buy on break above 20-day high, sell below 20-day low."""
import pandas as pd
from .base import StrategyBase, SignalResult


class Breakout(StrategyBase):
    name = '20-Day Breakout'
    description = 'Buy on 20-day high break, sell on 20-day low break'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        price = float(df['Close'].iloc[-1])
        high_20 = float(df['High'].iloc[-21:-1].max())
        low_20 = float(df['Low'].iloc[-21:-1].min())

        if price > high_20:
            return self._result(symbol, 'BUY', price, high_20,
                                f'Broke above 20-day high ${high_20:.2f}')
        if price < low_20:
            return self._result(symbol, 'SELL', price, low_20,
                                f'Broke below 20-day low ${low_20:.2f}')
        return self._result(symbol, 'HOLD', price, high_20,
                            f'Range ${low_20:.2f}–${high_20:.2f}')
