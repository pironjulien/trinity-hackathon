"""
JOBS/TRADER/INTELLIGENCE/PORTFOLIO.PY
==============================================================================
MODULE: PORTFOLIO MANAGER 📊
PURPOSE: Math-driven portfolio rebalancing and correlation analysis.
         Avid redundant positions and optimize allocation.
RESPECTS: ONE STATION POLICY - NO AI HERE (Latency Sensitive).
==============================================================================
"""

import polars as pl
from typing import Dict, List, Tuple
from dataclasses import dataclass
from loguru import logger

from jobs.trader.config import INV_PHI
from jobs.trader.data.history import create_history


@dataclass
class CorrelationWarning:
    """Correlation warning between positions."""

    pair1: str
    pair2: str
    correlation: float  # 0-1
    warning: str
    action: str  # "reduce", "avoid", "ok"


class PortfolioManager:
    """
    Portfolio Manager (Math-Based).

    Features:
    - Pearson Correlation matrix (avoids redundant positions)
    - Risk concentration detection
    - Non-blocking (fail-open)
    """

    def __init__(self):
        self._correlation_cache: Dict[str, float] = {}
        self.history = create_history()
        # Simple sector mapping helper
        self.L1_COINS = {"BTC", "ETH", "SOL", "AVAX", "ADA", "DOT", "NEAR", "ALGO"}
        self.DEFI_COINS = {"UNI", "AAVE", "MKR", "SNX", "CRV"}

    async def check_correlation(
        self, new_pair: str, existing_positions: List[str]
    ) -> Tuple[bool, List[CorrelationWarning]]:
        """
        Check if new position is correlated with existing portfolio using Pearson Correlation.

        Args:
            new_pair: Pair to buy (e.g., "SOL/EUR")
            existing_positions: List of pairs already held

        Returns:
            (is_safe, warnings)
        """
        if not existing_positions:
            return True, []

        new_asset = new_pair.split("/")[0]
        warnings = []

        try:
            # 1. Fast heuristic check (Sector Saturation)
            is_l1 = new_asset in self.L1_COINS
            l1_count = sum(
                1 for p in existing_positions if p.split("/")[0] in self.L1_COINS
            )

            if is_l1 and l1_count >= 3:
                warnings.append(
                    CorrelationWarning(
                        pair1=new_pair,
                        pair2="SECTOR_L1",
                        correlation=0.9,
                        warning="Sector Saturation: Layer 1",
                        action="avoid",
                    )
                )

            # 2. Mathematical Correlation Check (Pearson)
            # Fetch candles for new pair
            df_new = await self.history.get_candles(new_pair, limit=1000)

            if df_new.is_empty() or len(df_new) < 100:
                logger.debug(
                    f"📊 [PORTFOLIO] Insufficient history for {new_pair} - Skipping correlation"
                )
                return True, warnings  # Fail open

            # Prepare df_new for joining: select timestamp and close, rename close
            df_new = df_new.select(
                [pl.col("timestamp"), pl.col("close").alias("close_new")]
            )

            for existing_pair in existing_positions:
                # Fetch candles for existing pair
                df_existing = await self.history.get_candles(existing_pair, limit=1000)

                if df_existing.is_empty() or len(df_existing) < 100:
                    continue

                # Prepare df_existing
                df_existing = df_existing.select(
                    [pl.col("timestamp"), pl.col("close").alias("close_ex")]
                )

                # Join on timestamp
                joined = df_new.join(df_existing, on="timestamp", how="inner")

                if len(joined) < 50:
                    continue

                # Calculate Pearson Correlation
                correlation = joined.select(pl.corr("close_new", "close_ex")).item()

                # Check thresholds
                if correlation > 0.85:
                    action = "avoid" if correlation > 0.95 else "reduce"
                    warnings.append(
                        CorrelationWarning(
                            pair1=new_pair,
                            pair2=existing_pair,
                            correlation=correlation,
                            warning=f"High correlation with {existing_pair} ({correlation:.2f})",
                            action=action,
                        )
                    )

            # Decision
            # If any "avoid" warning exists, is_safe = False
            is_safe = not any(w.action == "avoid" for w in warnings)

            if warnings:
                logger.info(
                    f"📊 [PORTFOLIO] {new_asset}: {len(warnings)} correlation warnings found"
                )
                for w in warnings:
                    logger.debug(f"   - {w.warning} -> {w.action}")

            return is_safe, warnings

        except Exception as e:
            logger.error(f"📊 [PORTFOLIO] Correlation check failed: {e}")
            return True, []  # Fail open (allow trade) to avoid blocking

    def calculate_max_position_size(
        self, pair: str, existing_positions: List[str], base_size: float
    ) -> float:
        """
        Calculate max position size based on sector exposure.
        """
        asset = pair.split("/")[0]

        # Check for same-sector positions
        sector_count = 0
        current_sector_assets = self.L1_COINS if asset in self.L1_COINS else set()

        for pos in existing_positions:
            pos_asset = pos.split("/")[0]
            if pos_asset in current_sector_assets:
                sector_count += 1

        if sector_count >= 2:
            return base_size * INV_PHI  # Reduce size

        return base_size


def create_portfolio_manager() -> PortfolioManager:
    """Factory function."""
    return PortfolioManager()
