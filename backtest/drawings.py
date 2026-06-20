"""
backtest.drawings — automatic chart drawing for trades and orders.

When Strategy.broadcast is True, every position open/close and every
limit order place/cancel is automatically reflected as a drawing in the
connected TrexTerminal chart — no extra code needed from the user.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Union

from backtest.exchange.dataclass.classdata import (
    Order, PositionIsolate, PositionCross,
)
from backtest.exchange.dataclass.enums import Side

# ── colours ──────────────────────────────────────────────────────────────────
_LONG_COLOR  = "#26a69a"   # teal  — standard long green
_SHORT_COLOR = "#ef5350"   # red   — standard short red
_ORDER_COLOR = "#f59e0b"   # amber — pending limit order


def _ts(dt: datetime | None) -> int:
    """datetime → unix seconds (int). Falls back to now if None."""
    if dt is None:
        return int(datetime.now(tz=timezone.utc).timestamp())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return abs(numerator / denominator) * 100


# ── position drawings ─────────────────────────────────────────────────────────

def position_open_drawing(
    pos: Union[PositionIsolate, PositionCross],
    bar_interval_sec: int = 60,
) -> dict:
    """
    Build a ``longPosition`` / ``shortPosition`` drawing for an open position.

    The right edge of the box is set to entry_time + 30 bars so the box is
    visible immediately on the chart even before the position closes.
    """
    long  = pos.side == Side.LONG
    color = _LONG_COLOR if long else _SHORT_COLOR
    t0    = _ts(pos.open_time)
    t1    = t0 + bar_interval_sec * 30          # extend 30 bars to the right

    sl = pos.stop_price   or (pos.entry * (0.98 if long else 1.02))
    tp = pos.take_profit  or (pos.entry * (1.04 if long else 0.96))

    risk   = _pct(abs(pos.entry - sl), pos.entry)
    reward = _pct(abs(pos.entry - tp), pos.entry)

    return {
        "id":        f"pos_{pos.id}",
        "tool":      "longPosition" if long else "shortPosition",
        "points":    [
            {"time": t0, "price": pos.entry},
            {"time": t1, "price": pos.entry},
        ],
        "style":     {
            "color":       color,
            "lineWidth":   1,
            "fillColor":   color,
            "fillOpacity": 0.12,
            "showLabels":  True,
        },
        "paneId":    "main",
        "locked":    True,
        "visible":   True,
        "completed": True,
        "selected":  False,
        "origin":    "server",
        "positionData": {
            "entryPrice": pos.entry,
            "stopLoss":   sl,
            "takeProfit": tp,
            "quantity":   pos.margin,
            "risk":       round(risk,   2),
            "reward":     round(reward, 2),
        },
    }


def position_close_drawing(
    pos: Union[PositionIsolate, PositionCross],
    bar_interval_sec: int = 60,
) -> dict:
    """
    Update a position drawing when it is closed / triggered / stopped.

    The right edge is moved to close_time; colour darkens on loss.
    """
    long      = pos.side == Side.LONG
    profit    = pos.pnl_usdt >= 0
    color     = (_LONG_COLOR if long else _SHORT_COLOR) if profit else "#9e9e9e"
    t0        = _ts(pos.open_time)
    t1        = _ts(pos.close_time) if pos.close_time else t0 + bar_interval_sec

    # exit price: use whatever price produced the final pnl
    if long:
        exit_p = pos.entry * (1 + pos.pnl / pos.leverage) if pos.leverage else pos.entry
    else:
        exit_p = pos.entry * (1 - pos.pnl / pos.leverage) if pos.leverage else pos.entry

    sl = pos.stop_price  or (pos.entry * (0.98 if long else 1.02))
    tp = pos.take_profit or (pos.entry * (1.04 if long else 0.96))

    risk   = _pct(abs(pos.entry - sl), pos.entry)
    reward = _pct(abs(pos.entry - tp), pos.entry)

    pnl_sign = "+" if profit else ""
    label    = f"{pnl_sign}{pos.pnl_usdt:.2f} USDT"

    return {
        "id":        f"pos_{pos.id}",
        "tool":      "longPosition" if long else "shortPosition",
        "points":    [
            {"time": t0, "price": pos.entry},
            {"time": t1, "price": exit_p},
        ],
        "style":     {
            "color":       color,
            "lineWidth":   1,
            "fillColor":   color,
            "fillOpacity": 0.08,
            "showLabels":  True,
        },
        "text":      label,
        "paneId":    "main",
        "locked":    True,
        "visible":   True,
        "completed": True,
        "selected":  False,
        "origin":    "server",
        "positionData": {
            "entryPrice": pos.entry,
            "stopLoss":   sl,
            "takeProfit": tp,
            "quantity":   pos.margin,
            "risk":       round(risk,   2),
            "reward":     round(reward, 2),
        },
    }


# ── order drawings ────────────────────────────────────────────────────────────

def order_drawing(order: Order) -> dict:
    """Horizontal price line for a pending limit order."""
    long  = order.side == Side.LONG
    color = _LONG_COLOR if long else _SHORT_COLOR
    t     = _ts(order.placed_time)

    return {
        "id":        f"order_{order.id}",
        "tool":      "horizontal",
        "points":    [{"time": t, "price": order.entry}],
        "style":     {
            "color":      _ORDER_COLOR,
            "lineWidth":  1,
            "lineStyle":  2,       # dashed
            "showLabels": True,
        },
        "text":      f"{'LONG' if long else 'SHORT'} limit @ {order.entry:.4f}  {order.usdt:.0f} USDT",
        "paneId":    "main",
        "locked":    True,
        "visible":   True,
        "completed": True,
        "selected":  False,
        "origin":    "server",
    }
