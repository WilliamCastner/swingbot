"""Williams %R — momentum oscillator, %R<-80 oversold, %>-20 overbought."""
import pandas as pd
from .base import StrategyBase, SignalResult


class WilliamsR(StrategyBase):
    name = 'Williams %R'
    description = '%R<-80 oversold buy, %R>-20 overbought sell (14-period)'
    min_periods = 20

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        price = float(df['Close'].iloc[-1])
        high14 = df['High'].rolling(14).max()
        low14 = df['Low'].rolling(14).min()
        denom = (high14 - low14).replace(0, float('nan'))
        wr = -100 * (high14 - df['Close']) / denom
        current_wr = float(wr.iloc[-1])

        if current_wr < -80:
            return self._result(symbol, 'BUY', price, current_wr,
                                f'%R={current_wr:.1f} oversold (<-80)')
        if current_wr > -20:
            return self._result(symbol, 'SELL', price, current_wr,
                                f'%R={current_wr:.1f} overbought (>-20)')
        return self._result(symbol, 'HOLD', price, current_wr,
                            f'%R={current_wr:.1f}')
