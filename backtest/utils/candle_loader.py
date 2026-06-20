"""Candle data loaders — CSV, dict-list, and database helpers."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from trex import OHLCV


def _to_ts(value: str | int | float) -> datetime:
    """Convert a Unix ms/s timestamp or ISO string to a tz-aware datetime."""
    try:
        ts = float(value)
        # Heuristic: values > 1e12 are milliseconds
        if ts > 1e12:
            ts /= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, TypeError):
        pass
    return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)


def load_csv(
    path: str | Path,
    symbol: str = "",
    timeframe: str = "1m",
    *,
    time_col: str = "time",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    delimiter: str = ",",
    skip_header: bool = True,
) -> list[OHLCV]:
    """
    Load candles from a CSV file.

    Expected default columns (names are configurable):
        time, open, high, low, close, volume

    The *time* column may be:
      - Unix timestamp in seconds  (e.g. 1704067200)
      - Unix timestamp in ms       (e.g. 1704067200000)
      - ISO-8601 string            (e.g. 2024-01-01T00:00:00)

    Returns a list of OHLCV sorted ascending by time.
    """
    path = Path(path)
    bars: list[OHLCV] = []

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        for row in reader:
            try:
                bar = OHLCV(
                    time=_to_ts(row[time_col]),
                    open=float(row[open_col]),
                    high=float(row[high_col]),
                    low=float(row[low_col]),
                    close=float(row[close_col]),
                    volume=float(row.get(volume_col, 0) or 0),
                    symbol=symbol,
                    str_time=timeframe,
                )
                bars.append(bar)
            except (KeyError, ValueError):
                continue

    bars.sort(key=lambda b: b.time)
    return bars


def load_dicts(
    rows: Iterable[dict],
    symbol: str = "",
    timeframe: str = "1m",
    *,
    time_key: str = "time",
    open_key: str = "open",
    high_key: str = "high",
    low_key: str = "low",
    close_key: str = "close",
    volume_key: str = "volume",
) -> list[OHLCV]:
    """
    Convert a list of dicts (e.g. from pandas .to_dict('records')) into OHLCV.

    Example::

        df = pd.read_csv("btc.csv")
        candles = load_dicts(df.to_dict("records"), symbol="BTCUSDT")
    """
    bars: list[OHLCV] = []
    for row in rows:
        try:
            bar = OHLCV(
                time=_to_ts(row[time_key]),
                open=float(row[open_key]),
                high=float(row[high_key]),
                low=float(row[low_key]),
                close=float(row[close_key]),
                volume=float(row.get(volume_key, 0) or 0),
                symbol=symbol,
                str_time=timeframe,
            )
            bars.append(bar)
        except (KeyError, ValueError):
            continue
    bars.sort(key=lambda b: b.time)
    return bars


def load_lists(
    rows: Iterable[list | tuple],
    symbol: str = "",
    timeframe: str = "1m",
    order: tuple[str, ...] = ("time", "open", "high", "low", "close", "volume"),
) -> list[OHLCV]:
    """
    Convert raw list/tuple rows into OHLCV.

    *order* describes which index maps to which field.
    Default: [time, open, high, low, close, volume]
    """
    idx = {k: i for i, k in enumerate(order)}
    bars: list[OHLCV] = []
    for row in rows:
        try:
            bar = OHLCV(
                time=_to_ts(row[idx["time"]]),
                open=float(row[idx["open"]]),
                high=float(row[idx["high"]]),
                low=float(row[idx["low"]]),
                close=float(row[idx["close"]]),
                volume=float(row[idx.get("volume", -1)]) if "volume" in idx else 0.0,
                symbol=symbol,
                str_time=timeframe,
            )
            bars.append(bar)
        except (IndexError, ValueError):
            continue
    bars.sort(key=lambda b: b.time)
    return bars
