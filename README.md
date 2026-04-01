# SwingBot — Low-Budget US Equity Swing Trading Bot

## Context (for Claude Code)
This project was designed with the following constraints and goals:
- **Capital**: ~$500
- **Market**: US equities (via Alpaca — free tier)
- **Strategy**: Mean reversion swing trading on liquid ETFs (SPY, QQQ, IWM)
- **Holding period**: 2–5 days
- **Language**: Python
- **Infra cost**: $0 (runs locally or on PythonAnywhere free tier)
- **Goal**: Prove edge at small scale, build reusable infrastructure to scale up later

## Strategy Logic
- **Signal**: RSI(14) < 35 (oversold) AND price within 3% above 20-day MA → BUY
- **Exit**: RSI(14) > 60 → SELL
- **Universe**: SPY, QQQ, IWM (liquid ETFs, tight spreads, fractional shares)
- **Position sizing**: Never more than 90% of portfolio in one position
- **Risk**: Kill switch at 15% drawdown, 2% max daily loss

## Architecture
```
swingbot/
├── bot/
│   ├── strategy.py      # Signal generation (RSI + MA mean reversion)
│   ├── risk.py          # RiskManager — position sizing, kill switch
│   ├── execution.py     # Alpaca API wrapper (paper + live)
│   ├── data.py          # Market data fetching via yfinance + Alpaca
│   └── monitor.py       # Logging, P&L tracking, email/Slack alerts
├── scripts/
│   └── run_bot.py       # Daily entry point — run after market close
├── tests/
│   └── test_strategy.py # Backtesting harness using vectorbt
├── logs/                # Trade log CSVs + daily P&L
├── .env.example         # API key template (never commit real .env)
└── requirements.txt
```

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your Alpaca API keys in .env
# Run paper trading first:
python scripts/run_bot.py --paper
# After 60+ days of paper trading with positive results, go live:
python scripts/run_bot.py --live
```

## Important rules hardcoded in this bot
1. Paper trade for at least 60 days before going live
2. Kill switch triggers at 15% portfolio drawdown
3. Max 2% daily loss before bot halts
4. Never trade within 30 min of FOMC, CPI, NFP events
5. Never hold through earnings — bot checks and skips
6. Max 1-2 positions at a time (concentration, not diversification at $500)
