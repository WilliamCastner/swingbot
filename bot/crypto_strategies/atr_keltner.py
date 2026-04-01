"""ATR Keltner Channel (20MA ± 2.5×ATR) — wider channel for crypto swings."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoATR(StrategyBase):
    name = 'ATR Keltner 2.5x'
    description = 'Buy below lower Keltner band, sell above upper (20MA ± 2.5×ATR14)'
    min_periods = 25

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        price = float(df['Close'].iloc[-1])
        ma  = df['Close'].rolling(20).mean()
        hl  = df['High'] - df['Low']
        hc  = (df['High'] - df['Close'].shift()).abs()
        lc  = (df['Low']  - df['Close'].shift()).abs()
        atr = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
        upper = ma + 2.5 * atr
        lower = ma - 2.5 * atr
        cu, cl, a = float(upper.iloc[-1]), float(lower.iloc[-1]), float(atr.iloc[-1])
        if price < cl:
            return self._result(symbol, 'BUY', price, a, f'Below Keltner lower ${cl:.4f}')
        if price > cu:
            return self._result(symbol, 'SELL', price, a, f'Above Keltner upper ${cu:.4f}')
        return self._result(symbol, 'HOLD', price, a, f'Keltner [{cl:.4f}–{cu:.4f}]')
