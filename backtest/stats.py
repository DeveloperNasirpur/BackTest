"""Backtest statistics and results reporting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backtest.exchange.exchange import Exchange

from backtest.exchange.dataclass.classdata import PositionIsolate, PositionCross


@dataclass
class BacktestResult:
    """Aggregate statistics computed after a backtest run."""

    # ── capital ───────────────────────────────────────────────────────────
    initial_balance: float = 0.0
    final_balance:   float = 0.0

    # ── overview ──────────────────────────────────────────────────────────
    total_trades:   int = 0
    winning_trades: int = 0
    losing_trades:  int = 0

    # ── P&L ──────────────────────────────────────────────────────────────
    total_pnl_usdt: float = 0.0
    gross_profit:   float = 0.0
    gross_loss:     float = 0.0
    largest_win:    float = 0.0
    largest_loss:   float = 0.0

    # ── risk ──────────────────────────────────────────────────────────────
    max_drawdown_usdt: float = 0.0
    max_drawdown_pct:  float = 0.0

    # ── raw positions ─────────────────────────────────────────────────────
    positions: list = field(default_factory=list)

    # ── derived ───────────────────────────────────────────────────────────

    @property
    def return_pct(self) -> float:
        if self.initial_balance == 0:
            return 0.0
        return (self.final_balance - self.initial_balance) / self.initial_balance * 100

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return self.gross_profit / abs(self.gross_loss)

    @property
    def avg_win(self) -> float:
        return self.gross_profit / self.winning_trades if self.winning_trades else 0.0

    @property
    def avg_loss(self) -> float:
        return self.gross_loss / self.losing_trades if self.losing_trades else 0.0

    @property
    def risk_reward(self) -> float:
        if self.avg_loss == 0:
            return 0.0
        return abs(self.avg_win / self.avg_loss)

    # ── factory ───────────────────────────────────────────────────────────

    @classmethod
    def from_exchange(cls, exchange: "Exchange") -> "BacktestResult":
        result = cls()

        for user_id, user in exchange._users.items():
            initial = exchange._initial_deposits.get(user_id, 0.0)
            result.initial_balance += initial
            result.final_balance   += user._balance + user._frees_balance

            all_pos: list[Union[PositionIsolate, PositionCross]] = list(
                user._history_position.values()
            )
            result.positions.extend(all_pos)

            equity = initial
            peak   = equity

            for pos in all_pos:
                pnl = pos.pnl_usdt or 0.0
                result.total_pnl_usdt += pnl
                result.total_trades   += 1

                if pnl >= 0:
                    result.winning_trades += 1
                    result.gross_profit   += pnl
                    result.largest_win     = max(result.largest_win, pnl)
                else:
                    result.losing_trades += 1
                    result.gross_loss    += pnl
                    result.largest_loss   = min(result.largest_loss, pnl)

                equity += pnl
                peak    = max(peak, equity)
                dd      = peak - equity
                result.max_drawdown_usdt = max(result.max_drawdown_usdt, dd)
                if peak > 0:
                    result.max_drawdown_pct = max(
                        result.max_drawdown_pct, dd / peak * 100
                    )

        return result

    # ── display ───────────────────────────────────────────────────────────

    def summary(self) -> str:
        sep = "─" * 48
        lines = [
            sep,
            "  BACKTEST RESULTS",
            sep,
            f"  Initial balance  : ${self.initial_balance:>12,.2f}",
            f"  Final balance    : ${self.final_balance:>12,.2f}",
            f"  Return           : {self.return_pct:>+.2f}%",
            sep,
            f"  Total trades     : {self.total_trades}",
            f"  Wins / Losses    : {self.winning_trades} / {self.losing_trades}",
            f"  Win rate         : {self.win_rate:.1%}",
            f"  Profit factor    : {self.profit_factor:.2f}",
            f"  Risk / Reward    : {self.risk_reward:.2f}",
            sep,
            f"  Total P&L        : ${self.total_pnl_usdt:>+12,.2f}",
            f"  Gross profit     : ${self.gross_profit:>12,.2f}",
            f"  Gross loss       : ${self.gross_loss:>12,.2f}",
            f"  Largest win      : ${self.largest_win:>12,.2f}",
            f"  Largest loss     : ${self.largest_loss:>12,.2f}",
            f"  Avg win          : ${self.avg_win:>12,.2f}",
            f"  Avg loss         : ${self.avg_loss:>12,.2f}",
            sep,
            f"  Max drawdown     : ${self.max_drawdown_usdt:>12,.2f}  ({self.max_drawdown_pct:.1f}%)",
            sep,
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def __repr__(self) -> str:
        return (
            f"BacktestResult(trades={self.total_trades}, "
            f"win_rate={self.win_rate:.1%}, "
            f"return={self.return_pct:+.2f}%, "
            f"pf={self.profit_factor:.2f})"
        )
