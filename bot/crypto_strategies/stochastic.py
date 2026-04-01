"""Stochastic Oscillator (14/3) — oversold/overbought crypto bounces."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoStochastic(StrategyBase):
    name = 'Stochastic Oscillator'
    description = '%K<20 oversold buy, %K>80 overbought sell'
    min_periods = 20

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        price  = float(df['Close'].iloc[-1])
        low14  = df['Low'].rolling(14).min()
        high14 = df['High'].rolling(14).max()
        denom  = (high14 - low14).replace(0, float('nan'))
        pct_k  = 100 * (df['Close'] - low14) / denom
        k = float(pct_k.iloc[-1])
        d = float(pct_k.rolling(3).mean().iloc[-1])
        if k < 20:
            return self._result(symbol, 'BUY', price, k, f'%K={k:.1f} oversold')
        if k > 80:
            return self._result(symbol, 'SELL', price, k, f'%K={k:.1f} overbought')
        return self._result(symbol, 'HOLD', price, k, f'%K={k:.1f}, %D={d:.1f}')
