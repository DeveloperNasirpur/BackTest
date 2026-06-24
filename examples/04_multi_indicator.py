"""
Example 04 — Multi-Indicator Confluence
========================================
Combines three indicators for stronger signals:
  RSI for overbought/oversold
  EMA trend filter (only trade with the trend)
  ATR for dynamic stop-loss sizing

Long  when: RSI < 35  AND  price > EMA-50  (uptrend)
Short when: RSI > 65  AND  price < EMA-50  (downtrend)
Stop-loss:  1.5× ATR from entry (dynamic, not fixed)

Run:
    python examples/04_multi_indicator.py
"""
import trex
from backtest import Backtest, Strategy, demo_candles


class ConfluenceStrategy(Strategy):
    symbol    = "BTCUSDT"
    timeframe = "1m"
    deposit   = 10_000.0
    leverage  = 5
    broadcast = False

    RISK_USDT = 250.0   # fixed dollar risk per trade
    ATR_MULT  = 1.5     # stop = 1.5 × ATR
    RR        = 2.0     # reward : risk

    def indicators(self):
        trex.rsi(self.symbol, self.timeframe, period=14,  listener=self._on_rsi)
        trex.ema(self.symbol, self.timeframe, period=50,  listener=self._on_ema, visible=True)
        trex.atr(self.symbol, self.timeframe, period=14,  listener=self._on_atr)

    def _on_rsi(self, v): self._rsi = v
    def _on_ema(self, v): self._ema = v
    def _on_atr(self, v): self._atr = v

    def on_kline(self, ohlcv):
        rsi = getattr(self, "_rsi", None)
        ema = getattr(self, "_ema", None)
        atr = getattr(self, "_atr", None)
        if None in (rsi, ema, atr):
            return

        price   = ohlcv.close
        has_pos = bool(self.positions)
        sl_dist = atr * self.ATR_MULT

        # Long: oversold + above EMA trend filter
        if rsi < 35 and price > ema and not has_pos:
            sl = price - sl_dist
            tp = price + sl_dist * self.RR
            self.buy(usdt=self.RISK_USDT, sl=sl, tp=tp)

        # Short: overbought + below EMA trend filter
        elif rsi > 65 and price < ema and not has_pos:
            sl = price + sl_dist
            tp = price - sl_dist * self.RR
            self.sell(usdt=self.RISK_USDT, sl=sl, tp=tp)

    def on_position_opened(self, pos):
        atr = getattr(self, "_atr", 0)
        print(f"  ▶  {pos.side.value:5s} @ {pos.entry:,.2f}  "
              f"SL={pos.stop_price:,.2f}  ATR={atr:.2f}")

    def on_position_profit(self, pos):
        print(f"  ✔  TP  +${pos.pnl_usdt:,.2f}   balance=${self.balance:,.2f}")

    def on_position_loss(self, pos):
        print(f"  ✘  SL  ${pos.pnl_usdt:,.2f}   balance=${self.balance:,.2f}")


if __name__ == "__main__":
    print("RSI + EMA + ATR Confluence Strategy")
    print("─" * 40)
    candles = demo_candles(bars=6_000, volatility=0.002, trend=0.00003, seed=21)
    result  = Backtest(ConfluenceStrategy).run(candles)
    print(result)
