# BackTest

**Professional backtesting engine for Python — write a strategy in 20 lines, get a complete P&L report, and stream every trade live to your chart.**

Powered by [Trex Engine](https://github.com/DeveloperNasirpur/Trex_engin) for 110+ streaming indicators and [TrexTerminal](https://github.com/DeveloperNasirpur/TrexTerminal) for live visualization.

---

## Table of Contents

- [Quick Start](#quick-start)
- [How the Engine Works](#how-the-engine-works)
- [Strategy API](#strategy-api)
  - [Configuration](#configuration)
  - [Required Methods](#required-methods)
  - [Trading Commands](#trading-commands)
  - [Properties](#properties)
  - [OHLCV Object](#ohlcv-object)
  - [Event Callbacks](#event-callbacks)
  - [Position and Order Fields](#position-and-order-fields)
- [Position Sizing Patterns](#position-sizing-patterns)
- [Common Strategy Patterns](#common-strategy-patterns)
- [Candle Data](#candle-data)
- [Running a Backtest](#running-a-backtest)
- [Live Chart Integration](#live-chart-integration)
- [Backtest Results](#backtest-results)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Requirements](#requirements)

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

## How the Engine Works

Understanding the per-bar execution order is critical for writing correct strategies.

### Per-bar execution order

For each candle in the dataset, the engine executes **in this exact sequence**:

```
1.  trex.push(bar)          → indicators recomputed, listener callbacks fired
2.  exchange.kline(bar)     → limit orders checked, SL/TP evaluated, positions updated
3.  strategy.on_kline(bar)  → your trading logic runs
```

### What this means in practice

| Scenario | Behavior |
|----------|----------|
| **Market order** placed in `on_kline` | Fills at the **current bar's close** (realistic EOB) |
| **Limit order** placed in `on_kline` | Evaluated from the **next bar onward** |
| **SL / TP** | Evaluated at bar open — if the bar gaps through the level, it triggers at the level price |
| **Indicator values** | Always reflect the **closed** bar — no look-ahead bias |

### Fee and slippage model

```
market_fill_price = close × (1 + slippage)   # for longs
market_fill_price = close × (1 - slippage)   # for shorts
fee_deducted      = position_value × fee      # both on open and close
```

Default: `fee=0.0004` (0.04% — Binance/OKX taker), `slippage=0.0001` (0.01%).

---

## Strategy API

### Configuration

```python
class MyStrategy(Strategy):
    symbol       = "BTCUSDT"   # trading pair
    timeframe    = "1m"        # candle interval
    deposit      = 10_000.0    # starting USDT
    leverage     = 5           # position leverage (1–125)
    fee          = 0.0004      # taker fee per side (0.04%)
    slippage     = 0.0001      # market-order price impact (0.01%)
    broadcast    = False       # True → stream to TrexTerminal
    port         = 8765        # TrexTerminal WebSocket port
    replay_speed = 0.0         # 0=max speed, 1.0=1 bar/s, 60=1 bar per tf-sec
```

All fields can be overridden at run time without editing the class:

```python
result = Backtest(MyStrategy, deposit=5_000, leverage=10, fee=0.0002).run(candles)
```

### Required Methods

```python
class MyStrategy(Strategy):

    def indicators(self) -> None:
        """
        Register trex indicators here. Called once before the candle loop.
        trex is already initialized — just call trex.rsi(), trex.ema(), etc.
        """
        trex.ema(self.symbol, self.timeframe, period=20, listener=self._on_ema)
        trex.rsi(self.symbol, self.timeframe, period=14, listener=self._on_rsi)

    def on_kline(self, ohlcv: OHLCV) -> None:
        """
        Called once per bar, after indicators are updated and pending orders processed.
        Place your buy/sell/close logic here.
        """
        ...
```

### Trading Commands

```python
# ── Open positions ───────────────────────────────────────────────────────

# Market long (fills at current bar close)
self.buy(usdt=300)

# Market long with stop-loss and take-profit
self.buy(usdt=300, sl=41_000, tp=43_500)

# Limit long (evaluates from the next bar)
self.buy(usdt=300, price=42_000, sl=41_000, tp=43_500)

# Market short
self.sell(usdt=300, sl=43_000, tp=40_500)

# Limit short
self.sell(usdt=300, price=43_500, sl=44_000, tp=41_000)

# ── Close positions ──────────────────────────────────────────────────────

self.close()                    # close ALL open positions at market
self.close(position_id=42)      # close one specific position

# ── Modify running positions ─────────────────────────────────────────────

self.set_sl_tp(position_id, sl=41_500, tp=44_000)   # update SL/TP
self.set_sl_tp(position_id, tp=44_500)               # update only TP
self.set_sl_tp(position_id, sl=42_000)               # update only SL

# ── Orders ───────────────────────────────────────────────────────────────

self.cancel(order_id)           # cancel a pending limit order

# ── Leverage ─────────────────────────────────────────────────────────────

self.set_leverage(10)           # change leverage mid-strategy
```

### Properties

```python
self.balance    # float — current available USDT (excludes locked margin)
self.positions  # list  — all currently open positions for self.symbol
self.orders     # list  — all pending limit orders for self.symbol
self.history    # list  — all closed positions (full trade history)
```

### OHLCV Object

The `ohlcv` argument passed to `on_kline` has these fields:

```python
ohlcv.open       # float  — bar open price
ohlcv.high       # float  — bar high price
ohlcv.low        # float  — bar low price
ohlcv.close      # float  — bar close price  ← market orders fill here
ohlcv.volume     # float | None — volume (None if not in source data)
ohlcv.time       # datetime (UTC) — bar open time
ohlcv.symbol     # str    — e.g. "BTCUSDT"
ohlcv.str_time   # str    — timeframe string e.g. "1m"
```

**Example — ATR-based stop:**

```python
def on_kline(self, ohlcv):
    atr = getattr(self, "_atr", None)
    if atr is None:
        return
    price = ohlcv.close
    sl    = price - 1.5 * atr    # 1.5× ATR below close
    tp    = price + 3.0 * atr    # 3.0× ATR above close (1:2 R/R)
    if not self.positions:
        self.buy(usdt=200, sl=sl, tp=tp)
```

### Event Callbacks

Override any combination. All are called **after** the triggering action completes:

```python
def on_position_opened(self, pos):
    """Position opened (market filled or limit triggered)."""
    print(f"Opened {pos.side.value} @ {pos.entry:.2f}")

def on_position_closed(self, pos):
    """Position manually closed via self.close()."""
    print(f"Closed  PnL={pos.pnl_usdt:+.2f}")

def on_position_profit(self, pos):
    """Take-profit hit."""
    print(f"TP hit  +${pos.pnl_usdt:.2f}")

def on_position_loss(self, pos):
    """Stop-loss hit."""
    print(f"SL hit  -${abs(pos.pnl_usdt):.2f}")

def on_position_liquidated(self, pos):
    """Margin liquidated (balance too low to hold position)."""

def on_order_placed(self, order):
    """Limit order placed in the order book."""
    print(f"Limit order @ {order.entry:.2f}")

def on_order_cancelled(self, order):
    """Limit order cancelled."""
```

### Position and Order Fields

```python
# ── Position ─────────────────────────────────────────────────────────────
pos.id            # int    — unique position ID
pos.side          # Side.LONG | Side.SHORT
pos.symbol        # str    — e.g. "BTCUSDT"
pos.entry         # float  — fill price
pos.stop_price    # float | None — stop-loss price
pos.take_profit   # float | None — take-profit price
pos.margin        # float  — USDT locked as collateral
pos.leverage      # int    — effective leverage
pos.pnl           # float  — fractional P&L: (exit-entry)/entry for long
pos.pnl_usdt      # float  — realized P&L in USDT  [set on close]
pos.open_time     # datetime
pos.close_time    # datetime | None   [set on close]
pos.bars          # int    — number of bars the position was open
pos.state         # PositionState.OPEN | CLOSED | TRIGGERED | STOPPED | LIQUIDATED

# ── Order ────────────────────────────────────────────────────────────────
order.id          # int
order.side        # Side.LONG | Side.SHORT
order.order_type  # OrderType.LIMIT | OrderType.MARKET
order.symbol      # str
order.entry       # float  — limit price
order.usdt        # float  — order size
order.stop_price  # float | None
order.take_profit # float | None
order.placed_time # datetime
```

---

## Position Sizing Patterns

### Fixed USDT per trade

```python
def on_kline(self, ohlcv):
    if not self.positions and signal:
        self.buy(usdt=200)   # always risk exactly 200 USDT
```

### Percent of balance (compound growth)

```python
RISK_PCT = 0.02   # 2% of account per trade

def on_kline(self, ohlcv):
    if not self.positions and signal:
        usdt = self.balance * self.RISK_PCT
        self.buy(usdt=usdt)
```

### Fixed fractional risk (ATR-based)

Size the trade so that if the stop is hit you lose exactly `risk_usdt`:

```python
RISK_USDT = 50.0   # maximum loss per trade in USDT
ATR_MULT  = 1.5    # stop distance = 1.5× ATR

def on_kline(self, ohlcv):
    atr = getattr(self, "_atr", None)
    if atr is None or self.positions:
        return

    sl_dist  = atr * self.ATR_MULT           # price distance to stop
    sl_pct   = sl_dist / ohlcv.close         # as a fraction of price
    # margin × leverage × sl_pct = RISK_USDT
    # → margin = RISK_USDT / (leverage × sl_pct)
    margin   = self.RISK_USDT / (self.leverage * sl_pct)
    margin   = min(margin, self.balance * 0.5)  # cap at 50% of balance

    sl = ohlcv.close - sl_dist
    tp = ohlcv.close + sl_dist * 2          # 1:2 R/R
    self.buy(usdt=margin, sl=sl, tp=tp)
```

### Max one position, no pyramiding

```python
def on_kline(self, ohlcv):
    if len(self.positions) >= 1:   # already in a trade
        return
    ...
```

### Max N positions

```python
MAX_POSITIONS = 3

def on_kline(self, ohlcv):
    if len(self.positions) >= self.MAX_POSITIONS:
        return
    ...
```

---

## Common Strategy Patterns

### Detect indicator crossovers

Track the previous value yourself — the engine gives you one value per bar:

```python
def _on_fast(self, v):
    self._prev_fast = getattr(self, "_fast", None)
    self._fast = v

def _on_slow(self, v):
    self._prev_slow = getattr(self, "_slow", None)
    self._slow = v

def on_kline(self, ohlcv):
    f, pf = self._fast, self._prev_fast
    s, ps = self._slow, self._prev_slow
    if None in (f, pf, s, ps):
        return

    if pf <= ps and f > s:          # golden cross
        self.buy(usdt=200)
    elif pf >= ps and f < s:        # death cross
        self.sell(usdt=200)
```

### Multi-indicator confluence

```python
def on_kline(self, ohlcv):
    rsi = getattr(self, "_rsi", None)
    ema = getattr(self, "_ema", None)
    atr = getattr(self, "_atr", None)
    if None in (rsi, ema, atr) or self.positions:
        return

    price = ohlcv.close
    # require BOTH conditions
    if rsi < 35 and price > ema:
        sl = price - 1.5 * atr
        tp = price + 3.0 * atr
        self.buy(usdt=200, sl=sl, tp=tp)
```

### Trailing stop (manual)

```python
def on_position_opened(self, pos):
    self._trail_sl = pos.entry * 0.985   # initial stop 1.5% below

def on_kline(self, ohlcv):
    for pos in self.positions:
        new_sl = ohlcv.close * 0.985     # trail below current price
        if new_sl > (pos.stop_price or 0):
            self.set_sl_tp(pos.id, sl=new_sl)
```

### Close on opposite signal

```python
def on_kline(self, ohlcv):
    rsi = getattr(self, "_rsi", None)
    if rsi is None:
        return

    for pos in list(self.positions):
        # close long if now overbought
        if pos.side.value == "long" and rsi > 70:
            self.close(pos.id)
        # close short if now oversold
        elif pos.side.value == "short" and rsi < 30:
            self.close(pos.id)
```

### Time-based close (exit after N bars)

```python
def on_kline(self, ohlcv):
    for pos in list(self.positions):
        if pos.bars >= 20:         # exit after 20 bars
            self.close(pos.id)
```

### Limit order entry with fallback

```python
def on_kline(self, ohlcv):
    if self.positions or self.orders:
        return
    if signal:
        # try to get a better fill price
        limit_price = ohlcv.close * 0.998   # 0.2% below close
        self.buy(usdt=200, price=limit_price, sl=limit_price * 0.985, tp=limit_price * 1.03)

def on_kline(self, ohlcv):
    # cancel stale limit orders after 5 bars
    for order in list(self.orders):
        if (ohlcv.time - order.placed_time).total_seconds() > 5 * 60:
            self.cancel(order.id)
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
    start_price = 42_000.0,
    volatility  = 0.003,    # ~0.3% per bar (realistic BTC 1m)
    trend       = 0.0001,   # slight upward drift per bar
    seed        = 42,       # reproducible; pass None for random
)
```

Uses Geometric Brownian Motion with realistic OHLC wicks.

### Load from CSV

```python
from backtest import load_csv

candles = load_csv(
    "data/BTCUSDT_1m.csv",
    symbol    = "BTCUSDT",
    timeframe = "1m",
)
```

Timestamp formats auto-detected: Unix ms, Unix seconds, ISO 8601.  
Column names auto-detected: `time`/`open_time`/`timestamp`, `open`, `high`, `low`, `close`, `volume`.

Override column names explicitly if needed:

```python
candles = load_csv(
    "data/BTCUSDT_1m.csv",
    symbol    = "BTCUSDT",
    timeframe = "1m",
    time_col  = "Date",
    open_col  = "Open",
    high_col  = "High",
    low_col   = "Low",
    close_col = "Close",
    vol_col   = "Volume",
)
```

### Load from pandas DataFrame

```python
from backtest import load_dicts
import pandas as pd

df      = pd.read_parquet("data/btc.parquet")
candles = load_dicts(df.to_dict("records"), symbol="BTCUSDT", timeframe="1h")
```

### Load from lists/tuples

```python
from backtest import load_lists

# Each row: [time_ms, open, high, low, close, volume]
rows    = [[1704067200000, 42150.0, 42300.0, 42100.0, 42250.0, 123.45], ...]
candles = load_lists(rows, symbol="BTCUSDT", timeframe="1m")
```

### Load from PostgreSQL

Reads from the table format used by [Trex Engine](https://github.com/DeveloperNasirpur/Trex_engin)'s `TrexStore`.  
Table name auto-derived: `"BTCUSDT"` + `"1m"` → `"BTCUSDT1M"`.

```python
from backtest import load_postgres
from datetime import datetime

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
    limit    = 100_000,
    # override table name:
    # table = "my_custom_table",
)

result = Backtest(MyStrategy).run(candles)
```

Requires `pip install psycopg2-binary`.

---

## Running a Backtest

```python
# Basic
result = Backtest(MyStrategy).run(candles)

# Override strategy config at run time
result = Backtest(
    MyStrategy,
    deposit  = 5_000,
    leverage = 10,
    fee      = 0.0002,
).run(candles)

# Suppress progress output
result = Backtest(MyStrategy).run(candles, progress=False)

# Already-instantiated strategy
strategy = MyStrategy()
strategy.deposit = 50_000
result = Backtest(strategy).run(candles)
```

Progress is printed every 10,000 bars by default:

```
[backtest] Starting — 50,000 bars | symbol=BTCUSDT tf=1m deposit=$10,000 lev=5x fee=0.04%
[backtest] 10,000/50,000 (20.0%) elapsed=0s  ETA≈2s
[backtest] Done — 50,000 bars in 2.4s
```

---

## Live Chart Integration

Set `broadcast = True` to stream every bar, trade marker, and final results to TrexTerminal.

```python
class MyStrategy(Strategy):
    broadcast    = True
    port         = 8765
    replay_speed = 1.0    # 1 candle per second (0 = max speed)
```

### Setup

1. Start TrexTerminal: `npm run dev` in the TrexTerminal repo
2. Open `http://localhost:5173`
3. Select the matching symbol and timeframe
4. Run your backtest script

### What appears in the terminal

| Element | When |
|---------|------|
| Candles stream live | Every bar |
| Indicator overlays update | Every bar |
| Long/short position box drawn | On `on_position_opened` |
| Position box updated (color, exit price) | On close/TP/SL |
| Limit order horizontal line | On `on_order_placed` |
| Limit order line removed | On fill or cancel |
| BtPanel positions/orders/balance | Throttled to ~10 fps |
| Results tab fills in | After the last bar |

### Playback speed

```python
replay_speed = 0.0    # maximum speed — no delay (default)
replay_speed = 1.0    # 1 bar per second
replay_speed = 60.0   # 60 bars per second (feels realtime for 1m data)
```

Speed can be adjusted from TrexTerminal's playback slider while the backtest runs. Pause/Resume works too.

---

## Backtest Results

`BacktestResult` is a dataclass with full statistics:

```python
result = Backtest(MyStrategy).run(candles)

# Access any metric
print(result.return_pct)          # e.g.  12.44  (%)
print(result.win_rate)            # e.g.  0.586  (0–1)
print(result.profit_factor)       # e.g.  1.82
print(result.max_drawdown_pct)    # e.g.  6.20   (%)
print(result.total_trades)        # e.g.  87
print(result.positions)           # list of all closed positions

# Print full summary table
print(result)
```

### All fields

| Attribute | Type | Description |
|-----------|------|-------------|
| `initial_balance` | float | Starting USDT |
| `final_balance` | float | Ending USDT |
| `return_pct` | float | `(final−initial) / initial × 100` |
| `total_trades` | int | Total closed positions |
| `winning_trades` | int | Positions with `pnl_usdt ≥ 0` |
| `losing_trades` | int | Positions with `pnl_usdt < 0` |
| `win_rate` | float | `winning / total` (0–1) |
| `profit_factor` | float | `gross_profit / |gross_loss|` |
| `risk_reward` | float | `avg_win / |avg_loss|` |
| `total_pnl_usdt` | float | Net P&L in USDT |
| `gross_profit` | float | Sum of all winning trades |
| `gross_loss` | float | Sum of all losing trades (negative) |
| `largest_win` | float | Best single trade in USDT |
| `largest_loss` | float | Worst single trade in USDT |
| `avg_win` | float | `gross_profit / winning_trades` |
| `avg_loss` | float | `gross_loss / losing_trades` |
| `max_drawdown_usdt` | float | Peak-to-trough drawdown in USDT |
| `max_drawdown_pct` | float | Peak-to-trough drawdown as % of peak equity |
| `positions` | list | All closed `Position` objects |

### Iterate over individual trades

```python
for pos in result.positions:
    print(f"{pos.open_time:%Y-%m-%d}  {pos.side.value:5s}  "
          f"entry={pos.entry:,.2f}  pnl={pos.pnl_usdt:+.2f}  bars={pos.bars}")
```

### Build a custom equity curve

```python
equity = result.initial_balance
for pos in result.positions:
    equity += pos.pnl_usdt or 0
    print(f"{pos.close_time:%Y-%m-%d}  equity=${equity:,.2f}")
```

---

## Examples

### Example 1 — RSI Oversold/Overbought

```python
class SimpleRSI(Strategy):
    symbol = "BTCUSDT"; timeframe = "1m"; deposit = 10_000; leverage = 5

    def indicators(self):
        trex.rsi(self.symbol, self.timeframe, period=14, listener=self._rsi)

    def _rsi(self, v): self._rsi_val = v

    def on_kline(self, ohlcv):
        rsi = getattr(self, "_rsi_val", None)
        if rsi is None: return
        if rsi < 30 and not self.positions:
            self.buy(usdt=200)
        elif rsi > 70 and not self.positions:
            self.sell(usdt=200)
        elif self.positions and 45 < rsi < 55:
            self.close()
```

Run: `python examples/01_quick_start.py`

### Example 2 — EMA Crossover

Classic dual-EMA golden/death cross with fixed SL/TP:

```python
class EMACross(Strategy):
    symbol = "BTCUSDT"; timeframe = "1m"; deposit = 10_000; leverage = 3
    USDT_PER_TRADE = 300.0; SL_PCT = 0.015; TP_PCT = 0.030

    def indicators(self):
        trex.ema(self.symbol, self.timeframe, period=9,  listener=self._fast, visible=True)
        trex.ema(self.symbol, self.timeframe, period=21, listener=self._slow, visible=True)

    def _fast(self, v): self._prev_fast = getattr(self, "_fast", None); self._fast = v
    def _slow(self, v): self._prev_slow = getattr(self, "_slow", None); self._slow = v

    def on_kline(self, ohlcv):
        f, pf = getattr(self, "_fast", None), getattr(self, "_prev_fast", None)
        s, ps = getattr(self, "_slow", None), getattr(self, "_prev_slow", None)
        if None in (f, pf, s, ps) or self.positions: return
        p = ohlcv.close
        if pf <= ps and f > s:  # golden cross
            self.buy(usdt=self.USDT_PER_TRADE, sl=p*(1-self.SL_PCT), tp=p*(1+self.TP_PCT))
        elif pf >= ps and f < s:  # death cross
            self.sell(usdt=self.USDT_PER_TRADE, sl=p*(1+self.SL_PCT), tp=p*(1-self.TP_PCT))
```

Run: `python examples/02_ema_crossover.py`

### Example 3 — MACD with % Risk Sizing

```python
class MACDStrategy(Strategy):
    symbol = "BTCUSDT"; timeframe = "1m"; deposit = 10_000; leverage = 5
    RISK_PCT = 0.02; SL_PCT = 0.012; TP_PCT = 0.024

    def indicators(self):
        trex.macd(self.symbol, self.timeframe, fast=12, slow=26, signal=9,
                  listener=self._macd, visible=True)

    def _macd(self, macd, signal, histogram):
        self._prev_hist = getattr(self, "_hist", 0.0)
        self._hist = histogram

    def on_kline(self, ohlcv):
        h, ph = getattr(self, "_hist", None), getattr(self, "_prev_hist", None)
        if None in (h, ph) or self.positions: return
        usdt = self.balance * self.RISK_PCT
        p = ohlcv.close
        if ph <= 0 < h:   # crosses positive
            self.buy(usdt=usdt, sl=p*(1-self.SL_PCT), tp=p*(1+self.TP_PCT))
        elif ph >= 0 > h:  # crosses negative
            self.sell(usdt=usdt, sl=p*(1+self.SL_PCT), tp=p*(1-self.TP_PCT))
```

Run: `python examples/03_macd_strategy.py`

### Example 4 — Multi-Indicator Confluence + ATR Stop

```python
class ConfluenceStrategy(Strategy):
    symbol = "BTCUSDT"; timeframe = "1m"; deposit = 10_000; leverage = 5
    RISK_USDT = 250.0; ATR_MULT = 1.5; RR = 2.0

    def indicators(self):
        trex.rsi(self.symbol, self.timeframe, period=14, listener=self._on_rsi)
        trex.ema(self.symbol, self.timeframe, period=50, listener=self._on_ema, visible=True)
        trex.atr(self.symbol, self.timeframe, period=14, listener=self._on_atr)

    def _on_rsi(self, v): self._rsi = v
    def _on_ema(self, v): self._ema = v
    def _on_atr(self, v): self._atr = v

    def on_kline(self, ohlcv):
        rsi, ema, atr = (getattr(self, x, None) for x in ("_rsi", "_ema", "_atr"))
        if None in (rsi, ema, atr) or self.positions: return
        p, sl_d = ohlcv.close, atr * self.ATR_MULT
        if rsi < 35 and p > ema:   # oversold + uptrend
            self.buy(usdt=self.RISK_USDT, sl=p-sl_d, tp=p+sl_d*self.RR)
        elif rsi > 65 and p < ema:  # overbought + downtrend
            self.sell(usdt=self.RISK_USDT, sl=p+sl_d, tp=p-sl_d*self.RR)
```

Run: `python examples/04_multi_indicator.py`

### Example 5 — Real CSV Data

See `examples/05_real_data.py` for a Bollinger Band breakout strategy that loads from a CSV file with automatic fallback to synthetic data.

### Example 6 — Live Chart

See `examples/06_live_chart.py` for the same EMA crossover strategy with `broadcast=True`, showing trade markers, the BtPanel, and the Results tab in TrexTerminal.

---

## Project Structure

```
BackTest/
├── backtest/
│   ├── __init__.py              # public API
│   ├── strategy.py              # Strategy base class
│   ├── runner.py                # Backtest orchestrator — per-bar loop
│   ├── stats.py                 # BacktestResult dataclass
│   ├── drawings.py              # chart drawing helpers (positions, orders)
│   ├── playback.py              # PlaybackController — pause/speed/resume
│   ├── exchange/
│   │   ├── exchange.py          # Exchange simulation engine
│   │   ├── user/
│   │   │   ├── isolate.py       # isolated-margin account
│   │   │   └── cross.py         # cross-margin account
│   │   └── dataclass/
│   │       ├── classdata.py     # Order, Position, HostEventUser
│   │       └── enums.py         # Side, OrderType, PositionState
│   └── utils/
│       ├── demo.py              # demo_candles() — GBM synthetic data
│       ├── candle_loader.py     # load_csv / load_dicts / load_lists
│       └── postgres_loader.py   # load_postgres
├── examples/
│   ├── 01_quick_start.py        # RSI strategy, demo data
│   ├── 02_ema_crossover.py      # EMA 9/21, fixed SL/TP
│   ├── 03_macd_strategy.py      # MACD histogram, % risk sizing
│   ├── 04_multi_indicator.py    # RSI + EMA + ATR confluence
│   ├── 05_real_data.py          # Bollinger Band, CSV data
│   └── 06_live_chart.py         # EMA crossover, broadcast=True
└── strategies/
    └── rsi_strategy.py
```

---

## Troubleshooting

### `AttributeError: Strategy has no attribute 'X'`

You passed an unknown override to `Backtest()`. Check spelling:

```python
# Wrong
Backtest(MyStrategy, depoist=10_000)

# Right
Backtest(MyStrategy, deposit=10_000)
```

### Indicator value is `None` on the first bars

Indicators need a warmup period equal to their `period`. Always guard with `getattr`:

```python
def on_kline(self, ohlcv):
    rsi = getattr(self, "_rsi", None)
    if rsi is None:
        return   # still warming up
    ...
```

### Strategy opens a position every bar

You're missing the `not self.positions` guard:

```python
# Wrong — opens a new position every bar RSI is low
if rsi < 30:
    self.buy(usdt=200)

# Right — only opens when no position is open
if rsi < 30 and not self.positions:
    self.buy(usdt=200)
```

### `RuntimeError: Strategy is not wired to an exchange`

Don't call `strategy.buy()` outside of `on_kline()` or `on_*` callbacks. Always go through `Backtest(MyStrategy).run(candles)`.

### Limit orders never fill

Limit buy orders require `bar.low <= price`. Limit sell requires `bar.high >= price`.  
If your limit price is too far from current price, it may never be reached in the dataset.

### `broadcast=True` but nothing appears in TrexTerminal

1. Confirm TrexTerminal is running: `npm run dev` → open `http://localhost:5173`
2. Confirm `port` matches TrexTerminal's WebSocket port (default `8765`)
3. Select the matching symbol and timeframe in TrexTerminal **before** running the script
4. Check that `replay_speed` isn't `0.0` if you want to see candles animate (use `1.0` or higher)

### `ImportError: psycopg2 not installed`

```bash
pip install psycopg2-binary
```

---

## Requirements

- Python ≥ 3.11
- [Trex Engine](https://github.com/DeveloperNasirpur/Trex_engin): `pip install -e ../Trex_engin`
- PostgreSQL loader (optional): `pip install psycopg2-binary`
- [TrexTerminal](https://github.com/DeveloperNasirpur/TrexTerminal) (optional, for live chart): `npm install && npm run dev`

---

## License

MIT
