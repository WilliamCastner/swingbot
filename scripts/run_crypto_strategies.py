"""
run_crypto_strategies.py — Run all 10 crypto strategies as virtual simulations.
Each strategy gets a $100k virtual portfolio. No real orders placed.

Usage:
  py -3.11 scripts/run_crypto_strategies.py
  py -3.11 scripts/run_crypto_strategies.py --dry-run
"""

import sys
import os
import csv
import json
import argparse
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.crypto_data import get_crypto_watchlist_data, CRYPTO_WATCHLIST
from bot.crypto_strategies import ALL_CRYPTO_STRATEGIES

LOGS          = Path('logs/crypto_strategies')
STARTING_CASH = 100_000.0


class VirtualPortfolio:
    def __init__(self, starting_cash=STARTING_CASH, max_position_pct=0.95, max_positions=2):
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.positions: dict = {}
        self.peak_value = starting_cash
        self.max_position_pct = max_position_pct
        self.max_positions = max_positions

    def total_value(self, prices: dict) -> float:
        return self.cash + sum(
            pos['qty'] * prices.get(sym, pos['avg_price'])
            for sym, pos in self.positions.items()
        )

    def can_buy(self, symbol: str) -> bool:
        return symbol not in self.positions and len(self.positions) < self.max_positions

    def buy(self, symbol: str, price: float) -> float:
        if not self.can_buy(symbol) or price <= 0 or self.cash < 1:
            return 0.0
        dollars = self.cash * self.max_position_pct
        qty = dollars / price
        self.cash -= dollars
        self.positions[symbol] = {'qty': qty, 'avg_price': price}
        return qty

    def sell(self, symbol: str, price: float) -> tuple[float, float]:
        if symbol not in self.positions:
            return 0.0, 0.0
        pos = self.positions.pop(symbol)
        proceeds = pos['qty'] * price
        self.cash += proceeds
        return pos['qty'], proceeds - pos['qty'] * pos['avg_price']

    def to_dict(self):
        return {'cash': self.cash, 'starting_cash': self.starting_cash,
                'positions': self.positions, 'peak_value': self.peak_value}

    @classmethod
    def from_dict(cls, d):
        p = cls(starting_cash=d.get('starting_cash', STARTING_CASH))
        p.cash = d['cash']
        p.positions = d.get('positions', {})
        p.peak_value = d.get('peak_value', p.cash)
        return p


def load_portfolio(log_dir: Path) -> VirtualPortfolio:
    f = log_dir / 'portfolio.json'
    if f.exists():
        try:
            return VirtualPortfolio.from_dict(json.loads(f.read_text()))
        except Exception:
            pass
    return VirtualPortfolio()


def save_portfolio(p: VirtualPortfolio, log_dir: Path):
    (log_dir / 'portfolio.json').write_text(json.dumps(p.to_dict(), indent=2))


def log_trade(log_dir, symbol, side, qty, price, pnl, reason):
    f = log_dir / 'trades.csv'
    write_header = not f.exists()
    with open(f, 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['timestamp','symbol','side','qty','price','pnl','reason'])
        if write_header:
            w.writeheader()
        w.writerow({'timestamp': datetime.now().isoformat(), 'symbol': symbol,
                    'side': side, 'qty': round(qty, 8), 'price': round(price, 6),
                    'pnl': round(pnl, 2), 'reason': reason})


def log_pnl(log_dir, portfolio, prices):
    total = portfolio.total_value(prices)
    if total > portfolio.peak_value:
        portfolio.peak_value = total
    drawdown = (portfolio.peak_value - total) / portfolio.peak_value * 100 if portfolio.peak_value else 0
    pnl = total - portfolio.starting_cash
    f = log_dir / 'pnl.csv'
    write_header = not f.exists()
    with open(f, 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['date','portfolio_value','total_pnl','total_pnl_pct','drawdown_pct'])
        if write_header:
            w.writeheader()
        w.writerow({'date': date.today().isoformat(),
                    'portfolio_value': round(total, 2),
                    'total_pnl': round(pnl, 2),
                    'total_pnl_pct': round(pnl / portfolio.starting_cash * 100, 3),
                    'drawdown_pct': round(drawdown, 3)})
    return total


def run_strategy(strategy, market_data, dry_run=False):
    slug = (strategy.name.lower()
            .replace(' ', '_').replace('/', '_')
            .replace('(', '').replace(')', '').replace('.', ''))
    log_dir = LOGS / slug
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / 'name.txt').write_text(strategy.name)

    portfolio = load_portfolio(log_dir)
    prices = {sym: float(df['Close'].iloc[-1]) for sym, df in market_data.items()}
    signals = {sym: strategy.compute_signal(df, sym) for sym, df in market_data.items()}

    if not dry_run:
        for sym, result in signals.items():
            if result.signal == 'SELL' and sym in portfolio.positions:
                qty, pnl = portfolio.sell(sym, result.price)
                if qty > 0:
                    log_trade(log_dir, sym, 'SELL', qty, result.price, pnl, result.reason)
        for sym, result in signals.items():
            if result.signal == 'BUY' and portfolio.can_buy(sym):
                qty = portfolio.buy(sym, result.price)
                if qty > 0:
                    log_trade(log_dir, sym, 'BUY', qty, result.price, 0.0, result.reason)
        save_portfolio(portfolio, log_dir)

    total = log_pnl(log_dir, portfolio, prices)
    return signals, total, portfolio


def main(dry_run=False):
    print(f'\nCrypto Strategy Comparison - {date.today()}')
    print(f'Watchlist: {", ".join(CRYPTO_WATCHLIST)}')
    print(f'{"DRY RUN" if dry_run else "Live run"}\n')

    market_data = get_crypto_watchlist_data(days=90)

    results = []
    for strategy in ALL_CRYPTO_STRATEGIES:
        signals, total, portfolio = run_strategy(strategy, market_data, dry_run)
        pnl_pct = (total - portfolio.starting_cash) / portfolio.starting_cash * 100
        sign = '+' if pnl_pct >= 0 else ''
        buys  = [s.symbol for s in signals.values() if s.signal == 'BUY']
        sells = [s.symbol for s in signals.values() if s.signal == 'SELL']
        mode  = '[DRY]' if dry_run else '     '
        print(f'{mode} {strategy.name:<28} ${total:>10,.2f}  ({sign}{pnl_pct:.2f}%)  '
              f'BUY:{buys or "-"}  SELL:{sells or "-"}')
        results.append((strategy.name, total, pnl_pct))

    results.sort(key=lambda x: x[2], reverse=True)
    print(f'\n{"-" * 55}')
    print('Crypto Leaderboard:')
    for i, (name, val, pct) in enumerate(results, 1):
        sign = '+' if pct >= 0 else ''
        print(f'  {i:>2}. {name:<28} {sign}{pct:>7.2f}%')
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
