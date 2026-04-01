"""RSI + Volume Spike — crypto pumps are volume-driven, require confirmation."""
import numpy as np
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoRSIVolume(StrategyBase):
    name = 'RSI + Volume Spike'
    description = 'RSI(7)<35 confirmed by 2x average volume'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        closes = df['Close']
        price  = float(closes.iloc[-1])
        delta  = closes.diff()
        gain   = delta.clip(lower=0).rolling(7).mean()
        loss   = -delta.clip(upper=0).rolling(7).mean()
        rsi    = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        r      = float(rsi.iloc[-1])
        vol    = float(df['Volume'].iloc[-1])
        avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1])
        ratio  = vol / avg_vol if avg_vol > 0 else 1.0
        if r < 35 and ratio >= 2.0:
            return self._result(symbol, 'BUY', price, r,
                                f'RSI(7)={r:.1f}<35 + vol={ratio:.1f}x')
        if r > 65:
            return self._result(symbol, 'SELL', price, r, f'RSI(7)={r:.1f}>65')
        return self._result(symbol, 'HOLD', price, r,
                            f'RSI(7)={r:.1f}, vol={ratio:.1f}x')
