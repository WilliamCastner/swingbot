"""
run_strategies.py — Run all 10 strategies as virtual paper simulations.
Each strategy gets its own $100k virtual portfolio. No real Alpaca orders placed.

Usage:
  py -3.11 scripts/run_strategies.py           # run all strategies
  py -3.11 scripts/run_strategies.py --dry-run # signals only, no state changes
"""

import sys
import os
import csv
import json
import argparse
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.data import get_watchlist_data, WATCHLIST
from bot.strategies import ALL_STRATEGIES

LOGS = Path('logs/strategies')
STARTING_CASH = 100_000.0


class VirtualPortfolio:
    def __init__(self, starting_cash: float = STARTING_CASH,
                 max_position_pct: float = 0.95, max_positions: int = 3):
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.positions: dict = {}       # symbol -> {qty, avg_price}
        self.peak_value = starting_cash
        self.max_position_pct = max_position_pct
        self.max_positions = max_positions

    def total_value(self, prices: dict) -> float:
        val = self.cash
        for sym, pos in self.positions.items():
            val += pos['qty'] * prices.get(sym, pos['avg_price'])
        return val

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
        pnl = proceeds - pos['qty'] * pos['avg_price']
        self.cash += proceeds
        return pos['qty'], pnl

    def to_dict(self) -> dict:
        return {
            'cash': self.cash,
            'starting_cash': self.starting_cash,
            'positions': self.positions,
            'peak_value': self.peak_value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'VirtualPortfolio':
        p = cls(starting_cash=d.get('starting_cash', STARTING_CASH))
        p.cash = d['cash']
        p.positions = d.get('positions', {})
        p.peak_value = d.get('peak_value', p.total_value({}))
        return p


def load_portfolio(log_dir: Path) -> VirtualPortfolio:
    state = log_dir / 'portfolio.json'
    if state.exists():
        try:
            return VirtualPortfolio.from_dict(json.loads(state.read_text()))
        except Exception:
            pass
    return VirtualPortfolio()


def save_portfolio(portfolio: VirtualPortfolio, log_dir: Path):
    (log_dir / 'portfolio.json').write_text(
        json.dumps(portfolio.to_dict(), indent=2))


def log_trade(log_dir: Path, symbol: str, side: str,
              qty: float, price: float, pnl: float, reason: str):
    trade_file = log_dir / 'trades.csv'
    write_header = not trade_file.exists()
    with open(trade_file, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=[
            'timestamp', 'symbol', 'side', 'qty', 'price', 'pnl', 'reason'])
        if write_header:
            w.writeheader()
        w.writerow({
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol, 'side': side,
            'qty': round(qty, 4), 'price': round(price, 2),
            'pnl': round(pnl, 2), 'reason': reason,
        })


def log_pnl(log_dir: Path, portfolio: VirtualPortfolio, prices: dict) -> float:
    total = portfolio.total_value(prices)
    if total > portfolio.peak_value:
        portfolio.peak_value = total
    drawdown = ((portfolio.peak_value - total) / portfolio.peak_value * 100
                if portfolio.peak_value else 0)
    total_pnl = total - portfolio.starting_cash
    pnl_file = log_dir / 'pnl.csv'
    write_header = not pnl_file.exists()
    with open(pnl_file, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=[
            'date', 'portfolio_value', 'total_pnl', 'total_pnl_pct', 'drawdown_pct'])
        if write_header:
            w.writeheader()
        w.writerow({
            'date': date.today().isoformat(),
            'portfolio_value': round(total, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl / portfolio.starting_cash * 100, 3),
            'drawdown_pct': round(drawdown, 3),
        })
    return total


def run_strategy(strategy, market_data: dict, dry_run: bool = False):
    slug = (strategy.name.lower()
            .replace(' ', '_').replace('/', '_')
            .replace('(', '').replace(')', ''))
    log_dir = LOGS / slug
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / 'name.txt').write_text(strategy.name)

    portfolio = load_portfolio(log_dir)
    prices = {sym: float(df['Close'].iloc[-1]) for sym, df in market_data.items()}

    signals = {sym: strategy.compute_signal(df, sym)
               for sym, df in market_data.items()}

    if not dry_run:
        for symbol, result in signals.items():
            if result.signal == 'SELL' and symbol in portfolio.positions:
                qty, pnl = portfolio.sell(symbol, result.price)
                if qty > 0:
                    log_trade(log_dir, symbol, 'SELL', qty, result.price, pnl, result.reason)

        for symbol, result in signals.items():
            if result.signal == 'BUY' and portfolio.can_buy(symbol):
                qty = portfolio.buy(symbol, result.price)
                if qty > 0:
                    log_trade(log_dir, symbol, 'BUY', qty, result.price, 0.0, result.reason)

        save_portfolio(portfolio, log_dir)

    total = log_pnl(log_dir, portfolio, prices)
    return signals, total, portfolio


def main(dry_run: bool = False):
    print(f"\nSwingBot Strategy Comparison — {date.today()}")
    print(f"Watchlist: {', '.join(WATCHLIST)}")
    print(f"{'DRY RUN — no state changes' if dry_run else 'Live run — updating portfolios'}\n")

    market_data = get_watchlist_data(days=250)

    results = []
    for strategy in ALL_STRATEGIES:
        signals, total_val, portfolio = run_strategy(strategy, market_data, dry_run)
        pnl = total_val - portfolio.starting_cash
        pnl_pct = pnl / portfolio.starting_cash * 100
        sign = '+' if pnl >= 0 else ''
        buys = [s.symbol for s in signals.values() if s.signal == 'BUY']
        sells = [s.symbol for s in signals.values() if s.signal == 'SELL']
        mode = '[DRY]' if dry_run else '     '
        print(f"{mode} {strategy.name:<28} ${total_val:>10,.2f}  "
              f"({sign}{pnl_pct:.2f}%)  "
              f"BUY:{buys or '-'}  SELL:{sells or '-'}")
        results.append((strategy.name, total_val, pnl_pct))

    results.sort(key=lambda x: x[2], reverse=True)
    print(f"\n{'-' * 55}")
    print("Leaderboard:")
    for i, (name, val, pct) in enumerate(results, 1):
        sign = '+' if pct >= 0 else ''
        print(f"  {i:>2}. {name:<28} {sign}{pct:>7.2f}%")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run all 10 strategy simulations')
    parser.add_argument('--dry-run', action='store_true',
                        help='Compute signals only, no portfolio state changes')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
