"""
مثال ۸ — گزارش HTML از نتیجه بک‌تست
======================================
خروجی: یک فایل .html که در مرورگر باز می‌شود
       نمودار equity، آمار کامل، جدول معاملات

اجرا:
    python examples/08_html_report.py
    # سپس: open btcusdt_report.html
"""
from backtest import Backtest, Strategy, CandleSourceBinance, save_report


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
    print("در حال اجرای بک‌تست با داده واقعی Binance...")
    result = Backtest(RSIStrategy).run(
        CandleSourceBinance("BTCUSDT", days=90)
    )

    print(result.summary())

    # ذخیره گزارش HTML
    path = save_report(
        result,
        "btcusdt_report.html",
        title="BTCUSDT RSI Strategy — 90 Days",
    )
    print(f"\nگزارش HTML ذخیره شد: {path}")
    print("در مرورگر باز کنید تا نمودار و جزئیات معاملات را ببینید.")
