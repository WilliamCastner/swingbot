"""
execution.py — Alpaca brokerage wrapper
Handles paper and live trading via alpaca-py.
Always paper trades by default — set ALPACA_PAPER=false in .env to go live.
"""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

load_dotenv()


def _get_client() -> TradingClient:
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    paper = os.getenv('ALPACA_PAPER', 'true').lower() != 'false'

    if not api_key or not secret_key:
        raise ValueError(
            'Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env file. '
            'Copy .env.example to .env and fill in your keys from alpaca.markets'
        )

    return TradingClient(api_key, secret_key, paper=paper)


def get_account() -> dict:
    """Return account info including portfolio value and buying power."""
    client = _get_client()
    account = client.get_account()
    return {
        'portfolio_value': float(account.portfolio_value),
        'buying_power': float(account.buying_power),
        'cash': float(account.cash),
        'equity': float(account.equity),
        'paper': os.getenv('ALPACA_PAPER', 'true').lower() != 'false',
    }


def get_positions() -> dict[str, dict]:
    """Return current open positions keyed by symbol."""
    client = _get_client()
    positions = client.get_all_positions()
    return {
        p.symbol: {
            'qty': float(p.qty),
            'avg_entry_price': float(p.avg_entry_price),
            'market_value': float(p.market_value),
            'unrealized_pl': float(p.unrealized_pl),
            'unrealized_plpc': float(p.unrealized_plpc),
        }
        for p in positions
    }


def place_buy_order(symbol: str, qty: float) -> dict:
    """
    Place a fractional market buy order.
    qty can be fractional (e.g. 0.5 shares of SPY).
    """
    client = _get_client()
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
    result = client.submit_order(order)
    return {
        'id': str(result.id),
        'symbol': result.symbol,
        'qty': float(result.qty),
        'side': str(result.side),
        'status': str(result.status),
    }


def place_sell_order(symbol: str, qty: float) -> dict:
    """Place a fractional market sell order."""
    client = _get_client()
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    result = client.submit_order(order)
    return {
        'id': str(result.id),
        'symbol': result.symbol,
        'qty': float(result.qty),
        'side': str(result.side),
        'status': str(result.status),
    }


def close_position(symbol: str) -> dict:
    """Close entire position in a symbol."""
    client = _get_client()
    result = client.close_position(symbol)
    return {
        'id': str(result.id),
        'symbol': result.symbol,
        'status': str(result.status),
    }


def get_recent_orders(limit: int = 10) -> list[dict]:
    """Return the most recent orders."""
    client = _get_client()
    request = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=limit)
    orders = client.get_orders(request)
    return [
        {
            'id': str(o.id),
            'symbol': o.symbol,
            'qty': float(o.qty) if o.qty else None,
            'side': str(o.side),
            'status': str(o.status),
            'filled_avg_price': float(o.filled_avg_price) if o.filled_avg_price else None,
            'submitted_at': str(o.submitted_at),
        }
        for o in orders
    ]
