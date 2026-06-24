from __future__ import annotations
"""
backtest.report
===============
HTML report generator for BacktestResult.
Self-contained output — no external dependencies.

Usage:
    from backtest import save_report
    result = Backtest(MyStrategy).run(source)
    save_report(result, "report.html", title="My Strategy")
"""

import html as _html
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backtest.stats import BacktestResult


def _css() -> str:
    return (
        ":root{--bg:#0d1117;--card:#161b22;--border:#30363d;"
        "--text:#e6edf3;--muted:#8b949e;--green:#2ea043;"
        "--red:#da3633;--blue:#388bfd;--yellow:#e3b341}"
        "*{box-sizing:border-box;margin:0;padding:0}"
        "body{background:var(--bg);color:var(--text);"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',monospace;padding:24px}"
        "h1{font-size:1.5rem;margin-bottom:4px}"
        ".sub{color:var(--muted);font-size:.85rem;margin-bottom:24px}"
        ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:24px}"
        ".card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px}"
        ".card-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}"
        ".card-value{font-size:1.4rem;font-weight:700;margin-top:6px}"
        ".green{color:var(--green)}.red{color:var(--red)}.blue{color:var(--blue)}.yellow{color:var(--yellow)}"
        ".section{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:24px;overflow:hidden}"
        ".sec-title{padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:.9rem}"
        ".stats-grid{display:grid;grid-template-columns:1fr 1fr}"
        ".stats-col{}"
        ".stats-col+.stats-col{border-left:1px solid var(--border)}"
        ".srow{display:flex;justify-content:space-between;padding:9px 16px;border-bottom:1px solid rgba(48,54,61,.4)}"
        ".srow:last-child{border-bottom:none}"
        ".slabel{color:var(--muted);font-size:.82rem}"
        ".sval{font-weight:500;font-size:.85rem}"
        "table{width:100%;border-collapse:collapse;font-size:.78rem}"
        "th{padding:9px 14px;text-align:left;color:var(--muted);font-weight:500;border-bottom:1px solid var(--border)}"
        "td{padding:7px 14px;border-bottom:1px solid rgba(48,54,61,.35)}"
        "tr:last-child td{border-bottom:none}"
        "tr:hover td{background:rgba(255,255,255,.02)}"
        "svg.equity{width:100%;height:200px;display:block}"
    )


def _equity_svg(positions: list) -> str:
    """Build SVG equity curve from closed positions."""
    closed = sorted(
        [p for p in positions if getattr(p, "close_time", None) is not None],
        key=lambda p: p.close_time,
    )
    if len(closed) < 2:
        return '<p style="padding:16px;color:#8b949e;font-size:.85rem">کمتر از ۲ معامله بسته‌شده برای نمودار</p>'

    equity = [0.0]
    for p in closed:
        equity.append(equity[-1] + float(getattr(p, "pnl_usdt", 0.0)))

    W, H, PX, PY = 900, 190, 8, 10
    mn, mx = min(equity), max(equity)
    if mx == mn:
        mx = mn + 1.0

    def sx(i: int) -> str:
        return f"{PX + i / (len(equity) - 1) * (W - 2 * PX):.1f}"

    def sy(v: float) -> str:
        return f"{PY + (1 - (v - mn) / (mx - mn)) * (H - 2 * PY):.1f}"

    color = "#2ea043" if equity[-1] >= 0 else "#da3633"
    zy = sy(max(mn, 0.0))
    pts = " ".join(f"{sx(i)},{sy(v)}" for i, v in enumerate(equity))
    fill = (
        f"M {sx(0)},{sy(equity[0])} "
        + " ".join(f"L {sx(i)},{sy(v)}" for i, v in enumerate(equity))
        + f" L {sx(len(equity)-1)},{H - PY} L {sx(0)},{H - PY} Z"
    )
    return (
        f'<svg class="equity" viewBox="0 0 {W} {H}" '
        f'xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">'
        f'<defs><linearGradient id="eg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity=".25"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
        f'<path d="{fill}" fill="url(#eg)"/>'
        f'<line x1="{PX}" y1="{zy}" x2="{W-PX}" y2="{zy}" '
        f'stroke="#30363d" stroke-width="1" stroke-dasharray="4,3"/>'
        f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>'
        f'</svg>'
    )


def _ff(v, dec: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{dec}f}"
    except (TypeError, ValueError):
        return str(v)


def _fp(v) -> str:
    """Format percentage."""
    if v is None:
        return "—"
    return f"{float(v):.2f}%"


def _cc(v) -> str:
    """CSS class based on sign."""
    try:
        return "green" if float(v) > 0 else ("red" if float(v) < 0 else "")
    except (TypeError, ValueError):
        return ""


def _trade_rows(positions: list) -> str:
    closed = sorted(
        [p for p in positions if getattr(p, "close_time", None) is not None],
        key=lambda p: p.close_time,
        reverse=True,
    )
    if not closed:
        return (
            '<tr><td colspan="7" style="text-align:center;color:#8b949e;padding:16px">'
            "معامله بسته‌ای وجود ندارد"
            "</td></tr>"
        )

    rows = []
    n = len(closed)
    for i, p in enumerate(closed[:500]):
        side_raw = getattr(p, "side", None)
        side_str = str(side_raw).split(".")[-1] if side_raw is not None else "—"
        side_cls = "green" if "LONG" in side_str.upper() else "red"

        pnl = float(getattr(p, "pnl_usdt", 0.0))
        pnl_cls = _cc(pnl)
        pnl_str = f"{'+'if pnl>0 else ''}{_ff(pnl)}"

        ot = getattr(p, "open_time", None)
        ct = getattr(p, "close_time", None)
        ot_s = ot.strftime("%Y-%m-%d %H:%M") if isinstance(ot, datetime) else "—"
        ct_s = ct.strftime("%Y-%m-%d %H:%M") if isinstance(ct, datetime) else "—"

        rows.append(
            f"<tr>"
            f"<td style='color:#8b949e'>{n - i}</td>"
            f"<td>{_html.escape(str(getattr(p, 'symbol', '?')))}</td>"
            f"<td class='{side_cls}'>{side_str}</td>"
            f"<td>{_ff(getattr(p, 'entry', None))}</td>"
            f"<td style='color:#8b949e'>{ot_s}</td>"
            f"<td style='color:#8b949e'>{ct_s}</td>"
            f"<td class='{pnl_cls}' style='font-weight:600'>{pnl_str}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def generate_html(result: "BacktestResult", title: str = "Backtest Report") -> str:
    """Generate self-contained HTML string from a BacktestResult."""
    r = result
    pos = getattr(r, "positions", [])

    ret = getattr(r, "return_pct", 0.0)       # already in %
    wr  = getattr(r, "win_rate", 0.0) * 100   # 0-1 → %
    pf  = getattr(r, "profit_factor", 0.0)
    rr  = getattr(r, "risk_reward", 0.0)
    pnl = getattr(r, "total_pnl_usdt", 0.0)
    dd  = getattr(r, "max_drawdown_pct", 0.0)

    cards = [
        ("Total Return",   f"{'+'if ret>0 else ''}{_fp(ret)}",  _cc(ret)),
        ("Net P&L (USDT)", f"{'+'if pnl>0 else ''}${_ff(pnl)}", _cc(pnl)),
        ("Win Rate",        f"{_ff(wr, 1)}%",                    "blue"),
        ("Profit Factor",   _ff(pf),                             "yellow"),
        ("Max Drawdown",    f"-{_fp(dd)}",                       "red"),
        ("Risk / Reward",   _ff(rr),                             ""),
    ]

    cards_html = "\n".join(
        f'<div class="card"><div class="card-label">{lbl}</div>'
        f'<div class="card-value {cls}">{val}</div></div>'
        for lbl, val, cls in cards
    )

    stats_left = [
        ("Initial Balance",  f"${_ff(r.initial_balance)}"),
        ("Final Balance",    f"${_ff(r.final_balance)}"),
        ("Total Trades",     str(r.total_trades)),
        ("Winning Trades",   str(r.winning_trades)),
        ("Losing Trades",    str(r.losing_trades)),
        ("Avg Win",          f"+${_ff(getattr(r, 'avg_win', 0))}"),
    ]
    stats_right = [
        ("Gross Profit",     f"+${_ff(r.gross_profit)}"),
        ("Gross Loss",       f"-${_ff(abs(r.gross_loss))}"),
        ("Largest Win",      f"+${_ff(r.largest_win)}"),
        ("Largest Loss",     f"-${_ff(abs(r.largest_loss))}"),
        ("Max DD (USDT)",    f"-${_ff(r.max_drawdown_usdt)}"),
        ("Avg Loss",         f"-${_ff(abs(getattr(r, 'avg_loss', 0)))}"),
    ]

    def stat_rows(items):
        return "".join(
            f'<div class="srow">'
            f'<span class="slabel">{k}</span>'
            f'<span class="sval">{v}</span>'
            f'</div>'
            for k, v in items
        )

    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    n_trades = getattr(r, "total_trades", len(pos))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_html.escape(title)}</title>
<style>{_css()}</style>
</head>
<body>
<h1>{_html.escape(title)}</h1>
<p class="sub">Generated {generated}</p>

<div class="cards">
{cards_html}
</div>

<div class="section">
  <div class="sec-title">Equity Curve</div>
  {_equity_svg(pos)}
</div>

<div class="section">
  <div class="sec-title">Statistics</div>
  <div class="stats-grid">
    <div class="stats-col">{stat_rows(stats_left)}</div>
    <div class="stats-col">{stat_rows(stats_right)}</div>
  </div>
</div>

<div class="section">
  <div class="sec-title">Trade History ({n_trades} trades)</div>
  <div style="overflow-x:auto">
  <table>
    <thead>
      <tr>
        <th>#</th><th>Symbol</th><th>Side</th><th>Entry Price</th>
        <th>Open Time</th><th>Close Time</th><th>PnL (USDT)</th>
      </tr>
    </thead>
    <tbody>
{_trade_rows(pos)}
    </tbody>
  </table>
  </div>
</div>
</body>
</html>"""


def save_report(
    result: "BacktestResult",
    path: str = "backtest_report.html",
    *,
    title: str = "Backtest Report",
) -> str:
    """
    Generate HTML report and save to file.

    پارامترها
    ----------
    result : BacktestResult از Backtest.run()
    path   : مسیر فایل خروجی (پیش‌فرض: backtest_report.html)
    title  : عنوان صفحه HTML

    مثال
    ----
    result = Backtest(MyStrategy).run(source)
    save_report(result, "report.html", title="BTC RSI — 90 Days")
    """
    content = generate_html(result, title=title)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    abs_path = os.path.abspath(path)
    print(f"[report] ✓ {abs_path}")
    return abs_path


__all__ = ["generate_html", "save_report"]
