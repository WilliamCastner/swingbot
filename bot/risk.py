"""
risk.py — Risk management
Handles position sizing, kill switch, and event calendar filtering.
At sub-$500 capital, risk management is more important than signal quality.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path


# High-impact US economic events — dates to avoid trading around.
# Update this list monthly or fetch from a calendar API.
# Format: 'YYYY-MM-DD'
HIGH_IMPACT_DATES: list[str] = [
    # Add upcoming FOMC, CPI, NFP dates here
    # e.g. '2025-11-07',  # FOMC
    # e.g. '2025-11-08',  # NFP
]


class RiskManager:
    def __init__(
        self,
        portfolio_value: float,
        max_position_pct: float = 0.95,    # max 95% in one position (concentrated)
        max_drawdown_pct: float = 0.25,    # kill switch at 25% drawdown
        max_daily_loss_pct: float = 0.02,  # halt at 2% daily loss
        max_positions: int = 3,            # never hold more than 3 at once
    ):
        self.portfolio_value = portfolio_value
        self.peak_value = portfolio_value
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_positions = max_positions
        self.daily_start_value = portfolio_value
        self._state_path = Path('logs/risk_state.json')
        self._load_state()

    def _load_state(self):
        """Persist peak value across runs so drawdown is tracked correctly."""
        if self._state_path.exists():
            try:
                state = json.loads(self._state_path.read_text())
                self.peak_value = state.get('peak_value', self.portfolio_value)
                self.daily_start_value = state.get(
                    'daily_start_value', self.portfolio_value)
            except Exception:
                pass

    def save_state(self):
        self._state_path.parent.mkdir(exist_ok=True)
        self._state_path.write_text(json.dumps({
            'peak_value': self.peak_value,
            'daily_start_value': self.daily_start_value,
            'updated': datetime.now().isoformat(),
        }))

    def update_portfolio_value(self, current_value: float):
        """Call this at the start of each run with current portfolio value."""
        self.portfolio_value = current_value
        if current_value > self.peak_value:
            self.peak_value = current_value
        self.save_state()

    def position_size_dollars(self, price: float) -> float:
        """
        How many dollars to deploy in one trade.
        Conservative: never more than max_position_pct of portfolio.
        """
        return min(
            self.portfolio_value * self.max_position_pct,
            self.portfolio_value - 1.0   # always keep $1 buffer
        )

    def position_size_shares(self, price: float) -> float:
        """Fractional shares — how many shares to buy at given price."""
        dollars = self.position_size_dollars(price)
        return round(dollars / price, 4)

    def check_kill_switch(self, current_value: float) -> tuple[bool, str]:
        """
        Returns (should_halt, reason).
        Call this before placing any order.
        """
        drawdown = (self.peak_value - current_value) / self.peak_value
        daily_loss = (self.daily_start_value - current_value) / self.daily_start_value

        if drawdown >= self.max_drawdown_pct:
            return True, (f'KILL SWITCH: portfolio drawdown {drawdown:.1%} '
                         f'exceeds limit of {self.max_drawdown_pct:.0%}')

        if daily_loss >= self.max_daily_loss_pct:
            return True, (f'KILL SWITCH: daily loss {daily_loss:.1%} '
                         f'exceeds limit of {self.max_daily_loss_pct:.0%}')

        return False, ''

    def is_safe_to_trade(self, today: date | None = None) -> tuple[bool, str]:
        """
        Check if today is safe to trade (no high-impact events nearby).
        Returns (safe, reason).
        """
        today = today or date.today()
        today_str = today.strftime('%Y-%m-%d')

        if today_str in HIGH_IMPACT_DATES:
            return False, f'High-impact event on {today_str} — skipping'

        # Skip Mondays after a volatile Friday (simple heuristic)
        if today.weekday() == 0:  # Monday
            pass  # could add gap-risk check here

        return True, ''

    def can_add_position(self, current_position_count: int) -> bool:
        """Don't exceed max_positions."""
        return current_position_count < self.max_positions
