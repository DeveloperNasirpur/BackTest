"""
مثال ۸ — گزارش HTML از نتیجه بک‌تست
======================================
خروجی: یک فایل .html که در مرورگر باز می‌شود

اجرا:
    python examples/08_html_report.py
    open btcusdt_report.html
"""
from backtest import Backtest, Strategy, load_binance, save_report


class RSIStrategy(Strategy):
    symbol    = "BTCUSDT"
    timeframe = "1h"
    capital   = 10_000
    leverage  = 3

    def indicators(self):
        self.rsi = self.add_rsi(period=14)
        self.ema = self.add_ema(period=50)

    def on_kline(self, bar):
        if self.rsi.value is None or self.ema.value is None:
            return
        if self.rsi.value < 30 and bar.close > self.ema.value:
            self.buy(usdt=300, stop_pct=0.02, target_pct=0.04)
        elif self.rsi.value > 70 and bar.close < self.ema.value:
            self.sell(usdt=300, stop_pct=0.02, target_pct=0.04)


if __name__ == "__main__":
    print("در حال دانلود داده از Binance...")
    bars = load_binance("BTCUSDT", "1h", days=90)

    result = Backtest(RSIStrategy).run(bars)
    print(result.summary())

    path = save_report(
        result,
        "btcusdt_report.html",
        title="BTCUSDT RSI Strategy — 90 Days",
    )
    print(f"\nگزارش HTML ذخیره شد: {path}")
