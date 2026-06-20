"""
main.py — نقطه شروع backtest با trex indicator engine
"""
import trex
from trex.domain.types import Bar
from backtest import Exchange
from strategies.rsi_strategy import RSIStrategy

SYMBOL   = "BTCUSDT"
TIMEFRAME = "1m"

# ── ۱. شروع trex (بدون DB: فقط live broadcast به TrexTerminal) ───────────────
strategy = RSIStrategy()

trex.init(
    port=8765,
    source_timeframe=TIMEFRAME,
    # db_config=...  ← اگه دیتابیس داری اینجا اضافه کن
)

trex.rsi(
    SYMBOL, TIMEFRAME,
    period=14,
    visible=True,
    listener=strategy.on_rsi,   # هر بار RSI حساب شد → استراتژی خبردار میشه
)
trex.ema(SYMBOL, TIMEFRAME, period=20, visible=True)

# ── ۲. Exchange و ثبت‌نام استراتژی ──────────────────────────────────────────
exchange = Exchange(symbols=[SYMBOL])
user_id  = exchange.sing_up(strategy)
exchange.deposit(user_id, 10_000)   # ۱۰,۰۰۰ دلار سرمایه اولیه

strategy.exchange = exchange
strategy.user_id  = user_id

# ── ۳. لود کندل‌ها (اینجا از فایل CSV نمونه — جای DB خودت رو بذار) ──────────
def load_candles(symbol: str):
    """
    اینجا کندل‌هات رو بده.
    میتونه از CSV، PostgreSQL، یا هر منبع دیگه‌ای باشه.
    خروجی: list of trex.domain.types.Bar
    """
    # مثال — جای این با کد واقعی خودت عوض کن:
    # return db.fetch_bars("binance", symbol, "1m")
    raise NotImplementedError("کندل‌ها رو از منبع خودت لود کن")

# ── ۴. لوپ اصلی backtest ────────────────────────────────────────────────────
candles = load_candles(SYMBOL)
print(f"[backtest] {len(candles)} کندل لود شد — شروع بک‌تست...")

for bar in candles:
    # به trex بده → اندیکاتور حساب میشه + به TrexTerminal broadcast میشه
    trex.push(bar, symbol=SYMBOL)

    # به exchange بده → استراتژی کندل رو دریافت میکنه
    from trex.base.ohlcv import OHLCV
    ohlcv = OHLCV.from_bar(bar, symbol=SYMBOL, str_time=TIMEFRAME)
    exchange.kline(ohlcv)
    strategy.on_kline(ohlcv)

print("[backtest] تمام شد!")
print(f"[backtest] موجودی نهایی: ${exchange.get_balance(user_id):,.2f}")
