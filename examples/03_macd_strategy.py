"""
Example 03 — MACD Strategy
============================
MACD histogram crosses zero:
  histogram turns positive → Long
  histogram turns negative → Short
  Risk limited to 2 % of current balance per trade.

Run:
    python examples/03_macd_strategy.py
"""
import trex
from backtest import Backtest, Strategy, demo_candles


class MACDStrategy(Strategy):
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0
    leverage  = 5
    broadcast = False

    RISK_PCT = 0.02    # risk 2 % of balance per trade
    SL_PCT   = 0.012
    TP_PCT   = 0.024   # 1 : 2

    def indicators(self):
        trex.macd(
            self.symbol, self.timeframe,
            fast=12, slow=26, signal=9,
            listener=self._macd,
            visible=True,
        )

    def _macd(self, macd: float, signal: float, histogram: float):
        self._hist      = histogram
        self._prev_hist = getattr(self, "_hist", 0.0)

    def on_kline(self, ohlcv):
        hist      = getattr(self, "_hist", None)
        prev_hist = getattr(self, "_prev_hist", None)
        if None in (hist, prev_hist):
            return

        has_pos = bool(self.positions)
        price   = ohlcv.close
        usdt    = self.balance * self.RISK_PCT   # position-size by risk

        # histogram crosses from negative → positive
        if prev_hist <= 0 < hist and not has_pos:
            self.buy(usdt=usdt,
                     sl=price * (1 - self.SL_PCT),
                     tp=price * (1 + self.TP_PCT))

        # histogram crosses from positive → negative
        elif prev_hist >= 0 > hist and not has_pos:
            self.sell(usdt=usdt,
                      sl=price * (1 + self.SL_PCT),
                      tp=price * (1 - self.TP_PCT))

    def on_position_opened(self, pos):
        print(f"  ▶  {pos.side.value:5s} @ {pos.entry:,.2f}  margin=${pos.margin:.0f}")

    def on_position_profit(self, pos):
        print(f"  ✔  +${pos.pnl_usdt:,.2f}   balance=${self.balance:,.2f}")

    def on_position_loss(self, pos):
        print(f"  ✘  ${pos.pnl_usdt:,.2f}   balance=${self.balance:,.2f}")


if __name__ == "__main__":
    print("MACD Histogram Crossover Strategy")
    print("─" * 40)
    candles = demo_candles(bars=8_000, volatility=0.0025, seed=99)
    result  = Backtest(MACDStrategy).run(candles)
    print(result)
