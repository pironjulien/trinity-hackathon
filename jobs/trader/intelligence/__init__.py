"""
JOBS/TRADER/INTELLIGENCE/__INIT__.PY
==============================================================================
INTELLIGENCE MODULE - Advanced Trading Features
==============================================================================
"""

from jobs.trader.intelligence.memory import GoldenMemory, create_memory
from jobs.trader.intelligence.backtester import GoldenBacktester, create_backtester
from jobs.trader.intelligence.optimizer import OptimizerService, create_optimizer
from jobs.trader.intelligence.whales import WhaleTracker, create_whale_tracker
from jobs.trader.intelligence.portfolio import (
    PortfolioManager,
    create_portfolio_manager,
)

__all__ = [
    # Memory
    "GoldenMemory",
    "create_memory",
    # Backtester
    "GoldenBacktester",
    "create_backtester",
    # Optimizer
    "OptimizerService",
    "create_optimizer",
    # Whales
    "WhaleTracker",
    "create_whale_tracker",
    # Portfolio
    "PortfolioManager",
    "create_portfolio_manager",
]
