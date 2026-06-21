"""
backtest.runner — the Backtest orchestrator.

Wires Strategy ↔ Exchange ↔ trex_engine into a single run() call.
"""
from __future__ import annotations

import time
from typing import Iterable

from backtest.exchange.exchange import Exchange
from backtest.playback import PlaybackController
from backtest.stats import BacktestResult
from backtest.strategy import Strategy
from trex.base.ohlcv import OHLCV

# Max real-time interval between bt_state/bt_progress broadcasts (seconds).
# At max speed (speed=0) this caps broadcasts at ~10 fps to avoid flooding.
_BROADCAST_INTERVAL = 0.1


_TF_SECONDS: dict[str, int] = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "8h": 28800,
    "12h": 43200, "1d": 86400, "3d": 259200, "1w": 604800,
}

def _tf_to_seconds(tf: str) -> int:
    return _TF_SECONDS.get(tf, 60)


def _ohlcv_to_bar(ohlcv: OHLCV):
    """Convert an OHLCV candle to a trex Bar for broadcasting."""
    from trex.domain.types import Bar
    return Bar(
        time=int(ohlcv.time.timestamp()),
        open=ohlcv.open,
        high=ohlcv.high,
        low=ohlcv.low,
        close=ohlcv.close,
        volume=ohlcv.volume or 0.0,
    )


def _fmt_time(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M") if dt is not None else None


def _build_bt_state(s, bar) -> dict:
    """Serialize live exchange state for the TrexTerminal bottom panel."""
    exchange = s._exchange
    user_id  = s._user_id
    if exchange is None or user_id is None:
        return {"type": "bt_state"}

    positions = exchange.get_positions(symbol=s.symbol, user_id=user_id)
    orders    = exchange.get_orders(user_id, s.symbol)
    balance   = exchange.get_balance(user_id)
    history   = exchange.get_history_positions(symbol=s.symbol, user_id=user_id, limit=200)

    mark = bar.close

    def _pos(p):
        pnl_pct = round(p.pnl * p.leverage * 100, 2) if p.pnl else 0.0
        return {
            "id":          p.id,
            "symbol":      p.symbol,
            "side":        p.side.value,
            "entry":       p.entry,
            "mark":        mark,
            "margin":      p.margin,
            "leverage":    p.leverage,
            "pnl":         round(p.pnl, 6) if p.pnl else 0.0,
            "pnl_usdt":    round(p.pnl_usdt, 4) if p.pnl_usdt else 0.0,
            "pnl_pct":     pnl_pct,
            "stop_price":  p.stop_price,
            "take_profit": p.take_profit,
            "liquidy":     getattr(p, "liquidy", None),
            "open_time":   _fmt_time(p.open_time),
            "bars":        p.bars,
        }

    def _order(o):
        return {
            "id":          o.id,
            "symbol":      o.symbol,
            "side":        o.side.value,
            "type":        o.order_type.value,
            "entry":       o.entry,
            "usdt":        o.usdt,
            "stop_price":  o.stop_price,
            "take_profit": o.take_profit,
            "placed_time": _fmt_time(o.placed_time),
        }

    def _hist(p):
        pnl_pct = round(p.pnl * p.leverage * 100, 2) if p.pnl else 0.0
        return {
            "id":          p.id,
            "symbol":      p.symbol,
            "side":        p.side.value,
            "entry":       p.entry,
            "margin":      p.margin,
            "leverage":    p.leverage,
            "pnl_usdt":    round(p.pnl_usdt, 4) if p.pnl_usdt else 0.0,
            "pnl_pct":     pnl_pct,
            "state":       p.state.value,
            "open_time":   _fmt_time(p.open_time),
            "close_time":  _fmt_time(p.close_time),
        }

    margin_used = sum(p.margin or 0 for p in positions)
    unrealized  = sum(p.pnl_usdt or 0 for p in positions)

    return {
        "type":             "bt_state",
        "balance":          round(balance, 4),
        "margin_used":      round(margin_used, 4),
        "unrealized_pnl":   round(unrealized, 4),
        "equity":           round(balance + margin_used + unrealized, 4),
        "positions":        [_pos(p)    for p in positions],
        "orders":           [_order(o)  for o in orders],
        "trade_history":    [_hist(p)   for p in history],
    }


def _build_bt_result(result: BacktestResult) -> dict:
    """Serialize BacktestResult for the TrexTerminal Results tab."""
    equity = result.initial_balance
    equity_curve: list[float] = []
    for pos in result.positions:
        equity += pos.pnl_usdt or 0
        equity_curve.append(round(equity, 2))

    pf = result.profit_factor
    if pf == float("inf"):
        pf = 9999.0

    return {
        "type":             "bt_result",
        "initial_balance":  round(result.initial_balance, 2),
        "final_balance":    round(result.final_balance, 2),
        "return_pct":       round(result.return_pct, 2),
        "total_trades":     result.total_trades,
        "winning_trades":   result.winning_trades,
        "losing_trades":    result.losing_trades,
        "win_rate":         round(result.win_rate * 100, 1),
        "profit_factor":    round(pf, 2),
        "risk_reward":      round(result.risk_reward, 2),
        "total_pnl_usdt":   round(result.total_pnl_usdt, 2),
        "gross_profit":     round(result.gross_profit, 2),
        "gross_loss":       round(result.gross_loss, 2),
        "largest_win":      round(result.largest_win, 2),
        "largest_loss":     round(result.largest_loss, 2),
        "avg_win":          round(result.avg_win, 2),
        "avg_loss":         round(result.avg_loss, 2),
        "max_drawdown_usdt":round(result.max_drawdown_usdt, 2),
        "max_drawdown_pct": round(result.max_drawdown_pct, 2),
        "equity_curve":     equity_curve,
    }


class Backtest:
    """
    Run a strategy against historical candles.

    Usage::

        result = Backtest(MyStrategy).run(candles)
        print(result)

    You can also override strategy config at runtime::

        result = Backtest(MyStrategy, deposit=50_000, leverage=5).run(candles)

    Parameters
    ----------
    strategy:
        A Strategy subclass (or an already-instantiated object).
    **overrides:
        Any Strategy class attribute can be overridden here
        (symbol, timeframe, deposit, leverage, fee, slippage, broadcast, port).
    """

    def __init__(
        self,
        strategy: type | Strategy,
        **overrides,
    ):
        # Instantiate from class if needed
        if isinstance(strategy, type):
            if not issubclass(strategy, Strategy):
                raise TypeError(f"{strategy} must be a subclass of Strategy")
            instance = strategy.__new__(strategy)
            instance.__init__()
        else:
            instance = strategy

        # Apply runtime overrides
        for key, val in overrides.items():
            if not hasattr(instance, key):
                raise AttributeError(f"Strategy has no attribute '{key}'")
            setattr(instance, key, val)

        self._strategy: Strategy = instance

    # ─────────────────────────────────────────────────────────────────────

    def run(
        self,
        candles: Iterable[OHLCV],
        *,
        progress: bool = True,
    ) -> BacktestResult:
        """
        Feed all candles through the strategy and return statistics.

        Per-bar execution order
        -----------------------
        1. trex.push(bar)       → indicators recomputed, listeners called
        2. exchange.kline(bar)  → limit orders checked, positions updated
        3. strategy.on_kline()  → user logic runs, orders are placed

        This means market orders placed in on_kline() execute at the
        *current* bar's close price (realistic for EOB strategies).
        Limit orders placed in on_kline() are evaluated from the *next* bar.

        Parameters
        ----------
        candles:
            An iterable of OHLCV bars. Use load_csv() / load_dicts() helpers.
        progress:
            Print progress every 10 000 bars (default True).

        Returns
        -------
        BacktestResult with win rate, profit factor, drawdown, etc.
        """
        s = self._strategy
        candles = list(candles)
        total = len(candles)

        if total == 0:
            raise ValueError("Candle list is empty.")

        t0 = time.perf_counter()
        _last_broadcast = 0.0          # monotonic clock of last bt_state broadcast

        # ── 1. Init trex ──────────────────────────────────────────────────
        import trex as _trex
        if _trex.ctx.initialized:
            _trex.ctx.reset()
        _trex.init(port=s.port, source_timeframe=s.timeframe)

        # ── 1b. Playback controller (only when broadcasting) ──────────────
        ctrl: PlaybackController | None = None
        if s.broadcast:
            ctrl = PlaybackController(speed=s.replay_speed)
            _trex.set_playback_controller(ctrl)
            # Clear any drawings from a previous backtest run
            try:
                _trex.broadcast_raw({"type": "drawings_clear"})
            except Exception:
                pass

        # ── 2. Register indicators ────────────────────────────────────────
        s.indicators()

        # ── 3. Build exchange ─────────────────────────────────────────────
        exchange = Exchange(
            symbols=[s.symbol],
            taker_fee=s.fee,
            slippage=s.slippage,
        )
        user_id = exchange.sing_up(s)
        exchange.deposit(user_id, s.deposit)
        exchange.change_leverage(s.symbol, user_id, s.leverage)

        s._exchange = exchange
        s._user_id  = user_id
        s._bar_interval_sec = _tf_to_seconds(s.timeframe)

        # ── 4. Candle loop ────────────────────────────────────────────────
        if progress:
            print(
                f"[backtest] Starting — {total:,} bars | "
                f"symbol={s.symbol} tf={s.timeframe} "
                f"deposit=${s.deposit:,.0f} lev={s.leverage}x "
                f"fee={s.fee*100:.2f}%"
            )

        for i, bar in enumerate(candles):
            # a) push to trex → indicators recomputed → listeners fired
            #    Always push regardless of broadcast — indicators must run even when
            #    the chart stream is disabled.
            try:
                _trex.push(_ohlcv_to_bar(bar), symbol=s.symbol)
            except Exception:
                pass

            # b) exchange processes existing limit orders & updates positions
            #    (also sets user.ohlcv so market orders in on_kline get current close)
            exchange.kline(bar)

            # c) strategy logic: places new orders (market → current close, limit → next bar)
            s.on_kline(bar)

            # d) broadcast live state + progress to TrexTerminal (throttled)
            if s.broadcast:
                now = time.monotonic()
                if now - _last_broadcast >= _BROADCAST_INTERVAL:
                    _last_broadcast = now
                    try:
                        _trex.broadcast_raw({
                            "type":    "bt_progress",
                            "current": i + 1,
                            "total":   total,
                            "pct":     round((i + 1) / total * 100, 1),
                        })
                        _trex.broadcast_raw(_build_bt_state(s, bar))
                    except Exception:
                        pass

            # e) playback delay — honors pause/speed from TrexTerminal
            if ctrl is not None:
                ctrl.wait(_tf_to_seconds(s.timeframe))

            if progress and total >= 10_000 and (i + 1) % 10_000 == 0:
                pct = (i + 1) / total * 100
                elapsed = time.perf_counter() - t0
                eta = elapsed / (i + 1) * (total - i - 1)
                print(
                    f"[backtest] {i+1:,}/{total:,} ({pct:.1f}%) "
                    f"elapsed={elapsed:.0f}s  ETA≈{eta:.0f}s"
                )

        elapsed = time.perf_counter() - t0

        if progress:
            print(f"[backtest] Done — {total:,} bars in {elapsed:.1f}s")

        # ── 5. Stop playback controller and notify clients ────────────────
        if ctrl is not None:
            ctrl.stop()
            _trex.set_playback_controller(None)

        # ── 6. Collect results ────────────────────────────────────────────
        result = BacktestResult.from_exchange(exchange)

        # ── 7. Broadcast final state + results to TrexTerminal ───────────
        if s.broadcast:
            try:
                _trex.broadcast_raw({
                    "type": "bt_progress", "current": total, "total": total, "pct": 100.0,
                })
                _trex.broadcast_raw(_build_bt_state(s, candles[-1]))
                _trex.broadcast_raw(_build_bt_result(result))
            except Exception:
                pass

        return result
