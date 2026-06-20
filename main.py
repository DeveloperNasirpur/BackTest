"""
main.py — dead-simple backtest entry point.

1. Write your strategy in strategies/
2. Load candles
3. Run

That's it.
"""
from backtest import Backtest, load_csv
from strategies.rsi_strategy import RSIStrategy

# ── load candles (replace with your real data source) ────────────────────────
# candles = load_csv("data/BTCUSDT_1m.csv", symbol="BTCUSDT", timeframe="1m")

# ── run backtest ──────────────────────────────────────────────────────────────
# result = Backtest(RSIStrategy).run(candles)
# print(result)

# ── override any strategy parameter without touching the class ────────────────
# result = Backtest(RSIStrategy, deposit=50_000, leverage=5, fee=0.0002).run(candles)

# ── access raw positions after the run ───────────────────────────────────────
# for pos in result.positions:
#     print(pos.side, pos.pnl_usdt, pos.bars)

print("Edit main.py: provide candles via load_csv() and uncomment the lines above.")
