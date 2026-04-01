"""3-Day Momentum — buy accelerating uptrends, sell decelerating ones."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class Momentum3Day(StrategyBase):
    name = '3-Day Momentum'
    description = 'Buy when 3-day return > 0 and accelerating, sell when reversing'
    min_periods = 10

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        closes = df['Close']
        price  = float(closes.iloc[-1])

        ret3  = (closes.iloc[-1] - closes.iloc[-4]) / closes.iloc[-4]   # 3-day return
        ret3p = (closes.iloc[-2] - closes.iloc[-5]) / closes.iloc[-5]   # prev 3-day return
        mom   = float(ret3)
        accel = float(ret3 - ret3p)

        if mom > 0.02 and accel > 0:   # rising >2% and accelerating
            return self._result(symbol, 'BUY', price, mom,
                                f'3d momentum={mom:.2%}, accel={accel:.2%}')
        if mom < -0.02 or accel < -0.03:   # falling or sharply decelerating
            return self._result(symbol, 'SELL', price, mom,
                                f'3d momentum={mom:.2%}, accel={accel:.2%}')
        return self._result(symbol, 'HOLD', price, mom,
                            f'3d momentum={mom:.2%}')
