"""
main.py — backtest with trex indicator engine
"""
import trex
from trex.domain.types import Bar
from backtest import Exchange, load_csv, load_dicts
from strategies.rsi_strategy import RSIStrategy

SYMBOL    = "BTCUSDT"
TIMEFRAME = "1m"

# ── 1. Init trex (broadcasts live to TrexTerminal) ───────────────────────────
strategy = RSIStrategy()

trex.init(port=8765, source_timeframe=TIMEFRAME)

trex.rsi(SYMBOL, TIMEFRAME, period=14, visible=True, listener=strategy.on_rsi)
trex.ema(SYMBOL, TIMEFRAME, period=20, visible=True)

# ── 2. Exchange setup ─────────────────────────────────────────────────────────
exchange = Exchange(
    symbols=[SYMBOL],
    taker_fee=0.0004,   # 0.04% per trade
    slippage=0.0001,    # 0.01% slippage on market orders
)
user_id = exchange.sing_up(strategy)
exchange.deposit(user_id, 10_000)   # $10,000 starting capital

strategy.exchange = exchange
strategy.user_id  = user_id

# ── 3. Load candles ───────────────────────────────────────────────────────────
# Option A — from CSV:
#   candles = load_csv("data/BTCUSDT_1m.csv", symbol=SYMBOL, timeframe=TIMEFRAME)
#
# Option B — from a list of dicts (e.g. pandas DataFrame):
#   import pandas as pd
#   df = pd.read_csv("data/BTCUSDT_1m.csv")
#   candles = load_dicts(df.to_dict("records"), symbol=SYMBOL, timeframe=TIMEFRAME)
#
# Option C — from your own DB:
#   candles = db.fetch_bars("binance", SYMBOL, TIMEFRAME)

def load_candles(symbol: str):
    # Replace with your actual data source:
    raise NotImplementedError("Provide candles via load_csv() or load_dicts()")

candles = load_candles(SYMBOL)

# ── 4. Run backtest ───────────────────────────────────────────────────────────
def on_bar(ohlcv):
    """Called before each bar is processed by the exchange."""
    trex.push(Bar(
        time=int(ohlcv.time.timestamp() * 1000),
        open=ohlcv.open, high=ohlcv.high, low=ohlcv.low,
        close=ohlcv.close, volume=ohlcv.volume,
    ), symbol=SYMBOL)
    strategy.on_kline(ohlcv)

result = exchange.run(candles, on_bar=on_bar)

# ── 5. Results ────────────────────────────────────────────────────────────────
print(result)
