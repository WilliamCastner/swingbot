"""
dashboard.py — Generate a static HTML performance dashboard.
Shows main bot results + all 10 strategy comparisons.

Usage:
  py -3.11 scripts/dashboard.py
"""

import sys
import os
import csv
import json
import webbrowser
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOGS       = Path('logs')
TRADE_LOG  = LOGS / 'trades.csv'
PNL_LOG    = LOGS / 'daily_pnl.csv'
STRAT_LOGS = LOGS / 'strategies'
OUT        = Path('dashboard.html')

COLORS = [
    '#00c896', '#4a9eff', '#ff6b6b', '#ffd93d', '#c77dff',
    '#ff9f43', '#00d2d3', '#ff6348', '#a29bfe', '#55efc4',
]


def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def read_strategy_data():
    strategies = []
    if not STRAT_LOGS.exists():
        return strategies
    for slug_dir in sorted(STRAT_LOGS.iterdir()):
        if not slug_dir.is_dir():
            continue
        pnl_file = slug_dir / 'pnl.csv'
        if not pnl_file.exists():
            continue
        name_file = slug_dir / 'name.txt'
        name = name_file.read_text().strip() if name_file.exists() else slug_dir.name.replace('_', ' ').title()
        pnl_rows = read_csv(pnl_file)
        trades = read_csv(slug_dir / 'trades.csv') if (slug_dir / 'trades.csv').exists() else []
        if not pnl_rows:
            continue
        latest = pnl_rows[-1]
        strategies.append({
            'name': name,
            'pnl_rows': pnl_rows,
            'trades': trades,
            'current_value': float(latest['portfolio_value']),
            'total_pnl': float(latest['total_pnl']),
            'total_pnl_pct': float(latest['total_pnl_pct']),
            'drawdown_pct': float(latest['drawdown_pct']),
            'n_trades': len(trades),
        })
    strategies.sort(key=lambda s: s['total_pnl_pct'], reverse=True)
    return strategies


def build_html(trades, pnl_rows, strategies):
    # ── main bot summary ───────────────────────────────────────────────────────
    start_val  = float(pnl_rows[0]['portfolio_value'])  if pnl_rows else 100_000
    latest_val = float(pnl_rows[-1]['portfolio_value']) if pnl_rows else 100_000
    total_pnl  = latest_val - start_val
    total_pct  = (total_pnl / start_val * 100) if start_val else 0
    drawdown   = float(pnl_rows[-1]['drawdown_pct']) if pnl_rows else 0
    n_trades   = len(trades)
    sign       = '+' if total_pnl >= 0 else ''
    pnl_color  = '#00c896' if total_pnl >= 0 else '#ff4d4d'
    dd_color   = '#ff4d4d' if drawdown > 5 else '#aaa'

    dates_js  = json.dumps([r['date'] for r in pnl_rows])
    values_js = json.dumps([float(r['portfolio_value']) for r in pnl_rows])
    dds_js    = json.dumps([float(r['drawdown_pct']) for r in pnl_rows])

    # ── trade log rows ─────────────────────────────────────────────────────────
    trade_rows_html = ''
    for t in reversed(trades):
        side_color = '#00c896' if t['side'] == 'BUY' else '#ff4d4d'
        ts = t['timestamp'][:16].replace('T', ' ')
        trade_rows_html += f"""
        <tr>
          <td>{ts}</td><td><strong>{t['symbol']}</strong></td>
          <td style="color:{side_color};font-weight:700">{t['side']}</td>
          <td>{float(t['qty']):.4f}</td><td>${float(t['price']):.2f}</td>
          <td>{float(t['signal_rsi']):.1f}</td>
          <td style="color:#aaa;font-size:0.85em">{t['signal_reason']}</td>
        </tr>"""
    if not trade_rows_html:
        trade_rows_html = '<tr><td colspan="7" style="color:#555;text-align:center;padding:20px">No trades yet — run the bot after market close.</td></tr>'

    # ── strategy leaderboard rows ──────────────────────────────────────────────
    strat_rows_html = ''
    for i, s in enumerate(strategies):
        pct = s['total_pnl_pct']
        pnl = s['total_pnl']
        color = '#00c896' if pct >= 0 else '#ff4d4d'
        sign_s = '+' if pct >= 0 else ''
        medal = ['🥇', '🥈', '🥉'][i] if i < 3 else f'{i+1}.'
        strat_rows_html += f"""
        <tr>
          <td style="color:#666">{medal}</td>
          <td><strong>{s['name']}</strong></td>
          <td>${s['current_value']:,.2f}</td>
          <td style="color:{color};font-weight:700">{sign_s}{pct:.2f}%</td>
          <td style="color:{color}">{sign_s}${pnl:,.2f}</td>
          <td style="color:#ff4d4d">{s['drawdown_pct']:.2f}%</td>
          <td>{s['n_trades']}</td>
        </tr>"""
    if not strat_rows_html:
        strat_rows_html = '<tr><td colspan="7" style="color:#555;text-align:center;padding:20px">No strategy data yet — run scripts/run_strategies.py</td></tr>'

    # ── strategy chart datasets ────────────────────────────────────────────────
    strat_datasets_js = '[]'
    if strategies:
        datasets = []
        for i, s in enumerate(strategies):
            color = COLORS[i % len(COLORS)]
            dates = [r['date'] for r in s['pnl_rows']]
            values = [float(r['portfolio_value']) for r in s['pnl_rows']]
            datasets.append(
                f'{{"label":{json.dumps(s["name"])},'
                f'"data":{json.dumps([{"x": d, "y": v} for d, v in zip(dates, values)])},'
                f'"borderColor":"{color}","backgroundColor":"transparent",'
                f'"borderWidth":2,"pointRadius":0,"tension":0.3}}'
            )
        strat_datasets_js = '[' + ','.join(datasets) + ']'

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SwingBot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0d0d0d;color:#e0e0e0;font-family:'Segoe UI',system-ui,sans-serif;padding:24px;max-width:1400px;margin:0 auto}}
  h1{{font-size:1.4rem;font-weight:600;margin-bottom:4px}}
  h2{{font-size:1rem;font-weight:600;margin:28px 0 14px}}
  .sub{{color:#666;font-size:0.85rem;margin-bottom:28px}}
  .cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}}
  .card{{background:#161616;border:1px solid #222;border-radius:10px;padding:18px 22px;min-width:140px;flex:1}}
  .card .label{{font-size:0.72rem;color:#555;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}}
  .card .val{{font-size:1.45rem;font-weight:700}}
  .charts{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px}}
  .chart-box{{background:#161616;border:1px solid #222;border-radius:10px;padding:18px}}
  .chart-box .chart-title{{font-size:0.75rem;color:#555;text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px}}
  .chart-box.full{{grid-column:1/-1}}
  table{{width:100%;border-collapse:collapse;background:#161616;border-radius:10px;overflow:hidden;border:1px solid #222;margin-bottom:28px}}
  th{{padding:10px 14px;text-align:left;font-size:0.72rem;color:#444;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #222}}
  td{{padding:10px 14px;font-size:0.88rem;border-bottom:1px solid #1a1a1a}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#1c1c1c}}
  .section-label{{font-size:0.72rem;color:#444;text-transform:uppercase;letter-spacing:.08em;margin:28px 0 12px;padding-bottom:8px;border-bottom:1px solid #1e1e1e}}
  @media(max-width:700px){{.charts{{grid-template-columns:1fr}}.chart-box.full{{grid-column:1}}}}
</style>
</head>
<body>

<h1>SwingBot Dashboard</h1>
<div class="sub">Updated {now} &nbsp;·&nbsp; Paper trading &nbsp;·&nbsp; NVDA · TSLA · AMD · COIN · SPY</div>

<!-- ── Main Bot Summary ───────────────────────────────────────── -->
<div class="section-label">Main Bot (Alpaca Paper)</div>
<div class="cards">
  <div class="card">
    <div class="label">Portfolio Value</div>
    <div class="val">${latest_val:,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Total P&amp;L</div>
    <div class="val" style="color:{pnl_color}">{sign}${total_pnl:,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Total Return</div>
    <div class="val" style="color:{pnl_color}">{sign}{total_pct:.2f}%</div>
  </div>
  <div class="card">
    <div class="label">Max Drawdown</div>
    <div class="val" style="color:{dd_color}">{drawdown:.2f}%</div>
  </div>
  <div class="card">
    <div class="label">Trades</div>
    <div class="val">{n_trades}</div>
  </div>
</div>

<div class="charts">
  <div class="chart-box">
    <div class="chart-title">Portfolio Value</div>
    <canvas id="valueChart" height="160"></canvas>
  </div>
  <div class="chart-box">
    <div class="chart-title">Drawdown %</div>
    <canvas id="ddChart" height="160"></canvas>
  </div>
</div>

<!-- ── Strategy Leaderboard ───────────────────────────────────── -->
<div class="section-label">Strategy Comparison (10 Virtual Portfolios · $100k each)</div>
<table>
  <thead>
    <tr><th>#</th><th>Strategy</th><th>Value</th><th>Return</th><th>P&amp;L</th><th>Drawdown</th><th>Trades</th></tr>
  </thead>
  <tbody>{strat_rows_html}</tbody>
</table>

<!-- ── Strategy Equity Curves ─────────────────────────────────── -->
<div class="charts">
  <div class="chart-box full">
    <div class="chart-title">Strategy Equity Curves — All 10 Strategies</div>
    <canvas id="stratChart" height="90"></canvas>
  </div>
</div>

<!-- ── Trade Log ──────────────────────────────────────────────── -->
<div class="section-label">Main Bot Trade Log</div>
<table>
  <thead>
    <tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>RSI</th><th>Reason</th></tr>
  </thead>
  <tbody>{trade_rows_html}</tbody>
</table>

<script>
const gridColor = 'rgba(255,255,255,0.04)';
const tickColor = '#444';

// Main bot — portfolio value
new Chart(document.getElementById('valueChart'), {{
  type: 'line',
  data: {{
    labels: {dates_js},
    datasets: [{{
      data: {values_js},
      borderColor: '#00c896', backgroundColor: 'rgba(0,200,150,0.07)',
      borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: tickColor, maxTicksLimit: 5 }}, grid: {{ color: gridColor }} }},
      y: {{ ticks: {{ color: tickColor, callback: v => '$' + v.toLocaleString() }}, grid: {{ color: gridColor }} }}
    }}
  }}
}});

// Main bot — drawdown
new Chart(document.getElementById('ddChart'), {{
  type: 'line',
  data: {{
    labels: {dates_js},
    datasets: [{{
      data: {dds_js},
      borderColor: '#ff4d4d', backgroundColor: 'rgba(255,77,77,0.07)',
      borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: tickColor, maxTicksLimit: 5 }}, grid: {{ color: gridColor }} }},
      y: {{ ticks: {{ color: tickColor, callback: v => v + '%' }}, grid: {{ color: gridColor }} }}
    }}
  }}
}});

// Strategy equity curves
const stratDatasets = {strat_datasets_js};
if (stratDatasets.length > 0) {{
  new Chart(document.getElementById('stratChart'), {{
    type: 'line',
    data: {{ datasets: stratDatasets }},
    options: {{
      parsing: false,
      plugins: {{
        legend: {{
          display: true,
          labels: {{ color: '#666', boxWidth: 12, font: {{ size: 11 }} }}
        }}
      }},
      scales: {{
        x: {{
          type: 'time',
          time: {{ unit: 'day' }},
          ticks: {{ color: tickColor, maxTicksLimit: 8 }},
          grid: {{ color: gridColor }}
        }},
        y: {{
          ticks: {{ color: tickColor, callback: v => '$' + v.toLocaleString() }},
          grid: {{ color: gridColor }}
        }}
      }}
    }}
  }});
}} else {{
  document.getElementById('stratChart').parentElement.innerHTML +=
    '<p style="color:#555;text-align:center;padding:40px 0">Run scripts/run_strategies.py to populate strategy data.</p>';
}}
</script>
</body>
</html>"""


def main(no_browser: bool = False):
    trades     = read_csv(TRADE_LOG)
    pnl_rows   = read_csv(PNL_LOG)
    strategies = read_strategy_data()
    html       = build_html(trades, pnl_rows, strategies)
    OUT.write_text(html, encoding='utf-8')
    print(f"Dashboard written to {OUT.resolve()}")
    print(f"  Main bot trades: {len(trades)}")
    print(f"  Strategies tracked: {len(strategies)}")
    if not no_browser:
        webbrowser.open(OUT.resolve().as_uri())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true',
                        help='Skip opening browser (for CI)')
    args = parser.parse_args()
    main(no_browser=args.no_browser)
