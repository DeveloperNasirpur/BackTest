"""
backtest.utils.postgres_loader — load historical OHLCV candles from PostgreSQL.

Uses the same psycopg2 connection approach as Trex_engin's CandleSourcePostgres
but returns a plain list[OHLCV] suitable for Backtest.run(candles).

Table naming convention (TrexStore compatible):
    symbol="BTCUSDT", timeframe="1m"  →  table "BTCUSDT1M"
    symbol="ETHUSDT",  timeframe="4h"  →  table "ETHUSDT4H"
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from trex.base.ohlcv import OHLCV


_TF_MAP: dict[str, str] = {
    "1m": "1M", "3m": "3M", "5m": "5M", "15m": "15M", "30m": "30M",
    "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H",  "8h": "8H", "12h": "12H",
    "1d": "1D", "3d": "3D", "1w": "1W",
}


def _table_name(symbol: str, timeframe: str) -> str:
    suffix = _TF_MAP.get(timeframe, timeframe.upper())
    return f"{symbol.upper()}{suffix}"


def _row_to_ohlcv(row: tuple, timeframe: str) -> OHLCV:
    ts    = float(row[0]) / 1000.0
    open_ = float(row[1])
    high  = float(row[2])
    low   = float(row[3])
    close = float(row[4])
    vol   = float(row[5]) if row[5] is not None else None
    sym   = str(row[6]) if len(row) > 6 else ""
    return OHLCV(
        open=open_, high=high, low=low, close=close,
        volume=vol,
        time=datetime.fromtimestamp(ts, tz=timezone.utc),
        side=0 if open_ > close else 1,
        timeframe=1,
        str_time=timeframe,
        symbol=sym,
    )


def load_postgres(
    symbol:    str,
    timeframe: str,
    *,
    host:      str = "localhost",
    port:      int = 5432,
    user:      str = "postgres",
    password:  str = "",
    database:  str = "okx",
    table:     Optional[str] = None,
    start:     Optional[datetime] = None,
    end:       Optional[datetime] = None,
    limit:     Optional[int] = None,
) -> list[OHLCV]:
    """
    Load OHLCV candles from PostgreSQL and return as a list.

    Parameters
    ----------
    symbol:
        Trading pair, e.g. ``"BTCUSDT"``.
    timeframe:
        Candle interval, e.g. ``"1m"``, ``"4h"``, ``"1d"``.
    host / port / user / password / database:
        PostgreSQL connection parameters.
    table:
        Override the auto-derived table name. Default derives from
        symbol+timeframe following TrexStore convention (``"BTCUSDT1M"``).
    start / end:
        Optional datetime filters (timezone-aware or naive UTC).
    limit:
        Maximum number of candles to return (most recent if end is set,
        oldest first otherwise).

    Returns
    -------
    list[OHLCV]
        Ready to pass to ``Backtest(MyStrategy).run(candles)``.

    Raises
    ------
    ImportError
        If psycopg2 is not installed.
    """
    try:
        import psycopg2
    except ImportError as exc:
        raise ImportError(
            "psycopg2 not installed. Run: pip install psycopg2-binary"
        ) from exc

    tbl = table or _table_name(symbol, timeframe)

    # Build WHERE clause
    conditions: list[str] = []
    params: list[object] = []

    def _to_ms(dt: datetime) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

    if start is not None:
        conditions.append("open_time >= %s")
        params.append(_to_ms(start))
    if end is not None:
        conditions.append("open_time <= %s")
        params.append(_to_ms(end))

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    lim   = f"LIMIT {int(limit)}" if limit else ""

    sql = (
        f'SELECT open_time, open, high, low, close, volume, symbol '
        f'FROM "{tbl}" {where} ORDER BY open_time ASC {lim}'
    ).strip()

    candles: list[OHLCV] = []
    conn_params = {
        "host": host, "port": port,
        "user": user, "password": password,
        "dbname": database,
    }

    with psycopg2.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or None)
            while True:
                rows = cur.fetchmany(5000)
                if not rows:
                    break
                for row in rows:
                    candles.append(_row_to_ohlcv(row, timeframe))

    return candles


__all__ = ["load_postgres"]
