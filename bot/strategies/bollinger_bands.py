"""Bollinger Bands — buy at lower band, sell at upper band (20-period, 2σ)."""
import pandas as pd
from .base import StrategyBase, SignalResult


class BollingerBands(StrategyBase):
    name = 'Bollinger Bands'
    description = 'Buy below lower band, sell above upper band (20, 2σ)'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        closes = df['Close']
        price = float(closes.iloc[-1])
        ma = closes.rolling(20).mean()
        std = closes.rolling(20).std()
        upper = ma + 2 * std
        lower = ma - 2 * std

        curr_upper = float(upper.iloc[-1])
        curr_lower = float(lower.iloc[-1])
        band_width = curr_upper - curr_lower
        pct_b = (price - curr_lower) / band_width if band_width > 0 else 0.5

        if price < curr_lower:
            return self._result(symbol, 'BUY', price, pct_b,
                                f'Below lower BB ${curr_lower:.2f}')
        if price > curr_upper:
            return self._result(symbol, 'SELL', price, pct_b,
                                f'Above upper BB ${curr_upper:.2f}')
        return self._result(symbol, 'HOLD', price, pct_b,
                            f'BB [{curr_lower:.2f}–{curr_upper:.2f}]')
