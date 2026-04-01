"""
run_bot.py — Daily entry point
Run this once after market close each trading day.

Usage:
  python scripts/run_bot.py           # uses ALPACA_PAPER setting from .env
  python scripts/run_bot.py --paper   # force paper mode
  python scripts/run_bot.py --live    # force live mode (be careful)
  python scripts/run_bot.py --dry-run # compute signals only, no orders

Recommended schedule: run at 4:15pm ET Mon-Fri (15 min after close)
Cron example: 15 16 * * 1-5 cd /path/to/swingbot && python scripts/run_bot.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import date

from bot.data import get_watchlist_data, WATCHLIST
from bot.strategy import compute_signals
from bot.risk import RiskManager
from bot.execution import (
    get_account, get_positions, place_buy_order,
    close_position, get_recent_orders
)
from bot.monitor import (
    log_trade, log_daily_pnl, send_alert, print_summary
)


def main(dry_run: bool = False, force_paper: bool = False,
         force_live: bool = False):

    # Override paper/live mode if flags passed
    if force_paper:
        os.environ['ALPACA_PAPER'] = 'true'
    elif force_live:
        os.environ['ALPACA_PAPER'] = 'false'
        print("WARNING: Running in LIVE mode with real money.")

    print(f"\nSwingBot starting — {date.today()}")

    # 1. Get account state
    try:
        account = get_account()
    except Exception as e:
        send_alert(f"Failed to connect to Alpaca: {e}", level='KILL')
        sys.exit(1)

    portfolio_value = account['portfolio_value']
    mode = 'PAPER' if account['paper'] else 'LIVE'
    print(f"Mode: {mode} | Portfolio: ${portfolio_value:.2f}")

    # 2. Initialize risk manager
    risk = RiskManager(portfolio_value)
    risk.update_portfolio_value(portfolio_value)

    # 3. Kill switch check
    halted, reason = risk.check_kill_switch(portfolio_value)
    if halted:
        send_alert(reason, level='KILL')
        sys.exit(0)

    # 4. Event calendar check
    safe, reason = risk.is_safe_to_trade()
    if not safe:
        send_alert(f"Skipping today: {reason}", level='WARN')
        sys.exit(0)

    # 5. Get current positions
    try:
        positions = get_positions()
    except Exception as e:
        send_alert(f"Failed to get positions: {e}", level='WARN')
        positions = {}

    # 6. Fetch market data and compute signals
    print(f"Fetching data for: {', '.join(WATCHLIST)}")
    market_data = get_watchlist_data(days=90)

    signals = []
    for symbol in WATCHLIST:
        if symbol not in market_data:
            continue
        result = compute_signals(market_data[symbol], symbol)
        signals.append(result)
        print(f"  {symbol}: {result.signal:4s} | RSI={result.rsi:.1f} | {result.reason}")

    # 7. Execute signals
    for result in signals:

        # SELL: close position if we hold it and signal says sell
        if result.signal == 'SELL' and result.symbol in positions:
            if dry_run:
                print(f"[DRY RUN] Would SELL {result.symbol}")
                continue
            try:
                order = close_position(result.symbol)
                pos = positions[result.symbol]
                log_trade(
                    symbol=result.symbol, side='SELL',
                    qty=pos['qty'], price=result.price,
                    order_id=order['id'],
                    portfolio_value=portfolio_value,
                    signal_rsi=result.rsi, signal_reason=result.reason
                )
                send_alert(f"SELL {result.symbol} | RSI={result.rsi:.1f} | "
                          f"${result.price:.2f}")
            except Exception as e:
                send_alert(f"SELL order failed for {result.symbol}: {e}",
                          level='WARN')

        # BUY: enter if signal says buy and we don't already hold it
        elif (result.signal == 'BUY'
              and result.symbol not in positions
              and risk.can_add_position(len(positions))):

            qty = risk.position_size_shares(result.price)
            if qty <= 0:
                print(f"Skipping BUY {result.symbol} — insufficient buying power")
                continue

            if dry_run:
                print(f"[DRY RUN] Would BUY {qty:.4f} shares of {result.symbol} "
                      f"@ ${result.price:.2f}")
                continue

            try:
                order = place_buy_order(result.symbol, qty)
                log_trade(
                    symbol=result.symbol, side='BUY',
                    qty=qty, price=result.price,
                    order_id=order['id'],
                    portfolio_value=portfolio_value,
                    signal_rsi=result.rsi, signal_reason=result.reason
                )
                send_alert(f"BUY {qty:.4f} {result.symbol} | RSI={result.rsi:.1f} | "
                          f"${result.price:.2f}")
                positions[result.symbol] = {'qty': qty,
                                            'avg_entry_price': result.price,
                                            'market_value': qty * result.price,
                                            'unrealized_pl': 0,
                                            'unrealized_plpc': 0}
            except Exception as e:
                send_alert(f"BUY order failed for {result.symbol}: {e}",
                          level='WARN')

    # 8. Log daily P&L and print summary
    log_daily_pnl(portfolio_value, risk.peak_value,
                  risk.daily_start_value)
    print_summary(signals, positions, account)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SwingBot daily runner')
    parser.add_argument('--dry-run', action='store_true',
                        help='Compute signals only, place no orders')
    parser.add_argument('--paper', action='store_true',
                        help='Force paper trading mode')
    parser.add_argument('--live', action='store_true',
                        help='Force live trading mode')
    args = parser.parse_args()

    main(dry_run=args.dry_run, force_paper=args.paper,
         force_live=args.live)
