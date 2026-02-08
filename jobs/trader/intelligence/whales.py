"""
JOBS/TRADER/INTELLIGENCE/WHALES.PY
==============================================================================
MODULE: WHALE TRACKER 🐋
PURPOSE: Detect large orders indicating institutional movements.
==============================================================================
"""

import polars as pl
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from jobs.trader.config import PHI


@dataclass
class WhaleActivity:
    """A detected whale activity."""

    type: str  # "accumulation", "distribution", "large_order"
    volume_ratio: float  # vs average
    price_impact: float  # % impact
    timestamp: datetime
    direction: str  # "buy" or "sell"


class WhaleTracker:
    """
    Whale Movement Detector.

    Identifies large orders indicating institutional movements.
    Uses PHI (2.618x) as threshold for whale activity.
    """

    def __init__(self):
        self._threshold = PHI + 1  # 2.618x average = whale
        self._recent_activity: List[WhaleActivity] = []

    def detect(self, df: pl.DataFrame) -> List[WhaleActivity]:
        """
        Analyze volume to detect whale activity.

        Args:
            df: DataFrame with 'volume', 'close', 'open' columns

        Returns:
            List of detected whale activities
        """
        if df.height < 20 or "volume" not in df.columns:
            return []

        activities = []

        volumes = df["volume"].to_list()
        closes = df["close"].to_list()
        opens = df["open"].to_list()

        # Calculate average volume (excluding last 3 candles)
        avg_volume = sum(volumes[:-3]) / len(volumes[:-3])

        # Analyze last 3 candles for whales
        for i in range(-3, 0):
            current_volume = volumes[i]
            ratio = current_volume / avg_volume if avg_volume > 0 else 0

            if ratio >= self._threshold:
                price_change = (
                    (closes[i] - opens[i]) / opens[i] * 100 if opens[i] != 0 else 0
                )
                direction = "buy" if price_change > 0 else "sell"

                activity = WhaleActivity(
                    type="large_order",
                    volume_ratio=ratio,
                    price_impact=abs(price_change),
                    timestamp=datetime.now(),
                    direction=direction,
                )

                activities.append(activity)
                logger.info(f"🐋 [WHALES] {direction.upper()}: {ratio:.1f}x avg volume")

        # Update history (keep last 20)
        self._recent_activity.extend(activities)
        self._recent_activity = self._recent_activity[-20:]

        return activities

    def detect_accumulation(self, df: pl.DataFrame, window: int = 10) -> Optional[str]:
        """
        Detect accumulation/distribution phase.

        Returns:
            "accumulating", "distributing", or None
        """
        if df.height < window:
            return None

        volumes = df["volume"].to_list()[-window:]
        closes = df["close"].to_list()[-window:]

        # Rising volume with stable price = accumulation
        volume_rising = sum(
            1 for i in range(1, len(volumes)) if volumes[i] > volumes[i - 1]
        )
        price_range = (
            (max(closes) - min(closes)) / min(closes) * 100 if min(closes) > 0 else 0
        )

        if volume_rising >= window * 0.7 and price_range < 2.0:
            return "accumulating"
        elif volume_rising >= window * 0.7 and self._prices_declining(closes):
            return "distributing"

        return None

    def _prices_declining(self, prices: List[float]) -> bool:
        """Check if prices are declining."""
        lower_count = sum(1 for i in range(1, len(prices)) if prices[i] < prices[i - 1])
        return lower_count >= len(prices) * 0.6

    def get_sentiment(self) -> str:
        """Get overall sentiment based on recent whale activity."""
        if not self._recent_activity:
            return "neutral"

        recent = self._recent_activity[-5:]
        buys = sum(1 for w in recent if w.direction == "buy")
        sells = sum(1 for w in recent if w.direction == "sell")

        if buys > sells * PHI:
            return "whale_bullish"
        elif sells > buys * PHI:
            return "whale_bearish"

        return "neutral"

    def get_recent(self, n: int = 5) -> List[WhaleActivity]:
        """Get N most recent whale activities."""
        return self._recent_activity[-n:]


def create_whale_tracker() -> WhaleTracker:
    """Factory function to create WhaleTracker."""
    return WhaleTracker()
