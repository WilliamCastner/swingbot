"""
run_crypto_bot.py — Crypto bot runner.
Runs every 4 hours via GitHub Actions (crypto trades 24/7).

Usage:
  py -3.11 scripts/run_crypto_bot.py
  py -3.11 scripts/run_crypto_bot.py --dry-run
"""

import sys
import os
import csv
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from dotenv import load_dotenv
load_dotenv()

from bot.crypto_data import get_crypto_watchlist_data, CRYPTO_WATCHLIST, yf_to_alpaca
from bot.crypto_strategy import compute_crypto_signal
from bot.crypto_execution import get_crypto_positions, place_crypto_buy, close_crypto_position

LOG_DIR    = Path('logs/crypto')
TRADE_LOG  = LOG_DIR / 'trades.csv'
PNL_LOG    = LOG_DIR / 'pnl.csv'
STATE_FILE = LOG_DIR / 'state.json'

STARTING_CASH   = 100_000.0
MAX_POS_PCT     = 0.95
MAX_POSITIONS   = 2
KILL_SWITCH_PCT = 0.30   # halt at 30% drawdown (crypto is volatile)

TRADE_FIELDS = ['timestamp', 'symbol', 'side', 'qty', 'price', 'order_id', 'reason']
PNL_FIELDS   = ['timestamp', 'portfolio_value', 'total_pnl', 'total_pnl_pct', 'drawdown_pct']


def _ensure_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not TRADE_LOG.exists():
        with open(TRADE_LOG, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=TRADE_FIELDS).writeheader()
    if not PNL_LOG.exists():
        with open(PNL_LOG, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=PNL_FIELDS).writeheader()


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {'peak_value': STARTING_CASH, 'starting_cash': STARTING_CASH}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def log_trade(symbol: str, side: str, qty: float, price: float,
              order_id: str, reason: str):
    with open(TRADE_LOG, 'a', newline='') as f:
        csv.DictWriter(f, fieldnames=TRADE_FIELDS).writerow({
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol, 'side': side,
            'qty': round(qty, 8), 'price': round(price, 6),
            'order_id': order_id, 'reason': reason,
        })
    print(f'[CRYPTO] {side} {qty:.4f} {symbol} @ ${price:.4f} | {reason}')


def log_pnl(portfolio_value: float, state: dict):
    peak = state.get('peak_value', STARTING_CASH)
    starting = state.get('starting_cash', STARTING_CASH)
    if portfolio_value > peak:
        state['peak_value'] = portfolio_value
        peak = portfolio_value
    drawdown = (peak - portfolio_value) / peak * 100 if peak else 0
    total_pnl = portfolio_value - starting
    with open(PNL_LOG, 'a', newline='') as f:
        csv.DictWriter(f, fieldnames=PNL_FIELDS).writerow({
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': round(portfolio_value, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl / starting * 100, 3),
            'drawdown_pct': round(drawdown, 3),
        })


def estimate_portfolio_value(positions: dict, prices: dict, cash_estimate: float) -> float:
    """Estimate total value: cash + open position market values."""
    value = cash_estimate
    for sym, pos in positions.items():
        yf_sym = sym  # already mapped
        price = prices.get(sym, pos['avg_entry_price'])
        value += pos['qty'] * price
    return value


def main(dry_run: bool = False):
    _ensure_logs()
    state = load_state()

    print(f'\nCrypto bot starting — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'Watchlist: {", ".join(CRYPTO_WATCHLIST)}')

    # Fetch market data
    market_data = get_crypto_watchlist_data(days=60)

    # Compute signals
    signals = []
    for symbol in CRYPTO_WATCHLIST:
        if symbol not in market_data:
            continue
        alpaca_sym = yf_to_alpaca(symbol)
        result = compute_crypto_signal(market_data[symbol], symbol, alpaca_sym)
        signals.append(result)
        print(f'  {symbol:<10} {result.signal:4s} | RSI(7)={result.rsi:.1f} | {result.reason}')

    # Get current positions
    try:
        positions = get_crypto_positions()
    except Exception as e:
        print(f'Warning: could not fetch positions: {e}')
        positions = {}

    # Current prices from signals
    prices = {yf_to_alpaca(s.symbol): s.price for s in signals}

    # Estimate cash (rough: starting cash minus deployed capital)
    deployed = sum(p['market_value'] for p in positions.values())
    cash_estimate = max(state.get('starting_cash', STARTING_CASH) - deployed, 0)
    portfolio_value = sum(p['market_value'] for p in positions.values()) + cash_estimate

    # Kill switch
    peak = state.get('peak_value', STARTING_CASH)
    drawdown = (peak - portfolio_value) / peak if peak else 0
    if drawdown >= KILL_SWITCH_PCT:
        print(f'KILL SWITCH: drawdown {drawdown:.1%} exceeds {KILL_SWITCH_PCT:.0%}')
        log_pnl(portfolio_value, state)
        save_state(state)
        return

    # Execute signals
    for result in signals:
        alpaca_sym = result.alpaca_symbol

        # SELL
        if result.signal == 'SELL' and alpaca_sym in positions:
            if dry_run:
                print(f'[DRY RUN] Would SELL {alpaca_sym}')
                continue
            try:
                order = close_crypto_position(alpaca_sym)
                pos = positions.pop(alpaca_sym)
                log_trade(alpaca_sym, 'SELL', pos['qty'], result.price,
                          order['id'], result.reason)
                cash_estimate += pos['qty'] * result.price
            except Exception as e:
                print(f'SELL failed for {alpaca_sym}: {e}')

        # BUY
        elif (result.signal == 'BUY'
              and alpaca_sym not in positions
              and len(positions) < MAX_POSITIONS):
            dollars = cash_estimate * MAX_POS_PCT
            qty = dollars / result.price if result.price > 0 else 0
            if qty <= 0:
                print(f'Skipping BUY {alpaca_sym} — insufficient funds')
                continue
            if dry_run:
                print(f'[DRY RUN] Would BUY {qty:.4f} {alpaca_sym} @ ${result.price:.4f}')
                continue
            try:
                order = place_crypto_buy(alpaca_sym, qty)
                log_trade(alpaca_sym, 'BUY', qty, result.price,
                          order['id'], result.reason)
                positions[alpaca_sym] = {
                    'qty': qty, 'avg_entry_price': result.price,
                    'market_value': qty * result.price,
                    'unrealized_pl': 0, 'unrealized_plpc': 0,
                }
                cash_estimate -= dollars
            except Exception as e:
                print(f'BUY failed for {alpaca_sym}: {e}')

    # Update portfolio value and log
    portfolio_value = sum(
        pos['qty'] * prices.get(sym, pos['avg_entry_price'])
        for sym, pos in positions.items()
    ) + cash_estimate

    log_pnl(portfolio_value, state)
    save_state(state)

    sign = '+' if portfolio_value >= state['starting_cash'] else ''
    pnl = portfolio_value - state['starting_cash']
    print(f'\nCrypto portfolio: ${portfolio_value:,.2f} ({sign}${pnl:,.2f})')
    print(f'Open positions: {list(positions.keys()) or "none"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
