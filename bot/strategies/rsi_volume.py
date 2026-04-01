"""RSI + Volume — oversold RSI confirmed by a volume spike."""
import numpy as np
import pandas as pd
from .base import StrategyBase, SignalResult


class RSIVolume(StrategyBase):
    name = 'RSI + Volume'
    description = 'RSI<40 confirmed by 1.5x average volume spike'
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

        current_vol = float(df['Volume'].iloc[-1])
        avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1])
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0

        if current_rsi < 40 and vol_ratio >= 1.5:
            return self._result(symbol, 'BUY', price, current_rsi,
                                f'RSI={current_rsi:.1f}<40, vol={vol_ratio:.1f}x avg')
        if current_rsi > 65:
            return self._result(symbol, 'SELL', price, current_rsi,
                                f'RSI={current_rsi:.1f}>65')
        return self._result(symbol, 'HOLD', price, current_rsi,
                            f'RSI={current_rsi:.1f}, vol={vol_ratio:.1f}x')
