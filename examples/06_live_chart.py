"""
Example 06 — Live Chart Integration
=====================================
Streams the backtest replay to TrexTerminal so you can watch
candles, indicators, and trade markers in real time.

Prerequisites:
  1. Open TrexTerminal in your browser (http://localhost:5173 by default)
  2. Run this script:  python examples/06_live_chart.py
  3. In TrexTerminal select symbol BTCUSDT / timeframe 1m

All position open/close markers will appear automatically on the chart.

Run:
    python examples/06_live_chart.py
"""
import trex
from backtest import Backtest, Strategy, demo_candles


class LiveChartStrategy(Strategy):
    """
    Simple EMA crossover — same logic as example 02 but with broadcast=True
    so every trade is drawn on the TrexTerminal chart in real time.
    """
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0
    leverage  = 3
    broadcast = True          # ← enables chart drawing
    port      = 8765          # TrexTerminal WebSocket port (default)

    USDT_PER_TRADE = 300.0
    SL_PCT         = 0.015
    TP_PCT         = 0.030

    def indicators(self):
        trex.ema(self.symbol, self.timeframe, period=9,  listener=self._fast, visible=True)
        trex.ema(self.symbol, self.timeframe, period=21, listener=self._slow, visible=True)

    def _fast(self, v): self._ema_fast = v
    def _slow(self, v): self._ema_slow = v

    def on_kline(self, ohlcv):
        fast      = getattr(self, "_ema_fast", None)
        slow      = getattr(self, "_ema_slow", None)
        prev_fast = getattr(self, "_prev_fast", None)
        prev_slow = getattr(self, "_prev_slow", None)
        self._prev_fast, self._prev_slow = fast, slow

        if None in (fast, slow, prev_fast, prev_slow):
            return

        price   = ohlcv.close
        has_pos = bool(self.positions)

        if prev_fast <= prev_slow and fast > slow and not has_pos:
            self.buy(usdt=self.USDT_PER_TRADE,
                     sl=price * (1 - self.SL_PCT),
                     tp=price * (1 + self.TP_PCT))

        elif prev_fast >= prev_slow and fast < slow and not has_pos:
            self.sell(usdt=self.USDT_PER_TRADE,
                      sl=price * (1 + self.SL_PCT),
                      tp=price * (1 - self.TP_PCT))

    def on_position_opened(self, pos):
        print(f"  ▶  {pos.side.value:5s} @ {pos.entry:,.2f}  [drawn on chart]")

    def on_position_profit(self, pos):
        print(f"  ✔  +${pos.pnl_usdt:,.2f}   balance=${self.balance:,.2f}")

    def on_position_loss(self, pos):
        print(f"  ✘  ${pos.pnl_usdt:,.2f}   balance=${self.balance:,.2f}")


if __name__ == "__main__":
    print("Live Chart — EMA Crossover (watch in TrexTerminal)")
    print("─" * 50)
    print("Make sure TrexTerminal is running at http://localhost:5173")
    print()

    # Smaller bar count so replay isn't too long to watch
    candles = demo_candles(bars=2_000, volatility=0.002, trend=0.00005, seed=7)
    result  = Backtest(LiveChartStrategy).run(candles)
    print()
    print(result)
