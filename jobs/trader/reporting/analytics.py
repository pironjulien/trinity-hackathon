"""
JOBS/TRADER/REPORTING/ANALYTICS.PY
==============================================================================
MODULE: ANALYTICS 📊
PURPOSE: Performance calculations and statistics.
==============================================================================
"""

from typing import Dict, List, Tuple


def calculate_position_pnl(
    entry_price: float, current_price: float, quantity: float, fee_rate: float = 0.0026
) -> Tuple[float, float]:
    """
    Calculate position PnL with fees.

    Args:
        entry_price: Entry price
        current_price: Current/exit price
        quantity: Position quantity
        fee_rate: Fee rate (default: 0.26%)

    Returns:
        (pnl_pct, pnl_eur)
    """
    if entry_price <= 0:
        return 0.0, 0.0

    entry_cost = entry_price * quantity
    exit_value = current_price * quantity

    # Fees for entry and exit
    total_fees = (entry_cost + exit_value) * fee_rate

    pnl_eur = exit_value - entry_cost - total_fees
    pnl_pct = pnl_eur / entry_cost if entry_cost > 0 else 0.0

    return pnl_pct, pnl_eur


def calculate_win_rate(trades: List[Dict]) -> float:
    """
    Calculate win rate from trades list.

    Args:
        trades: List of trade dicts with 'pnl' key

    Returns:
        Win rate as percentage (0-100)
    """
    if not trades:
        return 0.0

    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    return (wins / len(trades)) * 100


def calculate_drawdown(equity_curve: List[float]) -> Tuple[float, float]:
    """
    Calculate max drawdown from equity curve.

    Args:
        equity_curve: List of equity values

    Returns:
        (current_drawdown, max_drawdown) as percentages
    """
    if not equity_curve or len(equity_curve) < 2:
        return 0.0, 0.0

    peak = equity_curve[0]
    max_dd = 0.0
    current_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value

        if peak > 0:
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
            current_dd = dd

    return current_dd, max_dd


def get_portfolio_summary(positions: Dict, prices: Dict) -> Dict:
    """
    Generate real-time portfolio summary.

    Args:
        positions: Dict {pair: position_data}
        prices: Dict {pair: current_price}

    Returns:
        Summary with position count, total value, unrealized PnL
    """
    total_value = 0.0
    total_pnl = 0.0
    details = []

    for pair, pos in positions.items():
        curr_price = prices.get(pair, pos.get("entry_price", 0))
        quantity = pos.get("quantity", 0)
        entry_price = pos.get("entry_price", 0)

        value = curr_price * quantity
        total_value += value

        pnl_pct, pnl_eur = calculate_position_pnl(entry_price, curr_price, quantity)
        total_pnl += pnl_eur

        details.append(
            {
                "pair": pair,
                "value": round(value, 2),
                "pnl_pct": round(pnl_pct * 100, 2),
                "pnl_eur": round(pnl_eur, 2),
            }
        )

    return {
        "positions_count": len(positions),
        "total_value": round(total_value, 2),
        "unrealized_pnl": round(total_pnl, 2),
        "details": details,
    }


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from returns.

    Args:
        returns: List of period returns
        risk_free_rate: Risk-free rate (default: 0)

    Returns:
        Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    import statistics

    avg_return = statistics.mean(returns)
    std_dev = statistics.stdev(returns)

    if std_dev == 0:
        return 0.0

    return (avg_return - risk_free_rate) / std_dev


def calculate_profit_factor(trades: List[Dict]) -> float:
    """
    Calculate profit factor (gross profits / gross losses).

    Args:
        trades: List of trade dicts with 'pnl' key

    Returns:
        Profit factor (>1 is profitable)
    """
    if not trades:
        return 0.0

    gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))

    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def get_performance_summary(
    trades: List[Dict], equity_curve: List[float] = None
) -> Dict:
    """
    Generate comprehensive performance summary.

    Args:
        trades: List of completed trades
        equity_curve: Optional equity history

    Returns:
        Performance metrics dict
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
        }

    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) < 0]

    total_pnl = sum(t.get("pnl", 0) for t in trades)
    avg_win = sum(t.get("pnl", 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get("pnl", 0) for t in losses) / len(losses) if losses else 0

    _, max_dd = calculate_drawdown(equity_curve or [100, 100 + total_pnl])

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": calculate_win_rate(trades),
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": calculate_profit_factor(trades),
        "max_drawdown": max_dd * 100,
        "best_trade": max((t.get("pnl", 0) for t in trades), default=0),
        "worst_trade": min((t.get("pnl", 0) for t in trades), default=0),
    }


def get_performance_stats(performance: Dict) -> Dict:
    """
    Extract key stats including streaks for brain analysis.

    Args:
        performance: Dict with 'good_trades', 'bad_trades', etc.

    Returns:
        Dict with total_pnl, win_rate, streaks, etc.
    """
    # Build all trades list
    all_trades = []
    for t in performance.get("good_trades", []):
        all_trades.append({**t, "type": "win"})
    for t in performance.get("bad_trades", []):
        all_trades.append({**t, "type": "loss"})

    # Sort by date (most recent first)
    all_trades.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Calculate streaks
    current_streak = 0
    recent_loss_streak = 0

    if all_trades:
        first_type = all_trades[0]["type"]

        # Current streak (+ for wins, - for losses)
        count = 0
        for t in all_trades:
            if t["type"] == first_type:
                count += 1
            else:
                break
        current_streak = count if first_type == "win" else -count

        # Recent loss streak
        for t in all_trades:
            if t["type"] == "loss":
                recent_loss_streak += 1
            else:
                break

    # Win rate
    total_trades = len(all_trades)
    wins = sum(1 for t in all_trades if t["type"] == "win")
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

    return {
        "total_pnl_eur": performance.get("total_pnl_eur", 0.0),
        "total_trades": total_trades,
        "wins": wins,
        "losses": total_trades - wins,
        "win_rate": round(win_rate, 1),
        "current_streak": current_streak,
        "recent_loss_streak": recent_loss_streak,
        "best_trade": performance.get("best_trade", 0.0),
        "worst_trade": performance.get("worst_trade", 0.0),
    }


def get_daily_stats(trades_today: List[Dict]) -> Dict:
    """
    Calculate daily trading statistics.

    Args:
        trades_today: List of today's trades

    Returns:
        Dict with trades count, pnl, win_rate
    """
    if not trades_today:
        return {"trades": 0, "pnl": 0.0, "win_rate": 0.0}

    pnl = sum(t.get("pnl", 0) for t in trades_today)
    wins = sum(1 for t in trades_today if t.get("pnl", 0) > 0)

    return {
        "trades": len(trades_today),
        "pnl": round(pnl, 2),
        "win_rate": round((wins / len(trades_today)) * 100, 1),
    }
