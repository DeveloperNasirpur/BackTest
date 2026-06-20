"""
RSI Strategy — نمونه استراتژی با اندیکاتور trex
- RSI < 30 → Long
- RSI > 70 → Short
"""
from backtest.exchange.dataclass.classdata import StrategyBase, Order, PositionIsolate
from backtest.exchange.dataclass.enums import Side
from trex.base.ohlcv import OHLCV


class RSIStrategy(StrategyBase):
    __author__ = "nasirpoor"
    __version__ = "1.0"

    def __init__(self):
        self._rsi_value: float | None = None
        self._usdt_per_trade: float = 100.0

    # ── trex listener: هر بار RSI حساب میشه اینجا صدا زده میشه ──────────────
    def on_rsi(self, value: float) -> None:
        self._rsi_value = value

    # ── هر کندل جدید ──────────────────────────────────────────────────────────
    def on_kline(self, ohlcv: OHLCV) -> None:
        if self._rsi_value is None:
            return

        symbol = ohlcv.symbol or "BTCUSDT"

        if self._rsi_value < 30:
            self.exchange.open_long(
                symbol=symbol,
                user_id=self.user_id,
                usdt=self._usdt_per_trade,
            )

        elif self._rsi_value > 70:
            self.exchange.open_short(
                symbol=symbol,
                user_id=self.user_id,
                usdt=self._usdt_per_trade,
            )

    # ── event های اجباری ──────────────────────────────────────────────────────
    def on_position_long(self, symbol: str, _id: int): pass
    def on_position_short(self, symbol: str, _id: int): pass
    def waiting_entry_short(self, symbol: str, _id: int): pass
    def waiting_entry_long(self, symbol: str, _id: int): pass
    def order_cancelled(self, order: Order): pass
    def order_triggered(self, order: Order, ohlcv: OHLCV): pass
    def position_closed(self, pos: PositionIsolate): pass
    def position_triggered(self, pos: PositionIsolate): pass
    def position_stopped(self, pos: PositionIsolate): pass
    def position_liquidated(self, pos: PositionIsolate): pass
