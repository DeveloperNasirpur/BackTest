"""
backtest.utils.binance_loader
==============================
دانلود تاریخچه کندل از Binance Public API — بدون نیاز به API Key.

استفاده:
    from backtest import load_binance

    bars = load_binance("BTCUSDT", "1h", days=90)
    result = Backtest(MyStrategy).run(bars)
"""
from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trex.base.ohlcv import OHLCV

_BINANCE_URL = "https://api.binance.com/api/v3/klines"
_LIMIT = 1000  # max per request


def _tf_to_ms(timeframe: str) -> int:
    """تبدیل timeframe به میلی‌ثانیه."""
    _map = {
        "1m": 60_000, "3m": 180_000, "5m": 300_000,
        "15m": 900_000, "30m": 1_800_000,
        "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
        "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000,
        "1d": 86_400_000, "3d": 259_200_000,
        "1w": 604_800_000, "1M": 2_592_000_000,
    }
    if timeframe not in _map:
        raise ValueError(f"Timeframe نامعتبر: {timeframe}. مقادیر مجاز: {list(_map)}")
    return _map[timeframe]


def load_binance(
    symbol: str,
    timeframe: str = "1h",
    *,
    days: int | None = None,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
    limit: int | None = None,
) -> list["OHLCV"]:
    """
    دانلود کندل از Binance.

    پارامترها
    ----------
    symbol     : نماد — مثال "BTCUSDT"، "ETHUSDT"
    timeframe  : بازه زمانی — "1m"، "5m"، "15m"، "1h"، "4h"، "1d"، ...
    days       : تعداد روزهای گذشته که می‌خواهید (اگر start/end ندادید)
    start      : تاریخ شروع — رشته ISO مثل "2024-01-01" یا datetime
    end        : تاریخ پایان — رشته ISO یا datetime (پیش‌فرض: همین لحظه)
    limit      : حداکثر تعداد کندل (فقط با days کار می‌کند)

    مثال‌ها
    --------
    bars = load_binance("BTCUSDT", "1h", days=30)
    bars = load_binance("ETHUSDT", "4h", start="2024-01-01", end="2024-06-01")
    bars = load_binance("BTCUSDT", "1d", limit=200)
    """
    try:
        import urllib.request
        import json as _json
    except ImportError as e:
        raise ImportError("urllib.request در stdlib پایتون وجود دارد — این خطا نباید رخ دهد") from e

    from trex.base.ohlcv import OHLCV

    tf_ms = _tf_to_ms(timeframe)
    now_ms = int(time.time() * 1000)

    # محاسبه بازه زمانی
    if start is not None:
        start_ms = _parse_dt(start)
        end_ms   = _parse_dt(end) if end else now_ms
    elif days is not None:
        end_ms   = now_ms
        start_ms = end_ms - days * 86_400_000
        if limit is not None:
            # محدود به آخرین `limit` کندل
            start_ms = max(start_ms, end_ms - limit * tf_ms)
    elif limit is not None:
        end_ms   = now_ms
        start_ms = end_ms - limit * tf_ms
    else:
        raise ValueError("حداقل یکی از: days، start، یا limit باید داده شود")

    print(f"[binance] دانلود {symbol} {timeframe} از "
          f"{datetime.fromtimestamp(start_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')} "
          f"تا {datetime.fromtimestamp(end_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')} ...")

    bars: list[OHLCV] = []
    cursor = start_ms

    while cursor < end_ms:
        batch_end = min(cursor + _LIMIT * tf_ms, end_ms)
        url = (
            f"{_BINANCE_URL}?symbol={symbol.upper()}"
            f"&interval={timeframe}"
            f"&startTime={cursor}"
            f"&endTime={batch_end}"
            f"&limit={_LIMIT}"
        )

        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                rows = _json.loads(resp.read())
        except Exception as exc:
            raise ConnectionError(
                f"خطا در دانلود از Binance: {exc}\n"
                "اینترنت را بررسی کنید یا کمی بعد دوباره امتحان کنید."
            ) from exc

        if not rows:
            break

        for row in rows:
            open_ts = int(row[0])
            o = float(row[1])
            h = float(row[2])
            l = float(row[3])
            c = float(row[4])
            v = float(row[5])
            dt = datetime.fromtimestamp(open_ts / 1000, tz=timezone.utc)

            bars.append(OHLCV(
                open=o, high=h, low=l, close=c, volume=v,
                time=dt,
                side=0 if o >= c else 1,
                timeframe=tf_ms // 60_000,
                str_time=timeframe,
                symbol=symbol.upper(),
            ))

        last_ts = int(rows[-1][0])
        cursor = last_ts + tf_ms

        # rate limiting — Binance اجازه می‌دهد تا 1200 req/min
        time.sleep(0.1)

    if not bars:
        raise ValueError(
            f"هیچ داده‌ای برای {symbol} {timeframe} در بازه مشخص‌شده پیدا نشد.\n"
            "نماد یا بازه زمانی را بررسی کنید."
        )

    # حذف تکراری و مرتب‌سازی
    seen: set[int] = set()
    unique = []
    for b in bars:
        ts = int(b.time.timestamp() * 1000)
        if ts not in seen:
            seen.add(ts)
            unique.append(b)
    unique.sort(key=lambda b: b.time)

    print(f"[binance] {len(unique)} کندل دانلود شد.")
    return unique


def _parse_dt(value: str | datetime) -> int:
    """تبدیل رشته یا datetime به unix milliseconds."""
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(
        f"فرمت تاریخ نامعتبر: '{value}'. "
        "فرمت‌های مجاز: 'YYYY-MM-DD'، 'YYYY-MM-DD HH:MM'، 'YYYY-MM-DD HH:MM:SS'"
    )


__all__ = ["load_binance"]
