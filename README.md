# BackTest

**Professional backtesting engine for Python — write a strategy in 20 lines, get a full P&L report, and stream every trade live to your chart.**

Powered by [Trex Engine](https://github.com/DeveloperNasirpur/Trex_engin) for indicators and [TrexTerminal](https://github.com/DeveloperNasirpur/TrexTerminal) for live visualization.

---

## Quick Start

```bash
pip install -e .
```

```python
import trex
from backtest import Backtest, Strategy, demo_candles

class MyStrategy(Strategy):
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0
    leverage  = 5

    def indicators(self):
        trex.rsi(self.symbol, self.timeframe, period=14, listener=self._on_rsi)

    def _on_rsi(self, v):
        self._rsi = v

    def on_kline(self, ohlcv):
        rsi = getattr(self, "_rsi", None)
        if rsi is None:
            return
        if rsi < 30 and not self.positions:
            self.buy(usdt=200, sl=ohlcv.close * 0.985, tp=ohlcv.close * 1.03)
        elif rsi > 70 and not self.positions:
            self.sell(usdt=200, sl=ohlcv.close * 1.015, tp=ohlcv.close * 0.97)

candles = demo_candles(bars=5_000, seed=42)
result  = Backtest(MyStrategy).run(candles)
print(result)
```

```
────────────────────────────────────────────────
  BACKTEST RESULTS
────────────────────────────────────────────────
  Initial balance  :      $10,000.00
  Final balance    :      $11,243.60
  Return           :          +12.44%
────────────────────────────────────────────────
  Total trades     : 87
  Wins / Losses    : 51 / 36
  Win rate         : 58.6%
  Profit factor    : 1.82
  Risk / Reward    : 1.23
────────────────────────────────────────────────
  Total P&L        :       +$1,243.60
  Gross profit     :       $2,468.30
  Gross loss       :      -$1,224.70
  Largest win      :         +$312.00
  Largest loss     :          -$89.50
  Avg win          :          +$48.40
  Avg loss         :          -$34.02
────────────────────────────────────────────────
  Max drawdown     :        -$620.40  (-6.2%)
────────────────────────────────────────────────
```

---

## Table of Contents

- [Strategy API](#strategy-api)
- [Candle Data](#candle-data)
- [Running a Backtest](#running-a-backtest)
- [Live Chart Integration](#live-chart-integration)
- [Backtest Results](#backtest-results)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Requirements](#requirements)

---

## Strategy API

### Configuration

```python
class MyStrategy(Strategy):
    symbol       = "BTCUSDT"   # trading pair
    timeframe    = "1m"        # candle interval
    deposit      = 10_000.0    # starting USDT
    leverage     = 5           # position leverage
    fee          = 0.0004      # 0.04% taker fee  (Binance/OKX default)
    slippage     = 0.0001      # 0.01% market-order slippage
    broadcast    = False       # True → stream bars and trades to TrexTerminal
    port         = 8765        # TrexTerminal WebSocket port
    replay_speed = 0.0         # 0 = max speed, 1.0 = 1 bar/s, 60 = realtime 1m
```

### Required methods

| Method | When called |
|--------|-------------|
| `indicators(self)` | Once before the candle loop. Register trex indicators here. |
| `on_kline(self, ohlcv)` | Once per bar, after all indicators are updated. |

### Trading commands

```python
# Open positions
self.buy(usdt=300)                                         # market long
self.buy(usdt=300, sl=41_000, tp=43_500)                  # with SL / TP
self.buy(usdt=300, price=42_000, sl=41_000, tp=43_500)    # limit long

self.sell(usdt=300, sl=43_000, tp=40_500)                 # market short
self.sell(usdt=300, price=43_000, sl=44_000, tp=41_000)   # limit short

# Close
self.close()                     # close ALL open positions (market)
self.close(position_id=42)       # close one specific position

# Modify
self.set_sl_tp(position_id, sl=41_500, tp=44_000)

# Orders
self.cancel(order_id)            # cancel a pending limit order
self.set_leverage(10)            # change leverage mid-strategy
```

### Properties

```python
self.balance    # float  — available USDT
self.positions  # list   — open positions
self.orders     # list   — pending limit orders
self.history    # list   — all closed positions
```

### Event callbacks (optional)

```python
def on_position_opened(self, pos):       ...   # called when a position opens
def on_position_closed(self, pos):       ...   # manual close
def on_position_profit(self, pos):       ...   # take-profit hit
def on_position_loss(self, pos):         ...   # stop-loss hit
def on_position_liquidated(self, pos):   ...
def on_order_placed(self, order):        ...
def on_order_cancelled(self, order):     ...
```

### Position and Order fields

```python
# Position
pos.id            # int
pos.side          # Side.LONG | Side.SHORT
pos.entry         # float  — entry price
pos.stop_price    # float | None
pos.take_profit   # float | None
pos.margin        # float  — USDT locked as collateral
pos.leverage      # int
pos.pnl           # float  — fractional P&L ((exit-entry)/entry)
pos.pnl_usdt      # float  — realized P&L in USDT (set on close)
pos.open_time     # datetime
pos.close_time    # datetime | None
pos.bars          # int  — number of bars the position was open

# Order
order.id
order.side        # Side.LONG | Side.SHORT
order.order_type  # OrderType.LIMIT | OrderType.MARKET
order.entry       # float  — limit price
order.usdt        # float  — order size
order.placed_time # datetime
```

---

## Candle Data

### Synthetic data (demo / CI)

```python
from backtest import demo_candles

candles = demo_candles(
    bars        = 5_000,
    symbol      = "BTCUSDT",
    timeframe   = "1m",
    start_price = 42_000,
    volatility  = 0.003,    # ~0.3% per bar
    trend       = 0.0001,   # slight upward drift
    seed        = 42,       # reproducible
)
```

### Load from CSV

```python
from backtest import load_csv

candles = load_csv(
    "data/BTCUSDT_1m.csv",
    symbol    = "BTCUSDT",
    timeframe = "1m",
    # column name overrides (optional):
    time_col  = "open_time",
    open_col  = "open",
    high_col  = "high",
    low_col   = "low",
    close_col = "close",
    vol_col   = "volume",
)
```

Timestamp formats auto-detected: Unix ms, Unix seconds, or ISO 8601.

### Load from dicts / DataFrame

```python
from backtest import load_dicts
import pandas as pd

df      = pd.read_parquet("data/btc.parquet")
candles = load_dicts(df.to_dict("records"), symbol="BTCUSDT", timeframe="1h")
```

### Load from PostgreSQL

Reads directly from the table format used by [Trex Engine](https://github.com/DeveloperNasirpur/Trex_engin)'s `TrexStore`. Table name is derived automatically: `symbol="BTCUSDT"` + `timeframe="1m"` → table `"BTCUSDT1M"`.

```python
from backtest import load_postgres

candles = load_postgres(
    "BTCUSDT", "1m",
    host     = "localhost",
    port     = 5432,
    user     = "postgres",
    password = "secret",
    database = "okx",
    # optional filters:
    start    = datetime(2024, 1, 1),
    end      = datetime(2024, 6, 1),
    limit    = 50_000,
)

result = Backtest(MyStrategy).run(candles)
```

Custom table name override:

```python
candles = load_postgres("BTCUSDT", "1m", table="my_custom_table", ...)
```

---

## Running a Backtest

```python
# Basic
result = Backtest(MyStrategy).run(candles)

# Override config without editing the class
result = Backtest(MyStrategy, deposit=5_000, leverage=3).run(candles)

# Access metrics
result.return_pct        # e.g. 12.44  (%)
result.win_rate          # e.g. 0.586
result.profit_factor     # e.g. 1.82
result.max_drawdown_pct  # e.g. 6.2   (%)
result.total_trades      # e.g. 87
result.positions         # list of all closed positions

# Pretty print
print(result)
```

Progress is printed every 10,000 bars by default. Suppress with `progress=False`:

```python
result = Backtest(MyStrategy).run(candles, progress=False)
```

---

## Live Chart Integration

Set `broadcast = True` to stream every bar, trade marker, and the final results to TrexTerminal.

```python
class MyStrategy(Strategy):
    broadcast    = True
    port         = 8765
    replay_speed = 1.0   # 1 candle per second (0 = max speed)
```

**Setup:**

1. Start TrexTerminal: `npm run dev` inside the TrexTerminal repo
2. Open `http://localhost:5173`
3. Select the matching symbol and timeframe
4. Run your backtest script

What you see in the terminal:

- Chart streams candles in real time as the backtest replays
- Long/short position boxes drawn automatically on open and updated on close
- Limit order lines appear when orders are placed and disappear when filled/cancelled
- The BtPanel shows live positions, orders, and balance
- The Results tab fills in with the equity curve and stats when the run finishes

### Playback speed

```python
replay_speed = 0.0    # maximum speed (no delay between bars)
replay_speed = 1.0    # 1 bar per real-time second
replay_speed = 60.0   # 60 bars per second (realtime feel for 1m data)
```

The speed can be adjusted from TrexTerminal's playback controls while the backtest is running.

---

## Backtest Results

`BacktestResult` is a dataclass with all statistics:

| Attribute | Type | Description |
|-----------|------|-------------|
| `initial_balance` | float | Starting USDT |
| `final_balance` | float | Ending USDT (including open position value) |
| `return_pct` | float | `(final - initial) / initial * 100` |
| `total_trades` | int | Total closed positions |
| `winning_trades` | int | Positions with `pnl_usdt >= 0` |
| `losing_trades` | int | Positions with `pnl_usdt < 0` |
| `win_rate` | float | `winning / total` (0–1) |
| `profit_factor` | float | `gross_profit / abs(gross_loss)` |
| `risk_reward` | float | `avg_win / abs(avg_loss)` |
| `total_pnl_usdt` | float | Net P&L in USDT |
| `gross_profit` | float | Sum of all winning trades |
| `gross_loss` | float | Sum of all losing trades (negative) |
| `largest_win` | float | Best single trade |
| `largest_loss` | float | Worst single trade |
| `avg_win` | float | `gross_profit / winning_trades` |
| `avg_loss` | float | `gross_loss / losing_trades` |
| `max_drawdown_usdt` | float | Peak-to-trough drawdown in USDT |
| `max_drawdown_pct` | float | Peak-to-trough drawdown as % of peak |
| `positions` | list | All closed `PositionIsolate` / `PositionCross` objects |

---

## Examples

| File | Strategy | Concepts |
|------|----------|---------|
| `examples/01_quick_start.py` | RSI oversold/overbought | Minimal strategy, demo data |
| `examples/02_ema_crossover.py` | EMA 9/21 golden/death cross | SL/TP %, fixed USDT per trade |
| `examples/03_macd_strategy.py` | MACD histogram zero-cross | Risk % of balance per trade |
| `examples/04_multi_indicator.py` | RSI + EMA filter + ATR SL | Multi-indicator confluence, dynamic SL |
| `examples/05_real_data.py` | Bollinger Band breakout | Loading real CSV data |
| `examples/06_live_chart.py` | EMA crossover + live chart | `broadcast=True`, TrexTerminal |

```bash
python examples/01_quick_start.py
```

---

## Project Structure

```
BackTest/
├── backtest/
│   ├── __init__.py              # public API
│   ├── strategy.py              # Strategy base class
│   ├── runner.py                # Backtest orchestrator
│   ├── stats.py                 # BacktestResult dataclass
│   ├── drawings.py              # chart drawing helpers
│   ├── playback.py              # PlaybackController (pause/speed)
│   ├── exchange/                # exchange simulation engine
│   │   ├── exchange.py          # Exchange class
│   │   ├── user/
│   │   │   ├── isolate.py       # isolated-margin account
│   │   │   └── cross.py         # cross-margin account
│   │   └── dataclass/           # Order, Position, enums
│   └── utils/
│       ├── demo.py              # demo_candles() GBM generator
│       ├── candle_loader.py     # load_csv / load_dicts / load_lists
│       └── postgres_loader.py   # load_postgres
├── examples/
│   ├── 01_quick_start.py
│   ├── 02_ema_crossover.py
│   ├── 03_macd_strategy.py
│   ├── 04_multi_indicator.py
│   ├── 05_real_data.py
│   └── 06_live_chart.py
└── strategies/
    └── rsi_strategy.py
```

---

## Requirements

- Python ≥ 3.11
- [Trex Engine](https://github.com/DeveloperNasirpur/Trex_engin): `pip install -e ../Trex_engin`
- PostgreSQL loader: `pip install psycopg2-binary` (optional, only for `load_postgres`)

---

## License

MIT
