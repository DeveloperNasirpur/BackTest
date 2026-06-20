"""
RSI Strategy — sample using the new Strategy base class.

Logic:
  RSI < 30  → buy  (oversold)
  RSI > 70  → sell (overbought)
  Close all positions when RSI crosses 50
"""
import trex
from backtest import Strategy
from trex.base.ohlcv import OHLCV


class RSIStrategy(Strategy):
    __author__  = "nasirpoor"
    __version__ = "2.0"

    # ── config ────────────────────────────────────────────────────────────
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0
    leverage  = 10

    _usdt_per_trade: float = 100.0

    # ── step 1: register indicators ───────────────────────────────────────
    def indicators(self):
        trex.rsi(self.symbol, self.timeframe, period=14, listener=self._on_rsi)
        trex.ema(self.symbol, self.timeframe, period=20,  visible=True)

    def _on_rsi(self, value: float):
        self._rsi = value

    # ── step 2: strategy logic per bar ───────────────────────────────────
    def on_kline(self, ohlcv: OHLCV) -> None:
        rsi = getattr(self, "_rsi", None)
        if rsi is None:
            return

        has_position = len(self.positions) > 0

        if rsi < 30 and not has_position:
            _id, msg = self.buy(usdt=self._usdt_per_trade)

        elif rsi > 70 and not has_position:
            _id, msg = self.sell(usdt=self._usdt_per_trade)

        elif 45 < rsi < 55 and has_position:
            self.close()   # close all when RSI is neutral

    # ── optional event hooks ──────────────────────────────────────────────
    def on_position_opened(self, pos):
        print(f"[{pos.open_time}] Position opened: {pos.side.value} @ {pos.entry:.2f}")

    def on_position_profit(self, pos):
        print(f"[{pos.close_time}] TP hit  +${pos.pnl_usdt:.2f}")

    def on_position_loss(self, pos):
        print(f"[{pos.close_time}] SL hit  ${pos.pnl_usdt:.2f}")

    def on_position_closed(self, pos):
        print(f"[{pos.close_time}] Closed  ${pos.pnl_usdt:.2f}")
