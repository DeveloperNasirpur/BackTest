"""
مثال ۷ — داده واقعی Binance + بک‌تست
======================================
نیازمندی: اینترنت (بدون API Key)

جریان داده:
    CandleSourceBinance → on_provide callback → Backtest
    هر bar: trex.push(1m) → CTF → indicator → TrexTerminal
            exchange.kline() → position management
            strategy.on_kline() → user logic

اجرا:
    python examples/07_binance_data.py
"""
from backtest import Backtest, Strategy, CandleSourceBinance


class RSIStrategy(Strategy):
    symbol    = "BTCUSDT"
    timeframe = "1m"
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
    # CandleSourceBinance به عنوان source داده می‌شود — نه list
    # Backtest به صورت خودکار on_provide را تنظیم می‌کند
    result = Backtest(RSIStrategy).run(
        CandleSourceBinance("BTCUSDT", days=90)
    )
    print(result.summary())
