"""
Example 01 — Quick Start
========================
The simplest possible backtest.

Run:
    python examples/01_quick_start.py
"""
import trex
from backtest import Backtest, Strategy, demo_candles


class SimpleRSI(Strategy):
    """
    Long  when RSI < 30 (oversold)
    Short when RSI > 70 (overbought)
    Close when RSI crosses 50
    """
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0     # starting capital in USDT
    leverage  = 5
    broadcast = False         # set True to see trades in TrexTerminal

    def indicators(self):
        trex.rsi(self.symbol, self.timeframe, period=14, listener=self._rsi)

    def _rsi(self, value: float):
        self._rsi_val = value

    def on_kline(self, ohlcv):
        rsi = getattr(self, "_rsi_val", None)
        if rsi is None:
            return

        has_pos = bool(self.positions)

        if rsi < 30 and not has_pos:
            self.buy(usdt=200)

        elif rsi > 70 and not has_pos:
            self.sell(usdt=200)

        elif has_pos and 45 < rsi < 55:
            self.close()


if __name__ == "__main__":
    candles = demo_candles(bars=3_000, seed=42)
    result  = Backtest(SimpleRSI).run(candles)
    print(result)
