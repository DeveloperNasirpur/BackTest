import logging
import uuid
from typing import Union, Callable, Iterable
from backtest.exchange.dataclass.classdata import PositionIsolate, Order, PositionCross
from backtest.exchange.dataclass.enums import Side, OrderType
from backtest.exchange.dataclass.classdata import HostEventUser, Api
from backtest.exchange.user.cross import CrossUser
from backtest.exchange.user.isolate import IsolateUser
from trex import OHLCV

logger = logging.getLogger("Exchange")

def _valid_order(side:Side, entry:float, stop:float = None, target:float =None)->tuple[bool, str] :
    msg_error_order:str = ""
    res:bool = True
    if Side.SHORT.value.__eq__(side.value):
        if stop:
            if stop < entry:
                msg_error_order+="Stop is lowing than entry."
                res = False
        if target:
            if target > entry:
                msg_error_order+="Target is higher than entry."
                res = False
        return res, msg_error_order
    if stop:
        if stop > entry:
            msg_error_order+="Stop is higher than entry."
            res = False
    if target:
        if target < entry:
            msg_error_order+="Target is lower than entry."
            res = False
    return res, msg_error_order


class Exchange(Api):
    def __init__(
        self,
        symbols: list[str],
        taker_fee: float = 0.0004,   # 0.04% per trade (Binance default)
        slippage: float = 0.0001,    # 0.01% price slippage on market orders
    ):
        super().__init__()
        self.symbols: list[str] = symbols
        self.ohlcv: OHLCV | None = None
        self._users: dict[str, Union[IsolateUser, CrossUser]] = {}
        self.taker_fee: float = taker_fee
        self.slippage: float = slippage
        self._initial_deposits: dict[str, float] = {}

    def change_to_isolated(self, symbol: str, user_id: str, event_host:HostEventUser) -> tuple[bool,str]:
        self.valid_user(user_id)
        if isinstance(self._users[user_id], IsolateUser):
            return False, "Margin Type is Isolated"

        perv_pipe_line: CrossUser = self._users[user_id]

        if perv_pipe_line.online_orders.__len__() > 0 \
                or perv_pipe_line.online_positions.__len__() > 0:
            return False, "For Change Margin Type Must Cancel All Order And close All Position"

        pipe_line:IsolateUser = IsolateUser(user_id = user_id,
                                            wallet= perv_pipe_line.balance(),
                                            user_event= perv_pipe_line.user_event
                                            )
        pipe_line.upload_pipe_line(perv_pipe_line)
        del perv_pipe_line
        self._users[user_id] = pipe_line

        return True, "Margin Type is Change To Isolated"

    def change_to_cross(self, user_id: str, event_host: HostEventUser) -> tuple[bool, str]:
        self.valid_user(user_id)
        if isinstance(self._users[user_id], CrossUser):
            return False, "Margin Type is Isolated"

        perv_pipe_line: IsolateUser = self._users[user_id]

        if perv_pipe_line.online_orders.__len__() > 0 \
                or perv_pipe_line.online_positions.__len__() > 0:
            return False, "For Change Margin Type Must Cancel All Order And close All Position"

        pipe_line: CrossUser = CrossUser(user_id=user_id,
                                         wallet=perv_pipe_line.balance(),
                                         user_event=perv_pipe_line.user_event
                                         )
        pipe_line.upload_pipe_line(perv_pipe_line)
        del perv_pipe_line
        self._users[user_id] = pipe_line

        return True, "Margin Type is Change To Cross"


    def valid_user(self, user_id: str) -> bool:
        if  user_id not in self._users.keys():
            raise f"{user_id} is not singUp"
        return True

        # ==================================================================================
        # =
        # =                      ACCOUNT HOST
        # ==================================================================================

    def sing_up(self, user_event: HostEventUser) -> str:
        user_id: str = str(int(uuid.uuid4().int % 10 ** 18))
        user = IsolateUser(user_id=user_id, wallet=0, user_event=user_event)
        user._taker_fee = self.taker_fee
        user._slippage = self.slippage
        self._users[user_id] = user
        return user_id

    def deposit(self, user_id: str, usdt: float) -> bool:
        self.valid_user(user_id)
        self._users[user_id].deposit(usdt)
        self._initial_deposits[user_id] = (
            self._initial_deposits.get(user_id, 0.0) + usdt
        )
        return True

    def get_balance(self, user_id: str) -> float:
        self.valid_user(user_id)
        return self._users[user_id].balance()

    def get_positions(self, symbol: str = None, user_id: str = "", side: str = None) \
            -> list[Union[PositionIsolate, PositionCross]]:
        self.valid_user(user_id)
        positions = list(self._users[user_id].online_positions.values())
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        if side:
            positions = [p for p in positions if p.side.value == side]
        return positions


    def get_history_positions(self, symbol: str = None, user_id: str = None, start_time: int = None,
                              end_time: int = None, limit: int = 20) -> list:
        self.valid_user(user_id)
        all_pos = list(self._users[user_id].history_positions.values())
        pos: list[Union[PositionIsolate, PositionCross]] = \
            [p for p in all_pos if p.symbol == symbol] if symbol else all_pos
        res: list[Union[PositionIsolate, PositionCross]] = []
        if start_time and end_time:
            for p in pos:
                if end_time >= p.open_time.timestamp() >= start_time:
                    res.append(p)
            return res
        if start_time:
            for p in pos:
                if p.open_time.timestamp() >= start_time:
                    res.append(p)
            return res
        if end_time:
            for p in pos:
                if end_time >= p.open_time.timestamp():
                    res.append(p)
            return res
        return pos

    def get_leverage_info(self, user_id: str, symbol: str) -> int:
        self.valid_user(user_id)
        return self._users[user_id].leverage(symbol)

    def change_leverage(self, symbol: str, user_id: str, leverage: int) -> bool:
        self.valid_user(user_id)
        self._users[user_id].set_leverage(symbol, leverage)
        return True

    # ==================================================================================
    # =
    # =                      MARKET HOST
    # ==================================================================================
    def kline(self, ohlcv: OHLCV):
        self.ohlcv = ohlcv
        for pl in self._users.values():
            pl.kline(ohlcv)

    # ==================================================================================
   # =
   # =                      ORDER HOST
   # ==================================================================================
    def place_order(self, symbol: str, user_id: str, side: Side, order_type: OrderType =None,
                    usdt: float = 0, entry: float = None, stop_price: float = None, take_profit: float = None
                    ) -> tuple[bool, int]:
        self.valid_user(user_id)
        res, msg = _valid_order(side, entry, stop_price, take_profit)
        if not res:
            return False, msg

        _id:int = uuid.uuid4().int
        order:Order = Order(self._users[user_id])
        order.id = _id
        order.symbol = symbol
        order.side = side
        order.order_type = order_type if order_type else( OrderType.MARKET if not entry else OrderType.LIMIT)
        order.usdt = usdt
        order.entry = entry
        order.stop_price = stop_price
        order.take_profit = take_profit
        order.placed_time = self.ohlcv.time
        res,msg = self._users[user_id].add_order( order)
        logger.info(msg)

        if res:
            return True, _id
        return False, 0

    def modify_order(
            self,
            user_id: str,
            order_id:int,
            side: Side,
            order_type: OrderType,
            usdt: float = 0,
            entry: float = None,
            stop_price: float = None,
            take_profit: float = None,
    ) -> tuple[bool, str]:
        self.valid_user(user_id)
        return self._users[user_id].modify_order(
            order_id=order_id,
            side=side,
            order_type=order_type,
            usdt=usdt,
            entry=entry,
            stop_price=stop_price,
            take_profit=take_profit
        )

    def _create_order(self, symbol: str, user_id: str, usdt:float, entry: float = None,stop_price: float = None,
            take_profit: float = None,) -> Order:
        self.valid_user(user_id)
        _id: int = uuid.uuid4().int
        order: Order = Order(self._users[user_id])
        order.id = _id
        order.symbol = symbol
        order.order_type = OrderType.MARKET if not entry else OrderType.LIMIT
        order.stop_price = stop_price
        order.take_profit = take_profit
        order.usdt = usdt if usdt else 0.0
        order.entry = entry
        return order

    def open_long(self,
                  symbol: str, user_id: str,  usdt:float, entry: float = None,
                  stop_price: float = None,
                  take_profit: float = None,
                  ) -> tuple[int, str]:
        self.valid_user(user_id)

        order:Order = self._create_order(
            symbol, user_id, usdt, entry,stop_price, take_profit)
        order.side = Side.LONG
        res, msg = self._users[user_id].add_order(
           order
        )
        if res:
            return 0, msg
        return order.id, msg

    def close_position(
            self,
            user_id: str,
            _id: int = None
    ) ->tuple[ bool, str]:
        self.valid_user(user_id)
        res = self._users[user_id].close_position(_id)
        if res:
            return True, "Position by Id {} is Closed".format(_id)
        return False, "Position Invalid Id {}".format(_id)

    def open_short(
            self,
            symbol: str,
            user_id,
            usdt:float,
            entry: float = None,stop_price: float = None,
            take_profit: float = None) -> tuple[int, str]:
        self.valid_user(user_id)
        order: Order = self._create_order(
            symbol, user_id, usdt, entry, stop_price, take_profit)
        order.side = Side.SHORT
        res, msg = self._users[user_id].add_order(
            order
        )
        if res:
            return 0, msg
        return order.id, msg

    def set_target(
            self,
            user_id: str,
            _id: int = None,
            stop: float = None,
            tp: float = None
    ) -> tuple[bool, str]:
        self.valid_user(user_id)
        if self._users[user_id].valid_order_id(_id):
            return self._users[user_id].modify_order(order_id=_id, take_profit=tp, stop_price=stop)
        else:
            return self._users[user_id].modify_position(pos_id=_id, tp=tp, stop=stop)

    def cancel_order(
            self,
            user_id: str,
            order_id: int = None
    ) -> tuple[bool, str]:
        self.valid_user(user_id)
        return self._users[user_id].cancel_order(order_id)

    def get_orders(self, user_id:str, symbol:str) -> list['Order']:
        self.valid_user(user_id)
        return self._users[user_id].get_orders(symbol)

    def run(
        self,
        candles: Iterable[OHLCV],
        on_bar: Callable[[OHLCV], None] | None = None,
        progress: bool = True,
    ) -> "BacktestResult":
        """
        Feed all candles through the exchange and return statistics.

        Args:
            candles:  Iterable of OHLCV bars (list, generator, CSV loader…)
            on_bar:   Optional callback called with each bar BEFORE orders/positions
                      are processed — use it to run indicator logic and place orders.
            progress: Print a progress line every 10,000 bars.
        """
        from backtest.stats import BacktestResult
        candle_list = list(candles)
        total = len(candle_list)
        for i, bar in enumerate(candle_list):
            if on_bar:
                on_bar(bar)
            self.kline(bar)
            if progress and total >= 10_000 and (i + 1) % 10_000 == 0:
                pct = (i + 1) / total * 100
                print(f"[backtest] {i+1:,}/{total:,} bars ({pct:.1f}%)")

        if progress:
            print(f"[backtest] Done — {total:,} bars processed")

        return BacktestResult.from_exchange(self)

    def start(self):
        """Alias kept for backward compatibility. Use run() instead."""
        raise NotImplementedError("Use exchange.run(candles) to start a backtest.")


