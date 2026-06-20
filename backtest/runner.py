"""
backtest.runner — the Backtest orchestrator.

Wires Strategy ↔ Exchange ↔ trex_engine into a single run() call.
"""
from __future__ import annotations

import time
from typing import Iterable

from backtest.exchange.exchange import Exchange
from backtest.stats import BacktestResult
from backtest.strategy import Strategy
from trex.base.ohlcv import OHLCV


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
        2. strategy.on_kline()  → user logic runs, orders are placed
        3. exchange.kline()     → limit orders checked, positions updated

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

        # ── 1. Init trex ──────────────────────────────────────────────────
        import trex as _trex
        _trex.init(port=s.port, source_timeframe=s.timeframe)

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
            # a) push to trex → indicators computed → listeners fired
            if s.broadcast:
                try:
                    _trex.push(_ohlcv_to_bar(bar), symbol=s.symbol)
                except Exception:
                    pass

            # b) exchange processes existing limit orders & updates positions
            #    (also sets user.ohlcv so market orders in on_kline get current close)
            exchange.kline(bar)

            # c) strategy logic: places new orders (market → current close, limit → next bar)
            s.on_kline(bar)

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

        # ── 5. Collect results ────────────────────────────────────────────
        return BacktestResult.from_exchange(exchange)
