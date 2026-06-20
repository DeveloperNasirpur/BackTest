"""backtest — simulation engine with Trex indicator integration."""
from backtest.exchange.exchange import Exchange
from backtest.exchange.dataclass.classdata import StrategyBase
from backtest.exchange.dataclass.enums import Side, OrderType
from backtest.utils.loader import StrategyLoader

__version__ = "1.0.0"

__all__ = [
    "Exchange",
    "StrategyBase",
    "Side",
    "OrderType",
    "StrategyLoader",
]
