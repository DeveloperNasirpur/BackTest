
from backtest.exchange.dataclass.classdata import Order, PositionIsolate, BaseUserParameter
from backtest.exchange.dataclass.classdata import PositionIsolateEvent, HostEventUser
from backtest.exchange.dataclass.enums import Side
from trex import OHLCV
class IsolateUser(BaseUserParameter, PositionIsolateEvent):

    def __init__(
        self,
        user_id:str,
        wallet:float = 0,
        user_event:HostEventUser = None
    ):

        super().__init__(user_id = user_id, wallet=wallet,
                         user_event=user_event)


    def waiting_entry_short(self, symbol: str, _id: int):
        self.user_event.waiting_entry_short(symbol, _id)

    def waiting_entry_long(self, symbol: str, _id: int):
        self.user_event.waiting_entry_long(symbol, _id)

    def on_position_long(self, symbol: str, _id: int):
        self.user_event.on_position_long(symbol, _id)

    def on_position_short(self, symbol: str, _id: int):
        self.user_event.on_position_short(symbol, _id)


    #----------------Insert Order Market --------------
    def _add_position_market(self, order: Order) -> bool:
        # Apply slippage: long buys slightly higher, short buys slightly lower
        slip = getattr(self, '_slippage', 0.0)
        if order.side == Side.LONG:
            order.entry = self.ohlcv.close * (1 + slip)
        else:
            order.entry = self.ohlcv.close * (1 - slip)
        pos = PositionIsolate(order, self.ohlcv.time, self)
        self._online_position[order.id] = pos
        self.user_event.position_opened(pos)
        return True
    #====================Event Position =============================
    def position_liquidated(self, pos: 'PositionIsolate'):
        pos.close_time = self.ohlcv.time if self.ohlcv else None
        # On liquidation the entire margin is lost
        self._frees_balance -= pos.margin
        self.user_event.position_liquidated(pos)
        self._ids_deprecate_position.append(pos.id)

    def position_triggered(self, pos: 'PositionIsolate'):
        pos.close_time = self.ohlcv.time if self.ohlcv else None
        self._return_margin_to_balance(pos.margin, pos.pnl_usdt)
        self.user_event.position_triggered(pos)
        self._ids_deprecate_position.append(pos.id)

    def position_stopped(self, pos: 'PositionIsolate'):
        pos.close_time = self.ohlcv.time if self.ohlcv else None
        self._return_margin_to_balance(pos.margin, pos.pnl_usdt)
        self.user_event.position_stopped(pos)
        self._ids_deprecate_position.append(pos.id)

    def position_closed(self, pos: PositionIsolate):
        pos.close_time = self.ohlcv.time if self.ohlcv else None
        self._return_margin_to_balance(pos.margin, pos.pnl_usdt)
        self.user_event.position_closed(pos)
        self._ids_deprecate_position.append(pos.id)

    #===========================Order===============================
    def order_triggered(self, order: Order, ohlcv: OHLCV):
        pos: PositionIsolate = PositionIsolate(order, ohlcv.time, self)
        self._online_position[order.id] = pos
        self._ids_deprecate_order.append(order.id)
        self.user_event.position_opened(pos)

    def kline(self, ohlcv: OHLCV):
        super().kline(ohlcv)

