"""MA Crossover — 50/200 SMA golden cross / death cross."""
import pandas as pd
from .base import StrategyBase, SignalResult


class MACrossover(StrategyBase):
    name = 'MA Crossover 50/200'
    description = 'Golden cross buy, death cross sell'
    min_periods = 210

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        closes = df['Close']
        price = float(closes.iloc[-1])
        ma50 = closes.rolling(50).mean()
        ma200 = closes.rolling(200).mean()

        prev_diff = float(ma50.iloc[-2]) - float(ma200.iloc[-2])
        curr_diff = float(ma50.iloc[-1]) - float(ma200.iloc[-1])

        if prev_diff < 0 and curr_diff > 0:
            return self._result(symbol, 'BUY', price, curr_diff,
                                '50MA crossed above 200MA (golden cross)')
        if prev_diff > 0 and curr_diff < 0:
            return self._result(symbol, 'SELL', price, curr_diff,
                                '50MA crossed below 200MA (death cross)')
        return self._result(symbol, 'HOLD', price, curr_diff,
                            f'50MA {"above" if curr_diff > 0 else "below"} 200MA')
