"""Bollinger Bands (20, 2.5σ) — wider bands suited for crypto volatility."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoBollinger(StrategyBase):
    name = 'Bollinger Bands 2.5x'
    description = 'Buy below lower band, sell above upper band (20-period, 2.5 std)'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        closes = df['Close']
        price = float(closes.iloc[-1])
        ma  = closes.rolling(20).mean()
        std = closes.rolling(20).std()
        upper = ma + 2.5 * std
        lower = ma - 2.5 * std
        cu, cl = float(upper.iloc[-1]), float(lower.iloc[-1])
        pct_b = (price - cl) / (cu - cl) if (cu - cl) > 0 else 0.5
        if price < cl:
            return self._result(symbol, 'BUY', price, pct_b, f'Below lower BB ${cl:.4f}')
        if price > cu:
            return self._result(symbol, 'SELL', price, pct_b, f'Above upper BB ${cu:.4f}')
        return self._result(symbol, 'HOLD', price, pct_b, f'BB [{cl:.4f}–{cu:.4f}]')
