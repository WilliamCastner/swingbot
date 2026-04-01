"""RSI Mean Reversion — buy oversold dips near the moving average."""
import numpy as np
import pandas as pd
from .base import StrategyBase, SignalResult


class RSIMeanReversion(StrategyBase):
    name = 'RSI Mean Reversion'
    description = 'Buy RSI<40 within 6% of 20MA, sell RSI>70'
    min_periods = 30

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        closes = df['Close']
        price = float(closes.iloc[-1])

        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        current_rsi = float(rsi.iloc[-1])

        ma20 = float(closes.rolling(20).mean().iloc[-1])
        price_vs_ma = (price - ma20) / ma20

        if current_rsi < 40 and price_vs_ma > -0.06:
            return self._result(symbol, 'BUY', price, current_rsi,
                                f'RSI={current_rsi:.1f}<40, near MA')
        if current_rsi > 70:
            return self._result(symbol, 'SELL', price, current_rsi,
                                f'RSI={current_rsi:.1f}>70')
        return self._result(symbol, 'HOLD', price, current_rsi, 'No signal')
