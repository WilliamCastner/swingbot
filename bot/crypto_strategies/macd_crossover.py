"""MACD Crossover (12/26/9) — trend following via MACD histogram flip."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoMACD(StrategyBase):
    name = 'MACD Crossover'
    description = 'MACD line crosses signal line (12/26/9)'
    min_periods = 35

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        closes = df['Close']
        price = float(closes.iloc[-1])
        macd   = closes.ewm(span=12, adjust=False).mean() - closes.ewm(span=26, adjust=False).mean()
        signal = macd.ewm(span=9, adjust=False).mean()
        hist   = macd - signal
        prev, curr = float(hist.iloc[-2]), float(hist.iloc[-1])
        m = float(macd.iloc[-1])
        if prev < 0 and curr > 0:
            return self._result(symbol, 'BUY', price, m, f'MACD crossed above signal')
        if prev > 0 and curr < 0:
            return self._result(symbol, 'SELL', price, m, f'MACD crossed below signal')
        return self._result(symbol, 'HOLD', price, m, f'MACD hist={curr:.6f}')
