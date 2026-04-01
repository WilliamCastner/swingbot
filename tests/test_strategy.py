"""
test_strategy.py — Backtesting harness
Uses vectorbt to backtest the mean reversion strategy across
SPY, QQQ, IWM over historical data.

Run with: python tests/test_strategy.py

Key metrics to look for before going live:
  - Sharpe ratio > 1.0
  - Max drawdown < 20%
  - Win rate > 50%
  - Total return > buy-and-hold over same period (on risk-adjusted basis)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import vectorbt as vbt

from bot.data import get_daily_bars, WATCHLIST
from bot.strategy import compute_rsi


def run_backtest(symbol: str, start: str = '2020-01-01',
                 end: str = '2024-12-31',
                 rsi_period: int = 14,
                 ma_period: int = 20,
                 rsi_oversold: float = 35,
                 rsi_overbought: float = 60,
                 initial_cash: float = 500.0):

    print(f"\nBacktesting {symbol} | {start} to {end}")
    print(f"Params: RSI({rsi_period}) oversold={rsi_oversold} "
          f"overbought={rsi_overbought} | MA({ma_period})")

    # Fetch data
    df = vbt.YFData.download(symbol, start=start, end=end).get('Close')
    if df is None or df.empty:
        print(f"No data for {symbol}")
        return

    closes = df

    # Compute indicators
    rsi = compute_rsi(closes, rsi_period)
    ma = closes.rolling(ma_period).mean()
    price_vs_ma = (closes - ma) / ma

    # Entry: RSI < oversold AND price within 3% of MA
    entries = (rsi < rsi_oversold) & (price_vs_ma > -0.03)

    # Exit: RSI > overbought
    exits = rsi > rsi_overbought

    # Run vectorbt portfolio simulation
    portfolio = vbt.Portfolio.from_signals(
        closes,
        entries=entries,
        exits=exits,
        init_cash=initial_cash,
        fees=0.0,           # Alpaca is commission-free
        slippage=0.001,     # 0.1% slippage estimate
        freq='D',
    )

    # Print results
    stats = portfolio.stats()
    print(f"\nResults:")
    print(f"  Total return:      {stats['Total Return [%]']:.1f}%")
    print(f"  Sharpe ratio:      {stats['Sharpe Ratio']:.2f}")
    print(f"  Max drawdown:      {stats['Max Drawdown [%]']:.1f}%")
    print(f"  Win rate:          {stats['Win Rate [%]']:.1f}%")
    print(f"  Total trades:      {stats['Total Trades']:.0f}")
    print(f"  Avg trade duration:{stats['Avg Winning Trade Duration']}")

    # Buy-and-hold comparison
    bh_return = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
    print(f"\n  Buy-and-hold:      {bh_return:.1f}%")
    alpha = stats['Total Return [%]'] - bh_return
    print(f"  Alpha vs B&H:      {alpha:+.1f}%")

    return portfolio, stats


def optimize_rsi_thresholds(symbol: str = 'SPY',
                             start: str = '2020-01-01',
                             end: str = '2023-12-31'):
    """
    Grid search over RSI oversold/overbought thresholds.
    Use this to find the best params, then validate on out-of-sample data.
    WARNING: do not fit and test on the same data period.
    """
    print(f"\nOptimizing RSI thresholds for {symbol} (in-sample: {start}-{end})")

    df = vbt.YFData.download(symbol, start=start, end=end).get('Close')
    closes = df

    # Parameter grid
    oversold_range = np.arange(25, 45, 5)     # [25, 30, 35, 40]
    overbought_range = np.arange(55, 75, 5)   # [55, 60, 65, 70]

    best_sharpe = -999
    best_params = {}

    for oversold in oversold_range:
        for overbought in overbought_range:
            if oversold >= overbought:
                continue
            rsi = compute_rsi(closes, 14)
            ma = closes.rolling(20).mean()
            entries = (rsi < oversold) & ((closes - ma) / ma > -0.03)
            exits = rsi > overbought

            try:
                pf = vbt.Portfolio.from_signals(
                    closes, entries=entries, exits=exits,
                    init_cash=500, fees=0.0, slippage=0.001, freq='D'
                )
                sharpe = pf.stats()['Sharpe Ratio']
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = {'oversold': oversold, 'overbought': overbought}
            except Exception:
                continue

    print(f"Best params: {best_params} | Sharpe: {best_sharpe:.2f}")
    print("IMPORTANT: validate these on OUT-OF-SAMPLE data before using live.")
    return best_params


if __name__ == '__main__':
    print("=" * 60)
    print("SwingBot Backtest — Mean Reversion on ETFs")
    print("=" * 60)

    results = {}
    for symbol in WATCHLIST:
        pf, stats = run_backtest(
            symbol,
            start='2019-01-01',
            end='2024-12-31',
            initial_cash=500.0
        )
        results[symbol] = stats

    print("\n" + "=" * 60)
    print("Summary across watchlist:")
    for sym, stats in results.items():
        print(f"  {sym}: {stats['Total Return [%]']:.1f}% return | "
              f"Sharpe {stats['Sharpe Ratio']:.2f} | "
              f"Max DD {stats['Max Drawdown [%]']:.1f}%")
