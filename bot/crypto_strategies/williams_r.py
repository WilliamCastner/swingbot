"""Williams %R — momentum oscillator popular in crypto trading."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoWilliamsR(StrategyBase):
    name = 'Williams %R'
    description = '%R<-80 oversold buy, %R>-20 overbought sell (14-period)'
    min_periods = 20

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        price  = float(df['Close'].iloc[-1])
        high14 = df['High'].rolling(14).max()
        low14  = df['Low'].rolling(14).min()
        denom  = (high14 - low14).replace(0, float('nan'))
        wr     = -100 * (high14 - df['Close']) / denom
        w = float(wr.iloc[-1])
        if w < -80:
            return self._result(symbol, 'BUY', price, w, f'%R={w:.1f} oversold')
        if w > -20:
            return self._result(symbol, 'SELL', price, w, f'%R={w:.1f} overbought')
        return self._result(symbol, 'HOLD', price, w, f'%R={w:.1f}')
