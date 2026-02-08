"""
JOBS/TRADER/INTELLIGENCE/BACKTESTER.PY
==============================================================================
MODULE: GOLDEN BACKTESTER 📊
PURPOSE: Backtest strategies with Fibonacci-aligned metrics.
==============================================================================
"""

import asyncio
import polars as pl
from typing import List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from jobs.trader.config import (
    PHI,
    INV_PHI,
    MITRAILLETTE,
)
from jobs.trader.reporting.analytics import calculate_sharpe_ratio


@dataclass
class Trade:
    """A trade in the backtest."""

    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    direction: str  # "long" or "short"
    pnl_pct: float
    reason: str


@dataclass
class BacktestResult:
    """Complete backtest result."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    expectancy: float
    golden_aligned: bool  # Win rate close to 61.8%?
    trades: List[Trade] = field(default_factory=list)

    @property
    def is_profitable(self) -> bool:
        return self.total_pnl_pct > 0

    @property
    def is_valid(self) -> bool:
        return self.total_trades >= 20


class GoldenBacktester:
    """
    Backtester with Sacred Metrics (Fibonacci standards).

    Features:
    - Trailing stop at 61.8% of gains
    - Golden ratio alignment check
    - Sharpe ratio, profit factor, expectancy
    """

    def __init__(self):
        self._golden_target = INV_PHI  # 61.8%
        self._min_trades = 20

    async def run(
        self,
        df: pl.DataFrame,
        strategy_fn: Callable,
        initial_capital: float = 10000,
        stop_loss_pct: float = None,
        take_profit_pct: float = None,
    ) -> BacktestResult:
        """
        Run backtest on historical data.

        Args:
            df: OHLCV DataFrame
            strategy_fn: Async function that returns Signal for each candle
            initial_capital: Starting capital
            stop_loss_pct: Stop loss % (negative). Defaults to strategy config.
            take_profit_pct: Take profit % (positive). Defaults to PHI.

        Returns:
            BacktestResult with all metrics
        """
        sl = (
            stop_loss_pct
            if stop_loss_pct is not None
            else (MITRAILLETTE.stop_loss * 100)
        )
        tp = take_profit_pct if take_profit_pct is not None else (PHI * 100)

        if df.height < 100:
            logger.warning("⚠️ [BACKTEST] Insufficient data")
            return self._empty_result()

        trades: List[Trade] = []
        equity = initial_capital
        peak_equity = initial_capital
        max_drawdown = 0.0

        in_position = False
        entry_price = 0.0
        entry_time = None
        highest_price = 0.0

        closes = df["close"].to_list()
        timestamps = (
            df["timestamp"].to_list()
            if "timestamp" in df.columns
            else [None] * len(closes)
        )

        # Trailing stop: keep 61.8% of gains
        trailing_pct = INV_PHI

        for i in range(55, len(closes) - 1):
            # Prevent Event Loop Starvation (TradingHeart/Scanner must breathe)
            if i % 100 == 0:
                await asyncio.sleep(0)

            current_df = df.slice(0, i + 1)
            current_price = closes[i]
            current_time = (
                datetime.fromtimestamp(timestamps[i] / 1000)  # type: ignore[operator]
                if timestamps[i]
                else datetime.now()
            )

            if not in_position:
                # Check for entry signal
                signal = await strategy_fn(current_df)

                if signal and signal.action == "BUY":
                    in_position = True
                    entry_price = current_price
                    entry_time = current_time
                    highest_price = current_price
            else:
                # Update highest for trailing
                if current_price > highest_price:
                    highest_price = current_price

                pnl_pct = (current_price - entry_price) / entry_price * 100
                peak_pnl = (highest_price - entry_price) / entry_price * 100
                trailing_sl = peak_pnl * trailing_pct if peak_pnl > 0 else sl

                # Check exits
                exit_reason = None

                if pnl_pct <= sl:
                    exit_reason = "stop_loss"
                elif peak_pnl > tp * 0.5 and pnl_pct < trailing_sl:
                    exit_reason = "trailing_stop"
                elif pnl_pct >= tp:
                    exit_reason = "take_profit"

                if exit_reason:
                    trades.append(
                        Trade(
                            entry_price=entry_price,
                            exit_price=current_price,
                            entry_time=entry_time,
                            exit_time=current_time,
                            direction="long",
                            pnl_pct=pnl_pct,
                            reason=exit_reason,
                        )
                    )
                    equity *= 1 + pnl_pct / 100
                    in_position = False

                # Update drawdown
                if equity > peak_equity:
                    peak_equity = equity
                current_dd = (peak_equity - equity) / peak_equity * 100
                max_drawdown = max(max_drawdown, current_dd)

        return self._calculate_metrics(trades, initial_capital, equity, max_drawdown)

    def _calculate_metrics(
        self, trades: List[Trade], initial: float, final: float, max_dd: float
    ) -> BacktestResult:
        """Calculate final metrics."""
        if not trades:
            return self._empty_result()

        winning = [t for t in trades if t.pnl_pct > 0]
        losing = [t for t in trades if t.pnl_pct <= 0]

        win_rate = len(winning) / len(trades) * 100
        total_pnl = (final - initial) / initial * 100

        # Sharpe ratio
        returns = [t.pnl_pct for t in trades]
        sharpe = calculate_sharpe_ratio(returns)

        # Profit factor
        total_gains = sum(t.pnl_pct for t in winning) if winning else 0
        total_losses = abs(sum(t.pnl_pct for t in losing)) if losing else 1
        profit_factor = total_gains / total_losses if total_losses > 0 else total_gains

        # Expectancy
        expectancy = sum(t.pnl_pct for t in trades) / len(trades)

        # Golden alignment (within 5% of 61.8%)
        golden_aligned = abs(win_rate - self._golden_target * 100) < 5

        return BacktestResult(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            total_pnl_pct=total_pnl,
            max_drawdown_pct=max_dd,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            expectancy=expectancy,
            golden_aligned=golden_aligned,
            trades=trades,
        )

    def _empty_result(self) -> BacktestResult:
        """Return empty result."""
        return BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_pnl_pct=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            profit_factor=0,
            expectancy=0,
            golden_aligned=False,
            trades=[],
        )

    def get_summary(self, result: BacktestResult) -> str:
        """Generate backtest summary."""
        emoji = "🟢" if result.is_profitable else "🔴"
        golden = "✨" if result.golden_aligned else ""

        return f"""
{emoji} Backtest Summary {golden}
═══════════════════════════
Trades: {result.total_trades} ({result.win_rate:.1f}% win rate)
PnL: {result.total_pnl_pct:+.2f}%
Max Drawdown: {result.max_drawdown_pct:.2f}%
Sharpe: {result.sharpe_ratio:.2f}
Profit Factor: {result.profit_factor:.2f}
Golden Aligned: {"Yes ✨" if result.golden_aligned else "No"}
"""


def create_backtester() -> GoldenBacktester:
    """Factory function to create GoldenBacktester."""
    return GoldenBacktester()
