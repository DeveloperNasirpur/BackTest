"""
مثال ۷ — دانلود داده واقعی از Binance و بک‌تست
================================================
نیازمندی: اینترنت (بدون API Key)

اجرا:
    python examples/07_binance_data.py
"""
from backtest import Backtest, Strategy, load_binance


class RSIWithRealData(Strategy):
    symbol     = "BTCUSDT"
    timeframe  = "1h"
    capital    = 10_000
    leverage   = 3

    def indicators(self):
        self.rsi = self.add_rsi(period=14)
        self.ema = self.add_ema(period=50)

    def on_kline(self, bar):
        if self.rsi.value is None or self.ema.value is None:
            return

        price = bar.close

        if self.rsi.value < 30 and price > self.ema.value:
            self.buy(usdt=300, stop_pct=0.02, target_pct=0.04)

        elif self.rsi.value > 70 and price < self.ema.value:
            self.sell(usdt=300, stop_pct=0.02, target_pct=0.04)


if __name__ == "__main__":
    # دانلود ۶ ماه آخر داده واقعی از Binance
    print("در حال دانلود داده از Binance...")
    bars = load_binance("BTCUSDT", "1h", days=180)

    result = Backtest(RSIWithRealData).run(bars)
    print(result.summary())
