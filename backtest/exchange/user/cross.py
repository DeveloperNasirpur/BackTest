from backtest.exchange.dataclass.classdata import Order, PositionCross, BaseUserParameter
from backtest.exchange.dataclass.classdata import PositionCrossEvent, HostEventUser
from trex import OHLCV

class CrossUser( PositionCrossEvent, BaseUserParameter):

    def __init__(
            self,
            user_id: str,
            wallet: float = 0,
            user_event: HostEventUser = None
    ):
        super().__init__(user_id, wallet, user_event)
        self._cross_pnl:float = 0
        self._frees_pnl_online_positions: float = 0.0

    def on_position_long(self, symbol: str, _id: int):
        self.user_event.on_position_long(symbol, _id)

    def on_position_short(self, symbol: str, _id: int):
        self.user_event.on_position_short(symbol, _id)

    def waiting_entry_short(self, symbol: str, _id: int):
        self.user_event.waiting_entry_short(symbol, _id)

    def waiting_entry_long(self, symbol: str, _id: int):
        self.user_event.waiting_entry_long(symbol, _id)

    def _add_position_market(self, order: Order) -> bool:
        order.entry = self.ohlcv.close
        self._online_position[order.id] = PositionCross(order, self.ohlcv.time, self)
        self.user_event.position_opened(self.online_positions[order.id])

        return True

    def order_triggered(self, order: Order, ohlcv: OHLCV):
        pos: PositionCross = PositionCross(order, ohlcv.time, self)
        self._online_position[order.id] = pos
        self._ids_deprecate_order.append(order.id)
        self.user_event.position_opened(pos)

    def position_closed(self, pos: PositionCross):
        pos.close_time = self.ohlcv.time
        self._return_margin_to_balance(pos.margin , pos.pnl_usdt)
        self.user_event.position_closed(pos)
        self._ids_deprecate_position.append(pos.id)

    def position_triggered(self, pos: PositionCross):
        pos.close_time = self.ohlcv.time
        self.user_event.position_triggered(pos)
        self._return_margin_to_balance(pos.margin , pos.pnl_usdt)

        self._ids_deprecate_position.append(pos.id)

    def position_stopped(self, pos: PositionCross):
        pos.close_time = self.ohlcv.time
        self.user_event.position_stopped(pos)
        self._return_margin_to_balance(pos.margin , pos.pnl_usdt)
        self._ids_deprecate_position.append(pos.id)

    def position_higher_loss_pnl(self, _id: int, usdt_pnl: float):
        self._frees_pnl_online_positions += usdt_pnl

    def compute_pnl(self):
        all_balance:float = self._balance + self._frees_balance + self._frees_pnl_online_positions
        if all_balance <= 0 :
            self.user_event.liquid_balance()
            self._balance = 0

        self._frees_pnl_online_positions = 0

    def kline(self, ohlcv: OHLCV):
        super().kline(ohlcv)
        self.compute_pnl()




