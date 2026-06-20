"""
backtest.utils.demo — synthetic candle generator for quick experimentation.

No real data needed. Call demo_candles() to get a realistic-looking price
series you can feed straight into Backtest.run().
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from trex.base.ohlcv import OHLCV


def demo_candles(
    symbol: str = "BTCUSDT",
    timeframe: str = "1m",
    bars: int = 2_000,
    start_price: float = 42_000.0,
    volatility: float = 0.003,   # ~0.3 % per bar (realistic for 1m BTC)
    trend: float = 0.0001,       # slight upward drift per bar
    seed: int | None = 42,
) -> list[OHLCV]:
    """
    Generate a list of synthetic OHLCV candles using Geometric Brownian Motion.

    Parameters
    ----------
    symbol:
        Symbol name embedded in each bar (used by the exchange for routing).
    timeframe:
        Timeframe string, e.g. ``"1m"``, ``"5m"``, ``"1h"``.
    bars:
        Number of candles to generate.
    start_price:
        Opening price of the first candle.
    volatility:
        Standard deviation of log-returns per bar.
        Default 0.003 mimics ~0.3% BTC 1-minute volatility.
    trend:
        Drift per bar (positive = uptrend). Keep small (< 0.001).
    seed:
        Random seed for reproducibility. Pass ``None`` for random output.

    Returns
    -------
    list[OHLCV] — sorted ascending, ready for ``Backtest.run()``.

    Example
    -------
    ::

        from backtest import Backtest, demo_candles
        from strategies.rsi_strategy import RSIStrategy

        candles = demo_candles(bars=5_000)
        result  = Backtest(RSIStrategy).run(candles)
        print(result)
    """
    _TF_SECS = {
        "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600,
        "8h": 28800, "12h": 43200, "1d": 86400,
    }
    bar_sec  = _TF_SECS.get(timeframe, 60)
    rng      = random.Random(seed)
    now_ts   = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())

    candles: list[OHLCV] = []
    price = start_price

    for i in range(bars):
        # GBM step
        ret   = trend + volatility * rng.gauss(0, 1)
        close = max(price * math.exp(ret), 0.01)

        # realistic OHLC from open/close
        lo, hi = min(price, close), max(price, close)
        wick   = abs(close - price) * rng.uniform(0.1, 0.6)
        low    = max(lo - wick, 0.01)
        high   = hi + wick
        vol    = abs(close - price) / price * rng.uniform(500, 5000)

        ts = datetime.fromtimestamp(now_ts + i * bar_sec, tz=timezone.utc)
        candles.append(OHLCV(
            open=round(price, 4), high=round(high, 4),
            low=round(low, 4),   close=round(close, 4),
            volume=round(vol, 2),
            time=ts, symbol=symbol, str_time=timeframe,
        ))
        price = close

    return candles
