"""
JOBS/TRADER/REPORTING/__INIT__.PY
==============================================================================
REPORTING MODULE - Output Layer
==============================================================================
"""

from jobs.trader.reporting.templates import (
    format_report,
    format_position_line,
    format_trade_notification,
    format_alert,
)
from jobs.trader.reporting.analytics import (
    calculate_position_pnl,
    calculate_win_rate,
    calculate_drawdown,
    get_performance_summary,
)
from jobs.trader.reporting.gamification import Gamification, create_gamification
from jobs.trader.reporting.hall_of_fame import HallOfFame, create_hall_of_fame
from jobs.trader.reporting.night_cycle import NightCycle, create_night_cycle

__all__ = [
    # Templates
    "format_report",
    "format_position_line",
    "format_trade_notification",
    "format_alert",
    # Analytics
    "calculate_position_pnl",
    "calculate_win_rate",
    "calculate_drawdown",
    "get_performance_summary",
    # Gamification
    "Gamification",
    "create_gamification",
    # Hall of Fame
    "HallOfFame",
    "create_hall_of_fame",
    # Night Cycle
    "NightCycle",
    "create_night_cycle",
]
