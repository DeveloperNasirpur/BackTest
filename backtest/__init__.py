"""
backtest — professional backtesting engine powered by trex_engine.

Quick start::

    from backtest import Backtest, Strategy, load_csv
    import trex

    class MyStrategy(Strategy):
        symbol    = "BTCUSDT"
        timeframe = "1m"
        deposit   = 10_000

        def indicators(self):
            trex.rsi(self.symbol, self.timeframe, period=14, listener=self.on_rsi)

        def on_rsi(self, value: float):
            self._rsi = value

        def on_kline(self, ohlcv):
            if not hasattr(self, '_rsi'):
                return
            if self._rsi < 30:
                self.buy(usdt=100)
            elif self._rsi > 70:
                self.sell(usdt=100)

    candles = load_csv("data/BTCUSDT_1m.csv", symbol="BTCUSDT")
    # or from PostgreSQL:
    # candles = load_postgres("BTCUSDT", "1m", host="localhost", database="okx")
    result  = Backtest(MyStrategy).run(candles)
    print(result)
"""
from backtest.strategy import Strategy
from backtest.runner import Backtest
from backtest.exchange.exchange import Exchange
from backtest.exchange.dataclass.classdata import StrategyBase
from backtest.exchange.dataclass.enums import Side, OrderType, PositionState
from backtest.utils.loader import StrategyLoader
from backtest.utils.candle_loader import load_csv, load_dicts, load_lists
from backtest.utils.postgres_loader import load_postgres
from backtest.utils.demo import demo_candles
from backtest.utils.binance_loader import load_binance
from backtest.stats import BacktestResult
from backtest.report import save_report

__version__ = "2.0.0"

__all__ = [
    # ── main API ──────────────────────────────────────────────────────────
    "Backtest",
    "Strategy",
    # ── data loading ──────────────────────────────────────────────────────
    "demo_candles",
    "load_csv",
    "load_dicts",
    "load_lists",
    "load_postgres",
    "load_binance",
    # ── results ───────────────────────────────────────────────────────────
    "BacktestResult",
    "save_report",
    # ── low-level (advanced use) ──────────────────────────────────────────
    "Exchange",
    "StrategyBase",
    "StrategyLoader",
    "Side",
    "OrderType",
    "PositionState",
]
