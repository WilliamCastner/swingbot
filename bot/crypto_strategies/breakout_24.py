"""24-Bar Breakout — momentum entry on new highs, exit on new lows."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class Breakout24(StrategyBase):
    name = '24-Bar Breakout'
    description = 'Buy on 24-bar high break, sell on 24-bar low break'
    min_periods = 28

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        price = float(df['Close'].iloc[-1])
        high_24 = float(df['High'].iloc[-25:-1].max())
        low_24  = float(df['Low'].iloc[-25:-1].min())
        if price > high_24:
            return self._result(symbol, 'BUY', price, high_24,
                                f'Broke 24-bar high ${high_24:.4f}')
        if price < low_24:
            return self._result(symbol, 'SELL', price, low_24,
                                f'Broke 24-bar low ${low_24:.4f}')
        return self._result(symbol, 'HOLD', price, high_24,
                            f'Range ${low_24:.4f}–${high_24:.4f}')
