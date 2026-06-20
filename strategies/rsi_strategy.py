"""
RSI Strategy — sample strategy using trex indicators
  RSI < 30 → open Long
  RSI > 70 → open Short
"""
from backtest.exchange.dataclass.classdata import StrategyBase, Order, PositionIsolate
from backtest.exchange.dataclass.enums import Side
from trex.base.ohlcv import OHLCV


class RSIStrategy(StrategyBase):
    __author__ = "nasirpoor"
    __version__ = "2.0"

    def __init__(self):
        self._rsi_value: float | None = None
        self._usdt_per_trade: float = 100.0
        # exchange and user_id are wired externally (see main.py)
        self.exchange = None
        self.user_id = None

    # ── trex listener: called every time RSI is computed ─────────────────────
    def on_rsi(self, value: float) -> None:
        self._rsi_value = value

    # ── called by exchange.run() via on_bar before each candle ───────────────
    def on_kline(self, ohlcv: OHLCV) -> None:
        if self._rsi_value is None or self.exchange is None:
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

    # ── required abstract stubs ───────────────────────────────────────────────
    def indicators(self): pass
    def idle(self, ohlcv: OHLCV): pass
    def finder(self): pass
    def complete_provide(self): pass

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
    def position_opened(self, pos): pass
    def liquid_balance(self): pass
    def deposited(self, balance: float): pass
    def new_balance(self, balance: float): pass
    def order_history(self, orders): pass
    def position_history(self, pos): pass
    def order_online(self, orders): pass
    def position_online(self, pos): pass
