from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Union
from backtest.exchange.dataclass.enums import Side, OrderType, PositionState
from trex.base.ohlcv import OHLCV

class BasePositionEvent(ABC):
    @abstractmethod
    def on_position_long(self, symbol: str, _id: int): pass

    @abstractmethod
    def on_position_short(self, symbol: str, _id: int): pass

class PositionIsolateEvent( BasePositionEvent):
    @abstractmethod
    def position_closed(self, pos: 'PositionIsolate'): pass

    @abstractmethod
    def position_triggered(self, pos: 'PositionIsolate'): pass

    @abstractmethod
    def position_stopped(self, pos: 'PositionIsolate'): pass

    @abstractmethod
    def position_liquidated(self, pos: 'PositionIsolate'): pass

class PositionCrossEvent(BasePositionEvent):

    @abstractmethod
    def position_closed(self, pos: 'PositionCross'): pass

    @abstractmethod
    def position_triggered(self, pos: 'PositionCross'): pass

    @abstractmethod
    def position_stopped(self, pos: 'PositionCross'): pass

    @abstractmethod
    def position_higher_loss_pnl(self, _id: int, usdt_pnl: float): pass


#==========================Event Orders ===========================
class OrderEvent(ABC):
    @abstractmethod
    def waiting_entry_short(self, symbol: str, _id: int):pass

    @abstractmethod
    def waiting_entry_long(self, symbol: str, _id: int): pass

    @abstractmethod
    def order_cancelled(self, order:'Order'): pass

    @abstractmethod
    def order_triggered(self, order:'Order', ohlcv:OHLCV):pass
# ============================================================================

#For Base Strategy listener
class HostEventUser(OrderEvent,BasePositionEvent):

    def order_placed(self, order: 'Order'): pass

    # def order_canceled(self, order: 'Order'): pass

    @abstractmethod
    def position_opened(self, pos: Union['PositionCross','PositionIsolate']): pass

    @abstractmethod
    def position_closed(self, pos: Union['PositionCross','PositionIsolate']): pass

    @abstractmethod
    def position_triggered(self, pos: Union['PositionCross','PositionIsolate']): pass

    @abstractmethod
    def position_stopped(self, pos: Union['PositionCross','PositionIsolate']): pass

    @abstractmethod
    def position_liquidated(self, pos: Union['PositionCross','PositionIsolate']): pass

    @abstractmethod
    def liquid_balance(self): pass

    @abstractmethod
    def deposited(self, balance: float): pass

    @abstractmethod
    def new_balance(self, balance: float): pass

    @abstractmethod
    def order_history(self, orders: dict[int, 'Order']): pass

    @abstractmethod
    def position_history(self, pos: dict[int, Union['PositionCross','PositionIsolate']]): pass

    @abstractmethod
    def order_online(self, orders: dict[int, 'Order']): pass

    @abstractmethod
    def position_online(self, pos: dict[int, Union['PositionCross','PositionIsolate']]): pass

class OrderHost(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def place_order(
            self,
            symbol: str,
            user_id: str,
            side: Side,
            order_type: OrderType = None,
            usdt: float = 0,
            entry: float = None,
            stop_price: float = None,
            take_profit: float = None,
    ) -> tuple[bool,str]: pass

    @abstractmethod
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
    ) -> bool: pass

    @abstractmethod
    def open_long(
            self,
            symbol: str,
            user_id: str,
            usdt: float,
            price: float = None,
            stop_price: float = None,
            take_profit: float = None,
    ) -> tuple[int, str]: pass

    @abstractmethod
    def close_position(
            self,
            user_id: str,
            _id: int = None
    ) ->tuple[ bool, str]: pass

    @abstractmethod
    def open_short(
            self,
            symbol: str,
            user_id,
            usdt:float,
            entry: float = None,
            stop_price: float = None,
            take_profit: float = None
    ) -> tuple[ int, str]: pass



    @abstractmethod
    def set_target(
            self,
            user_id: str,
            _id: int = None,
            stop: float = None,
            tp:float = None
    ) -> tuple[bool, str]: pass

    @abstractmethod
    def cancel_order(
            self,
            user_id: str,
            order_id: int = None
    ) -> tuple[bool, str]: pass

class MarketHost(ABC):
    def __init__(self): pass

    @abstractmethod
    def kline(
            self,
            ohlcv: OHLCV): pass

class AccountHost(ABC):
    def __init__(self): pass

    @abstractmethod
    def sing_up(self, user_event: HostEventUser) -> str: pass

    @abstractmethod
    def get_balance(
            self,
            user_id: str
    ) -> float: pass

    @abstractmethod
    def get_positions(
            self,
            symbol: str = None,
            user_id: str = "",
            side: str = None
    ) -> list[Union['PositionIsolate','PositionCross']]: pass

    @abstractmethod
    def get_orders(self, user_id:str, symbol:str) -> list['Order']:
        pass

    @abstractmethod
    def get_history_positions(
            self,
            symbol: str = None,
            user_id: str = None,
            start_time: int = None,
            end_time: int = None,
            limit: int = 20,
    ) -> list: pass

    @abstractmethod
    def get_leverage_info(
            self,
            user_id: str,
            symbol: str
    ) -> int: pass

    @abstractmethod
    def change_leverage(
            self,
            symbol: str,
            user_id: str,
            leverage: int
    ) -> bool: pass

    @abstractmethod
    def change_to_cross(
            self,
            user_id: str
            , event_host: HostEventUser
    ) -> tuple[bool,str]: pass

    @abstractmethod
    def change_to_isolated(
            self,
            symbol: str,
            user_id: str
            , event_host: HostEventUser
    ) -> tuple[bool,str]: pass

    @abstractmethod
    def deposit(
            self,
            user_id: str,
            usdt: float
    ) -> bool: pass

class Api( OrderHost, MarketHost, AccountHost,ABC):pass

import logging
logger = logging.getLogger("Exchange")

class MarginState(str, Enum):
    NONE = "None"
    ON_ORDER = "ON_ORDER"
    ON_POSITION = "ON_POSITION"
#-----------------------------------------------
class CapitalBase(ABC):
    def __init__(self, balance:float):
        self._balance:float = balance

    @abstractmethod
    def new_margin(self,order:'Order')->float:pass

    @abstractmethod
    def profit(self, pos:'BasePosition'):pass

    @abstractmethod
    def loss(self, pos:'BasePosition'):pass

    @abstractmethod
    def cancel_ordered(self, order:'Order'):pass

class StrategyBase( HostEventUser, ABC):

    def __init__(self, exchange: Api,  symbol:str, deposit:float = 100):
        self.first_deposit:float = deposit
        self.exchange: Api = exchange
        self.symbol = symbol
        self.user_id:str = self.exchange.sing_up(self)
        self.exchange.deposit(self.user_id, deposit)
        self.margin_state: str = MarginState.NONE.value
        self.indicators()

    @abstractmethod
    def indicators(self):
        pass

    @abstractmethod
    def idle(self, ohlcv:OHLCV): pass

    @abstractmethod
    def finder(self):pass

    @abstractmethod
    def complete_provide(self):
        ...

    # PipeLineHost Interface
    def order_placed(self, order: 'Order'):

        self.margin_state = MarginState.ON_ORDER.value
        logger.info("Order {} Placed in time {}".format(order.side.value, order.placed_time))

    def order_cancelled(self, order: 'Order'):
        self.margin_state = MarginState.NONE.value
        logger.info("Order {} Canceled in time {}".format(order.side.value, order.placed_time))

    def position_opened(self, pos: Union['PositionCross', 'PositionIsolate']):

        logger.info("Position {} Opened in time {}".format(
            pos.side.value, pos.open_time))
        self.margin_state = MarginState.ON_POSITION.value

    def liquid_balance(self):
        pass

    def deposited(self, balance: float):
        self.first_deposit = balance

    def new_balance(self, balance: float):
        pass

    def order_history(self, orders: dict[int, 'Order']):
        pass

    def position_history(self, pos: dict[int, Union['PositionCross', 'PositionIsolate']]):
        pass

    def order_online(self, orders: dict[int, 'Order']):
        pass

    def position_online(self, pos: dict[int, Union['PositionCross', 'PositionIsolate']]):
        pass

    def _reset_process(self):
        self.balance = self.exchange.get_balance(self.user_id)
        self.margin_state = MarginState.NONE.value

    def position_closed(self, pos: Union['PositionCross', 'PositionIsolate']):
        self._reset_process()

    def position_triggered(self, pos: Union['PositionCross', 'PositionIsolate']):
        self._reset_process()

    def position_stopped(self, pos: Union['PositionCross', 'PositionIsolate']):
        self._reset_process()

    def position_liquidated(self, pos: Union['PositionCross', 'PositionIsolate']):
        self._reset_process()

# ============================================================
@dataclass
class Order:
    id:int = 0
    symbol:str = ""
    side:Side = Side.LONG
    order_type:OrderType = OrderType.LIMIT
    entry:float = 0
    usdt:float= 0
    stop_price: float = None
    take_profit: float = None
    event: OrderEvent = None
    leverage = 10
    triggered_time:datetime = None
    placed_time:datetime = None

    def __init__(self, callback: OrderEvent):
        self.event = callback

    def kline(self, ohlcv: OHLCV):
        if self.side == Side.SHORT:
            self._trigger_short(ohlcv)
        else:
            self._trigger_long(ohlcv)

    def _trigger_short(self, ohlcv:OHLCV) :
        if   ohlcv.high >= self.entry:
            self.triggered_time = ohlcv.time
            self.event.order_triggered(self, ohlcv)
            return
        self.event.waiting_entry_short(self.symbol,self.id)

    def _trigger_long(self, ohlcv:OHLCV):
        if ohlcv.low <= self.entry:
            self.triggered_time = ohlcv.time
            self.event.order_triggered(self, ohlcv)
            return
        self.event.waiting_entry_long(self.symbol,self.id)

class ComputePosition:
    def __init__(self, position:Union['PositionIsolate', 'PositionCross'] = None):
        self.position:Union['PositionIsolate', 'PositionCross']  = position
        self.update_pnl:Callable[[OHLCV],None] = self._update_pnl_long
        self.stopped:Callable[[OHLCV],bool] = self._stopped_long
        self.triggered: Callable[[OHLCV],bool] = self._trigger_target_long
        self.pnl_higher:Callable[[OHLCV], float]  = self._upper_loss_pnl_long
        self.close_position:Callable[[OHLCV], None]  = self._close_long

        if self.position.side.value.__eq__(Side.SHORT.value):
            self.update_pnl = self._update_pnl_short
            self.stopped = self._stopped_short
            self.triggered = self._trigger_target_short
            self.pnl_higher = self._upper_loss_pnl_short
            self.close_position = self._close_short

    def _pnl_short(self, price:float):
        self.position.pnl = round((self.position.entry - price) / self.position.entry, 4)
        self.position.pnl_usdt = (self.position.pnl * self.position.leverage) * self.position.margin

    def _pnl_long(self, price:float):
        self.position.pnl = round((price - self.position.entry) / self.position.entry, 4)
        self.position.pnl_usdt = (self.position.pnl * self.position.leverage) * self.position.margin

    def _update_pnl_short(self, ohlcv: OHLCV) :
        self._pnl_short(ohlcv.close)

    def _update_pnl_long(self, ohlcv: OHLCV) :
        self._pnl_long(ohlcv.close)

    def _upper_loss_pnl_short(self, ohlcv: OHLCV) -> float:
        _pnl = round((self.position.entry - ohlcv.high) / self.position.entry, 4)
        self.position.higher_loss = min(_pnl, self.position.higher_loss)
        return (_pnl * self.position.leverage) * self.position.margin

    def _upper_loss_pnl_long(self, ohlcv: OHLCV) -> float :
        _pnl = round((ohlcv.low - self.position.entry) / self.position.entry, 4)
        self.position.higher_loss = min(_pnl, self.position.higher_loss)
        return (_pnl * self.position.leverage) * self.position.margin

    def _stopped_short(self, ohlcv:OHLCV)-> bool :
        if self.position.stop_price:
            if ohlcv.high >= self.position.stop_price:
                self.position.state = PositionState.STOPPED
                self._pnl_short(self.position.stop_price)
                self.position.event_callback.position_stopped(self.position)
                return True
        return False

    def _stopped_long(self, ohlcv: OHLCV) -> bool:
        if self.position.stop_price:
            if ohlcv.low <= self.position.stop_price:
                self.position.state = PositionState.STOPPED
                self._pnl_long(self.position.stop_price)
                self.position.event_callback.position_stopped(self.position)
                return True
        return False

    def _trigger_target_short(self, ohlcv: OHLCV) -> bool:
        if self.position.take_profit:
            if ohlcv.low <= self.position.take_profit:
                self.position.state = PositionState.TRIGGERED
                self._pnl_short(self.position.take_profit)
                self.position.event_callback.position_triggered(self.position)
                return True
        self.position.event_callback.on_position_short(self.position.symbol, self.position.id)
        return False

    def _trigger_target_long(self, ohlcv: OHLCV) -> bool:
        if self.position.take_profit:
            if ohlcv.high >= self.position.take_profit:
                self.position.state = PositionState.TRIGGERED
                self._pnl_long(self.position.take_profit)
                self.position.event_callback.position_triggered(self.position)
                return True
        self.position.event_callback.on_position_long(self.position.symbol, self.position.id)
        return False

    def _close_short(self, ohlcv:OHLCV):
        self._pnl_short(ohlcv.close)
        if ohlcv.close < self.position.entry:
            self.position.state = PositionState.TRIGGERED_BY_CLOSE
            self.position.event_callback.position_triggered(self.position)
            return
        self.position.state = PositionState.STOPPED_BY_CLOSE
        self.position.event_callback.position_stopped(self.position)

    def _close_long(self, ohlcv:OHLCV):
        self._pnl_long(ohlcv.close)
        if ohlcv.close > self.position.entry:
            self.position.state = PositionState.TRIGGERED_BY_CLOSE
            self.position.event_callback.position_triggered(self.position)
            return
        self.position.state = PositionState.STOPPED_BY_CLOSE
        self.position.event_callback.position_stopped(self.position)

@dataclass
class DescriptionPosition(ABC):
    bars:int = 0
    higher_loss:float = 0.0
    open_time: datetime = None
    close_time: datetime = None
    state: PositionState = PositionState.OPEN

@dataclass
class BasePosition(DescriptionPosition):
    id: int=0
    symbol: str=""
    margin: float=0.0
    entry: float=0.0
    side: Side = Side.LONG
    pnl: float = 0
    pnl_usdt: float = 0
    leverage: int = 10
    stop_price: float = None
    take_profit: float = None


    def __init__(self, order:Order, open_time:datetime, base_event:Union[PositionIsolateEvent, PositionCrossEvent]):
        self.base_event:Union[PositionIsolateEvent, PositionCrossEvent] = base_event
        self.id = order.id
        self.symbol = order.symbol
        self.entry = order.entry
        self.margin = order.usdt
        self.open_time = open_time
        self.side = order.side
        self.leverage = order.leverage
        self.stop_price = order.stop_price
        self.take_profit = order.take_profit

    @abstractmethod
    def compute_position(self, ohlcv: OHLCV): pass

@dataclass
class PositionIsolate(BasePosition):
    liquidy       :float = 0
    event_callback:PositionIsolateEvent = None

    compute: ComputePosition = None

    def __init__(self, order:Order, open_time:datetime, event:PositionIsolateEvent):
        super().__init__(order, open_time, event)
        self.event_callback:PositionIsolateEvent = event
        self.compute = ComputePosition(self)
        self._liquidated:Callable[[OHLCV], bool] = self._analyse_liquid_long\
            if self.side.value.__eq__(Side.LONG.value) else self._analyse_liquid_short
        # Calculate actual liquidation price based on leverage
        if order.leverage and order.leverage > 0:
            if self.side == Side.LONG:
                self.liquidy = self.entry * (1.0 - 1.0 / order.leverage)
            else:
                self.liquidy = self.entry * (1.0 + 1.0 / order.leverage)

    def compute_position(self, ohlcv: OHLCV):
        if ohlcv.time == self.open_time:
            return False
        self.bars += 1
        self.compute.update_pnl(ohlcv)
        if not self.compute.stopped(ohlcv) and not self._liquidated(ohlcv):
            self.compute.triggered(ohlcv)
        return None

    def _analyse_liquid_short(self, ohlcv:OHLCV)-> bool :
        if ohlcv.high >= self.liquidy:
            self.state = PositionState.LIQUID
            self.event_callback.position_liquidated(self)
            return True
        return False

    def _analyse_liquid_long(self, ohlcv:OHLCV)-> bool :
        if ohlcv.low <= self.liquidy:
            self.state = PositionState.LIQUID
            self.event_callback.position_liquidated(self)
            return True
        return False

@dataclass
class PositionCross(BasePosition):

    event_callback:PositionCrossEvent = None

    def __init__(self, order:Order, open_time:datetime, event:PositionCrossEvent):
        super().__init__(order, open_time, event)
        self.event_callback:PositionCrossEvent = event
        self.compute = ComputePosition(self)

    def compute_position(self, ohlcv: OHLCV):
        if ohlcv.time == self.open_time:
            return False
        self.bars += 1
        self.compute.update_pnl(ohlcv)
        self.event_callback.position_higher_loss_pnl(self.id, self.compute.pnl_higher(ohlcv))
        if not self.compute.stopped(ohlcv):
            self.compute.triggered(ohlcv)
        return None


@dataclass
class BaseUserParameter( OrderEvent):
    _balance: float
    _frees_balance: float
    _online_orders: dict[int, Order]
    _online_position: dict[int, Union[PositionIsolate, PositionCross]]
    _history_order: dict[int, Order]
    _history_position: dict[int, Union[PositionIsolate, PositionCross]]
    _user_id: str
    user_event: HostEventUser
    _leverage: dict[str, int]
    ohlcv: OHLCV | None
    _ids_deprecate_order: list[int]
    _ids_deprecate_position: list[int]
    def __init__(
            self,
            user_id: str,
            wallet: float = 0,
            user_event: HostEventUser = None,
    ):
        self._balance: float = wallet
        self._frees_balance: float = 0.0

        self._online_orders: dict[int, Order] = {}
        self._online_position: dict[int, Union[PositionIsolate, PositionCross]] = {}

        self._history_order: dict[int, Order] = {}
        self._history_position: dict[int, Union[PositionIsolate, PositionCross]] = {}

        self._user_id: str = user_id
        self.user_event: HostEventUser = user_event
        self._leverage: dict[str, int] = {}

        self.ohlcv: OHLCV | None = None

        self._ids_deprecate_order: list[int] = []
        self._ids_deprecate_position: list[int] = []

    def pipe_line_clone(self) -> 'BaseUserParameter':
        return self

    def upload_pipe_line(self, pipe: 'BaseUserParameter'):
        self._balance = pipe._balance
        self._frees_balance = pipe._frees_balance
        self._online_orders = {}
        self._online_position = {}
        self._history_order = pipe._history_order
        self._history_position = pipe._history_position
        self._user_id = pipe._user_id
        self.user_event = pipe.user_event
        self._leverage = pipe._leverage
        self.ohlcv: OHLCV | None
        self._ids_deprecate_order = pipe._ids_deprecate_order
        self._ids_deprecate_position = pipe._ids_deprecate_position


    def balance(self):
        self.user_event.new_balance(self._balance)
        return self._balance

    @property
    def online_orders(self):
        self.user_event.order_online(self._online_orders)
        return self._online_orders

    @property
    def online_positions(self):
        self.user_event.position_online(self._online_position)
        return self._online_position

    @property
    def history_orders(self):
        self.user_event.order_history(self._history_order)
        return self._history_order

    @property
    def history_positions(self):
        self.user_event.position_history(self._history_position)
        return self._history_position

    def valid_order_id(self, order_id: int) -> bool:
        return order_id in self._online_orders.keys()

    def valid_position_id(self, pos_id: int) -> bool:
        return pos_id in self._online_position.keys()

    def get_order(self, order_id: int) -> Union[None, 'Order']:
        return self._online_orders.get(order_id, None)

    def get_orders(self, symbol:str) -> list[Union[None, 'Order']]:
        o:list[Order] = []
        for order in self._online_orders.values():
            if order.symbol.__eq__(symbol):
                o.append(order)
        return o

    def get_position(self, pos_id: int) -> Union[PositionIsolate, PositionCross]:
        return self._online_position.get(pos_id, None)

    def leverage(self, symbol:str) -> int:
        if symbol in self._leverage:
            return self._leverage[symbol]
        self.set_leverage(symbol, 10)
        return 10

    def set_leverage(self,symbol:str, leverage:int)-> bool:
        self._leverage[symbol] = leverage
        return True

    def deposit(self,  balance:float ) -> tuple[bool, str] :
        self._balance += balance
        self.user_event.deposited(self._balance)
        return True, "deposited Usdt {}".format(balance)

    @abstractmethod
    def _add_position_market(self, order:Order)-> bool:
        pass

    def _return_margin_to_balance(self, margin:float, pnl:float=0) -> bool:
        self._balance += margin + pnl
        self._frees_balance -= margin
        return True

    def _get_margin_from_balance(self, usdt:float) -> bool:
        if self._balance < usdt:
            print("Not Enough Usdt In balance .")
            return False
        self._balance -= usdt
        self._frees_balance +=usdt
        return True

    def _has_enough_in_balance(self,usdt:float) -> bool:
        return self._balance >= usdt

    def add_order(self,order:Order) -> tuple[bool, str] :
        if not self._get_margin_from_balance(order.usdt):
            return False, "Not enough usdt available"

        order.leverage = self.leverage(order.symbol)  # safe: auto-defaults to 10 if unset

        if order.order_type.value.__eq__(OrderType.MARKET.value):
            order.entry = self.ohlcv.close
            # self.order_triggered(order, self.ohlcv)
            res:bool = self._add_position_market(order)
            self.user_event.order_placed(order)
            return (True, "Position is Opened By Market Order") if res else (False, "Position Is Not Open")

        self._online_orders[order.id] = order
        self.user_event.order_placed(order)

        return True , "order {} is placed".format(order.symbol)

    def cancel_order(self, order_id:int) -> tuple[bool, str]:
        if not self.valid_order_id(order_id):
            return False, "Invalid Order ID"
        order:Order = self._online_orders.pop(order_id)
        self._return_margin_to_balance(order.usdt)
        return True, "Order is canceled"

    def modify_order(self, order_id:int,side: Side = None,order_type: OrderType = None,
                     usdt: float = None,entry: float = None, stop_price: float = None,take_profit: float = None
                     ) -> tuple[bool, str] :

        if order_id not in self._online_orders:
            return False, "Order Is Not Modified. Order.id is not in Online Orders"

        order: Order = self._online_orders[order_id]

        # Determine the effective entry for validation (new value or current)
        eff_entry = entry if entry is not None else order.entry
        eff_side  = side  if side  is not None else order.side

        # Validate stop_price and take_profit BEFORE making any changes
        if stop_price is not None:
            if eff_side == Side.SHORT:
                if stop_price < eff_entry:
                    return False, "Stop Short Order Must Be Higher Than Entry"
            else:
                if stop_price > eff_entry:
                    return False, "Stop Long Order Must Be Lower Than Entry"

        if take_profit is not None:
            if eff_side == Side.SHORT:
                if take_profit > eff_entry:
                    return False, "Target Tp Short Order Must Be Lower Than Entry"
            else:
                if take_profit < eff_entry:
                    return False, "Target Tp Long Order Must Be Higher Than Entry"

        # Validate new usdt against available balance
        if usdt is not None and usdt != order.usdt:
            extra = usdt - order.usdt
            if extra > 0 and not self._has_enough_in_balance(extra):
                return False, "Order {} Is Not Modify Usdt Not Enough In Balance".format(order.symbol)

        # All validations passed — apply changes
        if side is not None:
            order.side = side
        if order_type is not None:
            order.order_type = order_type
        if usdt is not None and usdt != order.usdt:
            # Return old margin and lock new margin
            self._return_margin_to_balance(order.usdt)
            self._get_margin_from_balance(usdt)
            order.usdt = usdt
        if entry is not None:
            order.entry = entry
        if stop_price is not None:
            order.stop_price = stop_price
        if take_profit is not None:
            order.take_profit = take_profit

        return True, "Order Is Modified"

    def modify_position(self,
            pos_id: int, tp: float = None, stop: float = None) -> tuple[bool, str]:
        if not self.valid_position_id(pos_id):
            return False, "Invalid Position Id"

        pos: BasePosition = self._online_position[pos_id]
        close = self.ohlcv.close if self.ohlcv else pos.entry

        if pos.side == Side.LONG:
            if tp is not None:
                # TP must be above current price to still be reachable
                if tp <= close:
                    return False, "Tp Long Must Be Higher Than Current Price"
                pos.take_profit = tp
            if stop is not None:
                # SL must be below current price to not trigger immediately
                if stop >= close:
                    return False, "Stop Long Must Be Lower Than Current Price"
                pos.stop_price = stop

        elif pos.side == Side.SHORT:
            if tp is not None:
                # TP must be below current price to still be reachable
                if tp >= close:
                    return False, "Tp Short Must Be Lower Than Current Price"
                pos.take_profit = tp
            if stop is not None:
                # SL must be above current price to not trigger immediately
                if stop <= close:
                    return False, "Stop Short Must Be Higher Than Current Price"
                pos.stop_price = stop

        return True, "Position Modified"

    def _deprecate_event(self):
        for _id in self._ids_deprecate_order:
            self.history_orders[_id] = self._online_orders.pop(_id)
        self._ids_deprecate_order.clear()

        for _id in self._ids_deprecate_position:
            if _id in self._online_position.keys():
                self.history_positions[_id] = self._online_position.pop(_id)
        self._ids_deprecate_position.clear()

    @abstractmethod
    def kline(self, ohlcv:OHLCV):
        self.ohlcv = ohlcv
        # process Trigger Entry Orders
        for order in self._online_orders.values():
             order.kline(ohlcv)

        # Trigger Tp in Positions
        for _id, pos in self._online_position.items():
            if pos.state.value.__eq__(PositionState.OPEN.value):
                pos.compute_position(ohlcv)
                continue
            if not pos.id in self._ids_deprecate_position:
                self._ids_deprecate_position.append(pos.id)

        self._deprecate_event()


        # ===================Event Order =====================

    def order_cancelled(self, order: Order):
        self.user_event.order_cancelled(order)
        self._ids_deprecate_order.append(order.id)

    def close_position(self, pos_id:int) -> Union[None, PositionIsolate]:
        if self.valid_position_id(pos_id):
            pos: PositionIsolate = self._online_position[pos_id]
            pos.state = PositionState.STOPPED_BY_CLOSE if pos.pnl_usdt < 0 else PositionState.TRIGGERED_BY_CLOSE
            self._online_position[pos_id] = pos

            pos.compute.close_position(self.ohlcv)
            self._ids_deprecate_position.append(pos_id)

            self.user_event.position_closed(pos)
        return None



