"""ATR Keltner Channel — mean reversion using ATR-based bands (20MA ± 2×ATR)."""
import pandas as pd
from .base import StrategyBase, SignalResult


class ATRBreakout(StrategyBase):
    name = 'ATR Keltner Channel'
    description = 'Buy below lower Keltner band, sell above upper (20MA ± 2×ATR14)'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))

        price = float(df['Close'].iloc[-1])
        ma = df['Close'].rolling(20).mean()

        hl = df['High'] - df['Low']
        hc = (df['High'] - df['Close'].shift()).abs()
        lc = (df['Low'] - df['Close'].shift()).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        upper = ma + 2 * atr
        lower = ma - 2 * atr
        curr_upper = float(upper.iloc[-1])
        curr_lower = float(lower.iloc[-1])
        curr_atr = float(atr.iloc[-1])

        if price < curr_lower:
            return self._result(symbol, 'BUY', price, curr_atr,
                                f'Below Keltner lower ${curr_lower:.2f}')
        if price > curr_upper:
            return self._result(symbol, 'SELL', price, curr_atr,
                                f'Above Keltner upper ${curr_upper:.2f}')
        return self._result(symbol, 'HOLD', price, curr_atr,
                            f'Keltner [{curr_lower:.2f}–{curr_upper:.2f}]')
