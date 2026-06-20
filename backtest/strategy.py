"""
backtest.strategy — clean Strategy base class.

The user only needs to implement:
  - indicators()   → register trex indicators
  - on_kline()     → trading logic per bar

Everything else (exchange wiring, trex init, balance, shortcuts) is handled
automatically by the Backtest runner.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union

from backtest.exchange.dataclass.classdata import (
    HostEventUser, Order, PositionIsolate, PositionCross,
)
from trex.base.ohlcv import OHLCV

if TYPE_CHECKING:
    from backtest.exchange.exchange import Exchange


class Strategy(HostEventUser, ABC):
    """
    Base class for all backtest strategies.

    Class-level attributes (override per strategy):

        symbol    = "BTCUSDT"
        timeframe = "1m"
        deposit   = 1_000.0      # starting USDT
        leverage  = 10
        fee       = 0.0004       # 0.04 % taker fee
        slippage  = 0.0001       # 0.01 % market-order slippage
        broadcast = True         # stream bars to TrexTerminal
        port      = 8765         # TrexTerminal WebSocket port

    Example::

        class MyStrategy(Strategy):
            symbol    = "BTCUSDT"
            timeframe = "1m"
            deposit   = 5_000

            def indicators(self):
                trex.rsi(self.symbol, self.timeframe, period=14, listener=self.on_rsi)

            def on_rsi(self, value: float):
                self._rsi = value

            def on_kline(self, ohlcv):
                if getattr(self, '_rsi', None) is None:
                    return
                if self._rsi < 30:
                    self.buy(usdt=100)
                elif self._rsi > 70:
                    self.sell(usdt=100)
    """

    # ── class-level config (override in subclass) ─────────────────────────
    symbol: str    = "BTCUSDT"
    timeframe: str = "1m"
    deposit: float = 1_000.0
    leverage: int  = 10
    fee: float     = 0.0004
    slippage: float = 0.0001
    broadcast: bool = True
    port: int      = 8765

    # ── internal, wired by Backtest ───────────────────────────────────────
    _exchange: Exchange | None = None
    _user_id: str | None = None

    def __init__(self):
        pass

    # ── abstract: user must implement these two ───────────────────────────

    @abstractmethod
    def indicators(self) -> None:
        """
        Register trex indicators here.
        Called once before the candle loop starts (trex is already initialised).

        Example::

            def indicators(self):
                trex.rsi(self.symbol, self.timeframe, period=14, listener=self.on_rsi)
                trex.ema(self.symbol, self.timeframe, period=20, listener=self.on_ema)
        """

    @abstractmethod
    def on_kline(self, ohlcv: OHLCV) -> None:
        """
        Called once per bar after indicators have been updated.
        Place your trading logic here using self.buy() / self.sell() / self.close().
        """

    # ── trading shortcuts ─────────────────────────────────────────────────

    def buy(
        self,
        usdt: float,
        price: float = None,
        sl: float = None,
        tp: float = None,
    ) -> tuple[int, str]:
        """Open a Long position (market or limit)."""
        self._assert_ready()
        return self._exchange.open_long(
            symbol=self.symbol,
            user_id=self._user_id,
            usdt=usdt,
            entry=price,
            stop_price=sl,
            take_profit=tp,
        )

    def sell(
        self,
        usdt: float,
        price: float = None,
        sl: float = None,
        tp: float = None,
    ) -> tuple[int, str]:
        """Open a Short position (market or limit)."""
        self._assert_ready()
        return self._exchange.open_short(
            symbol=self.symbol,
            user_id=self._user_id,
            usdt=usdt,
            entry=price,
            stop_price=sl,
            take_profit=tp,
        )

    def close(self, position_id: int = None) -> None:
        """
        Close a position by ID, or close ALL open positions if no ID given.
        """
        self._assert_ready()
        if position_id is not None:
            self._exchange.close_position(self._user_id, position_id)
        else:
            for pos in list(self.positions):
                self._exchange.close_position(self._user_id, pos.id)

    def set_sl_tp(
        self,
        position_id: int,
        sl: float = None,
        tp: float = None,
    ) -> tuple[bool, str]:
        """Modify stop-loss and/or take-profit on an open position."""
        self._assert_ready()
        return self._exchange.set_target(self._user_id, position_id, sl, tp)

    def cancel(self, order_id: int) -> tuple[bool, str]:
        """Cancel a pending limit order by ID."""
        self._assert_ready()
        return self._exchange.cancel_order(self._user_id, order_id)

    def set_leverage(self, leverage: int) -> None:
        """Change leverage for this strategy's symbol."""
        self._assert_ready()
        self._exchange.change_leverage(self.symbol, self._user_id, leverage)
        self.leverage = leverage

    # ── read-only properties ──────────────────────────────────────────────

    @property
    def balance(self) -> float:
        """Current available USDT balance."""
        self._assert_ready()
        return self._exchange.get_balance(self._user_id)

    @property
    def positions(self) -> list[Union[PositionIsolate, PositionCross]]:
        """All currently open positions for this strategy's symbol."""
        self._assert_ready()
        return self._exchange.get_positions(symbol=self.symbol, user_id=self._user_id)

    @property
    def orders(self) -> list[Order]:
        """All pending limit orders for this strategy's symbol."""
        self._assert_ready()
        return self._exchange.get_orders(self._user_id, self.symbol)

    @property
    def history(self) -> list[Union[PositionIsolate, PositionCross]]:
        """All closed/triggered/stopped positions (full trade history)."""
        self._assert_ready()
        return self._exchange.get_history_positions(
            symbol=self.symbol, user_id=self._user_id
        )

    # ── optional event hooks (override any you need) ──────────────────────

    def on_position_opened(self, pos: Union[PositionIsolate, PositionCross]) -> None:
        """Called when any position is opened (market order filled or limit triggered)."""

    def on_position_closed(self, pos: Union[PositionIsolate, PositionCross]) -> None:
        """Called when a position is manually closed."""

    def on_position_profit(self, pos: Union[PositionIsolate, PositionCross]) -> None:
        """Called when a take-profit is hit."""

    def on_position_loss(self, pos: Union[PositionIsolate, PositionCross]) -> None:
        """Called when a stop-loss is hit."""

    def on_position_liquidated(self, pos: Union[PositionIsolate, PositionCross]) -> None:
        """Called when a position is liquidated."""

    def on_order_placed(self, order: Order) -> None:
        """Called when a limit order is placed."""

    def on_order_cancelled(self, order: Order) -> None:
        """Called when an order is cancelled."""

    # ── HostEventUser interface (wired to user hooks above) ───────────────

    def position_opened(self, pos):
        self.on_position_opened(pos)

    def position_closed(self, pos):
        self.on_position_closed(pos)

    def position_triggered(self, pos):
        self.on_position_profit(pos)

    def position_stopped(self, pos):
        self.on_position_loss(pos)

    def position_liquidated(self, pos):
        self.on_position_liquidated(pos)

    def order_placed(self, order: Order):
        self.on_order_placed(order)

    def order_cancelled(self, order: Order):
        self.on_order_cancelled(order)

    # ── silent no-ops for the rest of the interface ───────────────────────

    def on_position_long(self, symbol: str, _id: int): pass
    def on_position_short(self, symbol: str, _id: int): pass
    def waiting_entry_long(self, symbol: str, _id: int): pass
    def waiting_entry_short(self, symbol: str, _id: int): pass
    def order_triggered(self, order: Order, ohlcv: OHLCV): pass
    def liquid_balance(self): pass
    def deposited(self, balance: float): pass
    def new_balance(self, balance: float): pass
    def order_history(self, orders: dict): pass
    def position_history(self, pos: dict): pass
    def order_online(self, orders: dict): pass
    def position_online(self, pos: dict): pass

    # ── internal ──────────────────────────────────────────────────────────

    def _assert_ready(self):
        if self._exchange is None or self._user_id is None:
            raise RuntimeError(
                "Strategy is not wired to an exchange. "
                "Use Backtest(MyStrategy).run(candles) instead of running manually."
            )
