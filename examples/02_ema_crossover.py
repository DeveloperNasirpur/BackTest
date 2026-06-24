"""
Example 02 — EMA Crossover
===========================
Classic dual-EMA strategy:
  EMA-fast crosses above EMA-slow → Long
  EMA-fast crosses below EMA-slow → Short

Run:
    python examples/02_ema_crossover.py
"""
import trex
from backtest import Backtest, Strategy, demo_candles


class EMACross(Strategy):
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0
    leverage  = 3
    broadcast = False

    # ── how much to risk per trade ──────────────────────────────────────
    USDT_PER_TRADE = 300.0
    SL_PCT         = 0.015   # 1.5 % stop-loss
    TP_PCT         = 0.030   # 3.0 % take-profit  → 1 : 2 R/R

    def indicators(self):
        trex.ema(self.symbol, self.timeframe, period=9,  listener=self._ema_fast, visible=True)
        trex.ema(self.symbol, self.timeframe, period=21, listener=self._ema_slow, visible=True)

    # ── indicator listeners ─────────────────────────────────────────────
    def _ema_fast(self, v): self._fast = v
    def _ema_slow(self, v): self._slow = v

    # ── bar logic ───────────────────────────────────────────────────────
    def on_kline(self, ohlcv):
        fast = getattr(self, "_fast", None)
        slow = getattr(self, "_slow", None)
        prev_fast = getattr(self, "_prev_fast", None)
        prev_slow = getattr(self, "_prev_slow", None)

        # store last bar values before updating
        self._prev_fast, self._prev_slow = fast, slow

        if None in (fast, slow, prev_fast, prev_slow):
            return

        price    = ohlcv.close
        has_pos  = bool(self.positions)

        # golden cross → long
        if prev_fast <= prev_slow and fast > slow and not has_pos:
            sl = price * (1 - self.SL_PCT)
            tp = price * (1 + self.TP_PCT)
            self.buy(usdt=self.USDT_PER_TRADE, sl=sl, tp=tp)

        # death cross → short
        elif prev_fast >= prev_slow and fast < slow and not has_pos:
            sl = price * (1 + self.SL_PCT)
            tp = price * (1 - self.TP_PCT)
            self.sell(usdt=self.USDT_PER_TRADE, sl=sl, tp=tp)

    # ── optional: log every trade ───────────────────────────────────────
    def on_position_opened(self, pos):
        print(f"  ▶  {pos.side.value:5s} opened  @ {pos.entry:,.2f}")

    def on_position_profit(self, pos):
        print(f"  ✔  TP hit  +${pos.pnl_usdt:,.2f}")

    def on_position_loss(self, pos):
        print(f"  ✘  SL hit  -${abs(pos.pnl_usdt):,.2f}")


if __name__ == "__main__":
    print("EMA 9/21 Crossover Strategy")
    print("─" * 40)
    candles = demo_candles(bars=5_000, volatility=0.002, trend=0.00005, seed=7)
    result  = Backtest(EMACross).run(candles)
    print(result)
