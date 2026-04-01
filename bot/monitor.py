"""
monitor.py — Trade logging, P&L tracking, and alerts
Writes a CSV trade log and prints daily summaries.
Optional Slack webhook for real-time alerts.
"""

import os
import csv
import json
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = Path('logs')
TRADE_LOG = LOG_DIR / 'trades.csv'
PNL_LOG = LOG_DIR / 'daily_pnl.csv'

TRADE_FIELDS = [
    'timestamp', 'symbol', 'side', 'qty', 'price',
    'order_id', 'portfolio_value', 'signal_rsi', 'signal_reason'
]

PNL_FIELDS = ['date', 'portfolio_value', 'daily_pnl', 'daily_pnl_pct',
              'peak_value', 'drawdown_pct']


def _ensure_logs():
    LOG_DIR.mkdir(exist_ok=True)
    if not TRADE_LOG.exists():
        with open(TRADE_LOG, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=TRADE_FIELDS).writeheader()
    if not PNL_LOG.exists():
        with open(PNL_LOG, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=PNL_FIELDS).writeheader()


def log_trade(symbol: str, side: str, qty: float, price: float,
              order_id: str, portfolio_value: float,
              signal_rsi: float = 0.0, signal_reason: str = ''):
    _ensure_logs()
    row = {
        'timestamp': datetime.now().isoformat(),
        'symbol': symbol,
        'side': side,
        'qty': qty,
        'price': price,
        'order_id': order_id,
        'portfolio_value': round(portfolio_value, 2),
        'signal_rsi': round(signal_rsi, 2),
        'signal_reason': signal_reason,
    }
    with open(TRADE_LOG, 'a', newline='') as f:
        csv.DictWriter(f, fieldnames=TRADE_FIELDS).writerow(row)
    print(f"[TRADE] {side} {qty} {symbol} @ ${price:.2f} | RSI={signal_rsi:.1f}")


def log_daily_pnl(portfolio_value: float, peak_value: float,
                  prev_value: float):
    _ensure_logs()
    daily_pnl = portfolio_value - prev_value
    daily_pnl_pct = daily_pnl / prev_value if prev_value else 0
    drawdown = (peak_value - portfolio_value) / peak_value if peak_value else 0
    row = {
        'date': datetime.now().date().isoformat(),
        'portfolio_value': round(portfolio_value, 2),
        'daily_pnl': round(daily_pnl, 2),
        'daily_pnl_pct': round(daily_pnl_pct * 100, 3),
        'peak_value': round(peak_value, 2),
        'drawdown_pct': round(drawdown * 100, 3),
    }
    with open(PNL_LOG, 'a', newline='') as f:
        csv.DictWriter(f, fieldnames=PNL_FIELDS).writerow(row)
    sign = '+' if daily_pnl >= 0 else ''
    print(f"[P&L] Portfolio: ${portfolio_value:.2f} | "
          f"Daily: {sign}${daily_pnl:.2f} ({sign}{daily_pnl_pct*100:.2f}%) | "
          f"Drawdown: {drawdown*100:.1f}%")


def send_alert(message: str, level: str = 'INFO'):
    """
    Print to console. Optionally send to Slack if SLACK_WEBHOOK_URL is set.
    level: 'INFO', 'WARN', 'KILL'
    """
    prefix = {'INFO': '', 'WARN': 'WARNING: ', 'KILL': 'KILL SWITCH: '}.get(level, '')
    full_msg = f"[SwingBot] {prefix}{message}"
    print(full_msg)

    webhook = os.getenv('SLACK_WEBHOOK_URL')
    if webhook:
        try:
            emoji = {'INFO': ':chart_with_upwards_trend:',
                     'WARN': ':warning:', 'KILL': ':stop_sign:'}.get(level, '')
            requests.post(webhook, json={'text': f"{emoji} {full_msg}"},
                         timeout=5)
        except Exception as e:
            print(f"Slack alert failed: {e}")


def print_summary(signals: list, positions: dict, account: dict):
    """Print a readable end-of-run summary."""
    print("\n" + "="*50)
    print(f"SwingBot Run — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Portfolio: ${account['portfolio_value']:.2f} | "
          f"Cash: ${account['cash']:.2f} | "
          f"Mode: {'PAPER' if account['paper'] else 'LIVE'}")
    print(f"\nSignals:")
    for s in signals:
        print(f"  {s.symbol}: {s.signal:4s} | RSI={s.rsi:.1f} | "
              f"Price=${s.price:.2f} | {s.reason}")
    print(f"\nOpen positions: {len(positions)}")
    for sym, pos in positions.items():
        pl_sign = '+' if pos['unrealized_pl'] >= 0 else ''
        print(f"  {sym}: {pos['qty']} shares | "
              f"Entry=${pos['avg_entry_price']:.2f} | "
              f"P&L: {pl_sign}${pos['unrealized_pl']:.2f} "
              f"({pl_sign}{pos['unrealized_plpc']*100:.1f}%)")
    print("="*50 + "\n")
