# BackTest

A professional-grade backtesting engine for Python, powered by [trex_engine](https://github.com/developernasirpur/trexterminal).

Write your strategy in **20 lines**. Get a full P&L report. Stream trade markers live to your chart — zero boilerplate.

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

    def _on_rsi(self, v): self._rsi = v

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

Sample output:

```
══════════════════════════════════════════
         BACKTEST RESULTS
══════════════════════════════════════════
 Initial balance   $10,000.00
 Final balance     $11,243.60
 Net P&L           +$1,243.60  (+12.44 %)
──────────────────────────────────────────
 Total trades      87
 Win rate          58.6 %
 Profit factor     1.82
──────────────────────────────────────────
 Avg win           +$48.30
 Avg loss          -$26.10
 Largest win       +$312.00
 Largest loss      -$89.50
 Max drawdown      -$620.40  (-6.20 %)
══════════════════════════════════════════
```

---

## Strategy API

### Class-level configuration

```python
class MyStrategy(Strategy):
    symbol    = "BTCUSDT"   # trading pair
    timeframe = "1m"        # candle interval
    deposit   = 10_000.0   # starting USDT
    leverage  = 5           # position leverage
    fee       = 0.0004      # 0.04% taker fee
    slippage  = 0.0001      # 0.01% market-order slippage
    broadcast = False       # True → stream to TrexTerminal
    port      = 8765        # TrexTerminal WebSocket port
```

### Required methods

| Method | When called |
|---|---|
| `indicators(self)` | Once before the candle loop. Register trex indicators here. |
| `on_kline(self, ohlcv)` | Once per bar, after all indicators are updated. |

### Trading commands

```python
# Open positions
self.buy(usdt=300)                                       # market long, no SL/TP
self.buy(usdt=300, sl=41000, tp=43500)                  # with SL and TP
self.buy(usdt=300, price=42000, sl=41000, tp=43500)     # limit long

self.sell(usdt=300, sl=43000, tp=40500)                 # market short

# Close positions
self.close()                 # close ALL open positions
self.close(position_id=42)   # close one specific position

# Modify a running position
self.set_sl_tp(position_id, sl=41500, tp=44000)

# Cancel a pending limit order
self.cancel(order_id)

# Change leverage mid-strategy
self.set_leverage(10)
```

### Read-only properties

```python
self.balance    # current available USDT
self.positions  # list of open positions
self.orders     # list of pending limit orders
self.history    # list of all closed positions
```

### Event hooks (optional)

Override any combination:

```python
def on_position_opened(self, pos):     ...
def on_position_closed(self, pos):     ...  # manual close
def on_position_profit(self, pos):     ...  # TP hit
def on_position_loss(self, pos):       ...  # SL hit
def on_position_liquidated(self, pos): ...
def on_order_placed(self, order):      ...
def on_order_cancelled(self, order):   ...
```

### Position / Order fields

```python
pos.id           # int
pos.side         # Side.LONG | Side.SHORT
pos.entry        # entry price
pos.stop_price   # stop-loss price
pos.take_profit  # take-profit price
pos.margin       # USDT collateral locked
pos.pnl_usdt     # realized P&L (available in close callbacks)
pos.open_time    # datetime
pos.close_time   # datetime (set on close)

order.id
order.side       # Side.LONG | Side.SHORT
order.entry      # limit price
order.usdt       # order size in USDT
```

---

## Candle Data

### Synthetic data (demo / prototyping)

```python
from backtest import demo_candles

candles = demo_candles(
    bars        = 5_000,
    symbol      = "BTCUSDT",
    timeframe   = "1m",
    start_price = 42_000,
    volatility  = 0.003,   # ~0.3% per bar
    trend       = 0.0001,  # slight upward drift
    seed        = 42,      # reproducible
)
```

### Load from CSV

```python
from backtest import load_csv

# CSV with columns: timestamp, open, high, low, close, volume
candles = load_csv(
    "data/BTCUSDT_1m.csv",
    symbol="BTCUSDT",
    timeframe="1m",
    # optional column name overrides:
    time_col  = "open_time",
    open_col  = "open",
    high_col  = "high",
    low_col   = "low",
    close_col = "close",
    vol_col   = "volume",
)
```

Timestamp formats auto-detected: unix milliseconds, unix seconds, or ISO 8601.

### Load from pandas DataFrame

```python
from backtest import load_dicts
import pandas as pd

df      = pd.read_parquet("data/btc.parquet")
candles = load_dicts(df.to_dict("records"), symbol="BTCUSDT", timeframe="1h")
```

---

## Live Chart Integration (TrexTerminal)

Set `broadcast = True` and every trade is drawn on the chart automatically.

```python
class MyStrategy(Strategy):
    broadcast = True    # enable drawing
    port      = 8765   # TrexTerminal WebSocket port
```

1. Start TrexTerminal: `npm run dev` in the TrexTerminal repo
2. Open `http://localhost:5173` in your browser
3. Select the matching symbol and timeframe
4. Run your backtest script

Position markers, stop-loss / take-profit levels, and limit order lines appear in real time as the backtest replays.

---

## Running the Backtest

```python
# Basic
result = Backtest(MyStrategy).run(candles)

# Override strategy config without editing the class
result = Backtest(MyStrategy, deposit=5_000, leverage=3).run(candles)

# Access individual metrics
print(result.return_pct)       # e.g. 12.44
print(result.win_rate)         # e.g. 0.586
print(result.profit_factor)    # e.g. 1.82
print(result.max_drawdown_pct) # e.g. -6.20
print(result.total_trades)     # e.g. 87
print(result.positions)        # list of all closed positions

# Pretty-print full summary
print(result)
```

---

## Examples

| File | Strategy | Concepts |
|---|---|---|
| `examples/01_quick_start.py` | RSI oversold/overbought | Minimal strategy, demo data |
| `examples/02_ema_crossover.py` | EMA 9/21 golden/death cross | SL/TP %, fixed USDT per trade |
| `examples/03_macd_strategy.py` | MACD histogram zero-cross | Risk % of balance per trade |
| `examples/04_multi_indicator.py` | RSI + EMA filter + ATR SL | Multi-indicator confluence, dynamic SL |
| `examples/05_real_data.py` | Bollinger Band breakout | Loading real CSV data |
| `examples/06_live_chart.py` | EMA crossover + live chart | `broadcast=True`, TrexTerminal |

Run any example:

```bash
python examples/01_quick_start.py
```

---

## Project Structure

```
BackTest/
├── backtest/
│   ├── __init__.py          # public API
│   ├── strategy.py          # Strategy base class
│   ├── runner.py            # Backtest orchestrator
│   ├── stats.py             # BacktestResult dataclass
│   ├── drawings.py          # chart drawing helpers
│   ├── exchange/            # exchange simulation engine
│   │   ├── exchange.py
│   │   ├── user/
│   │   │   ├── isolate.py   # isolated-margin user
│   │   │   └── cross.py     # cross-margin user
│   │   └── dataclass/       # Order, Position, enums
│   └── utils/
│       ├── demo.py          # demo_candles() GBM generator
│       └── candle_loader.py # load_csv / load_dicts / load_lists
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
- trex_engine (`pip install -e ../Trex_engin`)

---

## License

MIT
