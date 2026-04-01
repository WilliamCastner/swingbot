"""EMA Crossover (5/13) — faster EMAs for quicker crypto signals."""
import pandas as pd
from bot.strategies.base import StrategyBase, SignalResult


class CryptoEMA(StrategyBase):
    name = 'EMA Crossover 5/13'
    description = '5 EMA crosses above/below 13 EMA'
    min_periods = 20

    def compute_signal(self, df: pd.DataFrame, symbol: str) -> SignalResult:
        if len(df) < self.min_periods:
            return self._insufficient(symbol, float(df['Close'].iloc[-1]))
        closes = df['Close']
        price = float(closes.iloc[-1])
        ema5  = closes.ewm(span=5,  adjust=False).mean()
        ema13 = closes.ewm(span=13, adjust=False).mean()
        prev_diff = float(ema5.iloc[-2]) - float(ema13.iloc[-2])
        curr_diff = float(ema5.iloc[-1]) - float(ema13.iloc[-1])
        if prev_diff < 0 and curr_diff > 0:
            return self._result(symbol, 'BUY', price, curr_diff, '5EMA crossed above 13EMA')
        if prev_diff > 0 and curr_diff < 0:
            return self._result(symbol, 'SELL', price, curr_diff, '5EMA crossed below 13EMA')
        return self._result(symbol, 'HOLD', price, curr_diff,
                            f'5EMA {">" if curr_diff > 0 else "<"} 13EMA')
