"""backtest — simulation engine with Trex indicator integration."""
from backtest.exchange.exchange import Exchange
from backtest.exchange.dataclass.classdata import StrategyBase
from backtest.exchange.dataclass.enums import Side, OrderType, PositionState
from backtest.utils.loader import StrategyLoader
from backtest.utils.candle_loader import load_csv, load_dicts, load_lists
from backtest.stats import BacktestResult

__version__ = "2.0.0"

__all__ = [
    "Exchange",
    "StrategyBase",
    "Side",
    "OrderType",
    "PositionState",
    "StrategyLoader",
    "BacktestResult",
    "load_csv",
    "load_dicts",
    "load_lists",
]
