"""RSI(7) Mean Reversion — fast RSI tuned for crypto volatility."""
import numpy as np
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoRSI(StrategyBase):
    name = 'RSI(7) Mean Reversion'
    description = 'Buy RSI(7)<35, sell RSI(7)>65'
    min_periods = 15

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        closes = df['Close']
        price = float(closes.iloc[-1])
        delta = closes.diff()
        gain = delta.clip(lower=0).rolling(7).mean()
        loss = -delta.clip(upper=0).rolling(7).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        r = float(rsi.iloc[-1])
        if r < 35:
            return self._result(symbol, 'BUY', price, r, f'RSI(7)={r:.1f}<35')
        if r > 65:
            return self._result(symbol, 'SELL', price, r, f'RSI(7)={r:.1f}>65')
        return self._result(symbol, 'HOLD', price, r, f'RSI(7)={r:.1f}')
