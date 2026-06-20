"""
Example 05 — Real CSV Data
===========================
Shows how to load your own historical candle data from a CSV file
and run a backtest on it.

Expected CSV columns (order does not matter, names are flexible):
    timestamp,open,high,low,close,volume
    1704067200000,42150.0,42300.0,42100.0,42250.0,123.45

Run:
    python examples/05_real_data.py

If you don't have a CSV yet, the script falls back to synthetic data
so you can still see the output format.
"""
import os
import trex
from backtest import Backtest, Strategy, load_csv, demo_candles


class BollingerBreakout(Strategy):
    """
    Price breaks above upper Bollinger Band → Long
    Price breaks below lower Bollinger Band → Short
    Fixed SL/TP in % from entry.
    """
    symbol    = "BTCUSDT"
    timeframe = "1h"
    deposit   = 10_000.0
    leverage  = 3
    broadcast = False

    USDT_PER_TRADE = 400.0
    SL_PCT         = 0.02    # 2 %
    TP_PCT         = 0.04    # 4 %

    def indicators(self):
        trex.bbands(
            self.symbol, self.timeframe,
            period=20, std_dev=2.0,
            listener=self._on_bb,
            visible=True,
        )

    def _on_bb(self, upper: float, middle: float, lower: float):
        self._prev_price = getattr(self, "_cur_price", None)
        self._upper = upper
        self._lower = lower

    def on_kline(self, ohlcv):
        upper = getattr(self, "_upper", None)
        lower = getattr(self, "_lower", None)
        if None in (upper, lower):
            return

        price   = ohlcv.close
        has_pos = bool(self.positions)

        if price > upper and not has_pos:
            sl = price * (1 - self.SL_PCT)
            tp = price * (1 + self.TP_PCT)
            self.buy(usdt=self.USDT_PER_TRADE, sl=sl, tp=tp)

        elif price < lower and not has_pos:
            sl = price * (1 + self.SL_PCT)
            tp = price * (1 - self.TP_PCT)
            self.sell(usdt=self.USDT_PER_TRADE, sl=sl, tp=tp)

    def on_position_profit(self, pos):
        print(f"  ✔  +${pos.pnl_usdt:,.2f}")

    def on_position_loss(self, pos):
        print(f"  ✘  ${pos.pnl_usdt:,.2f}")


if __name__ == "__main__":
    print("Bollinger Band Breakout Strategy")
    print("─" * 40)

    CSV_PATH = "data/BTCUSDT_1h.csv"

    if os.path.exists(CSV_PATH):
        print(f"Loading real data from {CSV_PATH} …")
        # load_csv auto-detects column names and timestamp format (unix ms/s or ISO)
        candles = load_csv(
            CSV_PATH,
            symbol="BTCUSDT",
            timeframe="1h",
            # Override column names if yours differ:
            # time_col="open_time", open_col="open", ...
        )
        print(f"Loaded {len(candles):,} candles")
    else:
        print(f"[demo] {CSV_PATH} not found — using synthetic 1h data instead")
        # Switch strategy to 1h for consistency
        candles = demo_candles(
            bars=2_000,
            timeframe="1h",
            volatility=0.008,
            trend=0.0002,
            seed=55,
        )

    result = Backtest(BollingerBreakout).run(candles)
    print(result)
