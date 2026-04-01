"""
crypto_execution.py — Alpaca crypto order wrapper.
Same client as stocks but uses GTC (crypto trades 24/7, no DAY orders).
"""

import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()


def _get_client() -> TradingClient:
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    if not api_key or not secret_key:
        raise ValueError('Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env')
    return TradingClient(api_key, secret_key, paper=True)


def get_crypto_positions() -> dict[str, dict]:
    """Return open crypto positions keyed by Alpaca symbol (e.g. SOLUSD)."""
    client = _get_client()
    positions = client.get_all_positions()
    crypto_symbols = {'SOLUSD', 'ETHUSD', 'DOGEUSD', 'AVAXUSD',
                      'BTCUSD', 'LINKUSD', 'UNIUSD'}
    return {
        p.symbol: {
            'qty': float(p.qty),
            'avg_entry_price': float(p.avg_entry_price),
            'market_value': float(p.market_value),
            'unrealized_pl': float(p.unrealized_pl),
            'unrealized_plpc': float(p.unrealized_plpc),
        }
        for p in positions
        if p.symbol in crypto_symbols
    }


def place_crypto_buy(symbol: str, qty: float) -> dict:
    """Buy crypto. symbol = Alpaca format (e.g. 'SOLUSD'). qty = coin amount."""
    client = _get_client()
    order = MarketOrderRequest(
        symbol=symbol,
        qty=round(qty, 8),
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC,
    )
    result = client.submit_order(order)
    return {'id': str(result.id), 'symbol': result.symbol,
            'qty': float(result.qty), 'status': str(result.status)}


def close_crypto_position(symbol: str) -> dict:
    """Close entire crypto position."""
    client = _get_client()
    result = client.close_position(symbol)
    return {'id': str(result.id), 'symbol': result.symbol,
            'status': str(result.status)}
