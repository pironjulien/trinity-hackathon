"""
JOBS/TRADER/INTELLIGENCE/MEMORY.PY
==============================================================================
MODULE: GOLDEN MEMORY 🧠
PURPOSE: Learn from winning trade patterns and boost confidence on similar setups.
==============================================================================
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
from loguru import logger

from jobs.trader.config import MEMORIES_DIR
from jobs.trader.utils import atomic_save_json


MEMORY_FILE = MEMORIES_DIR / "trader" / "golden_memory.json"
MAX_MEMORIES = 100


@dataclass
class TradeMemory:
    """A remembered winning trade."""

    pair: str
    pnl_pct: float
    pnl_eur: float
    entry_price: float
    exit_price: float
    indicators: Dict
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "pair": self.pair,
            "pnl_pct": self.pnl_pct,
            "pnl_eur": self.pnl_eur,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "indicators": self.indicators,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TradeMemory":
        return cls(
            pair=data["pair"],
            pnl_pct=data["pnl_pct"],
            pnl_eur=data["pnl_eur"],
            entry_price=data["entry_price"],
            exit_price=data["exit_price"],
            indicators=data.get("indicators", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if data.get("timestamp")
            else datetime.now(),
        )


class GoldenMemory:
    """
    Remembers winning trade patterns and recognizes similar setups.

    Features:
    - Store winning trades with context
    - Calculate similarity between current and past setups
    - Boost confidence on proven patterns
    """

    def __init__(self):
        self._memories: List[TradeMemory] = []
        self._load()

    def _load(self) -> None:
        """Load memories from disk."""
        try:
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._memories = [
                    TradeMemory.from_dict(m) for m in data.get("memories", [])
                ]
                logger.debug(f"🧠 [MEMORY] Loaded {len(self._memories)} memories")
        except Exception as e:
            logger.warning(f"🧠 [MEMORY] Load error: {e}")

    def _save(self) -> None:
        """Persist memories to disk (ATOMICALLY)."""
        try:
            atomic_save_json(
                MEMORY_FILE, {"memories": [m.to_dict() for m in self._memories]}
            )
        except Exception as e:
            logger.error(f"🧠 [MEMORY] Save error: {e}")

    def remember(
        self,
        pair: str,
        pnl_pct: float,
        pnl_eur: float,
        entry_price: float,
        exit_price: float,
        indicators: Dict,
    ) -> None:
        """
        Store a winning trade in memory.

        Only profitable trades are remembered.
        """
        if pnl_pct <= 0:
            return  # Only remember winners

        memory = TradeMemory(
            pair=pair,
            pnl_pct=pnl_pct,
            pnl_eur=pnl_eur,
            entry_price=entry_price,
            exit_price=exit_price,
            indicators=indicators,
        )

        self._memories.append(memory)

        # Prune to max size, keeping best trades
        if len(self._memories) > MAX_MEMORIES:
            self._memories.sort(key=lambda m: m.pnl_eur, reverse=True)
            self._memories = self._memories[:MAX_MEMORIES]

        self._save()
        logger.info(f"🧠 [MEMORY] Remembered {pair} (+{pnl_pct * 100:.1f}%)")

    def recall(
        self, pair: str, current_indicators: Dict
    ) -> tuple[float, Optional[str]]:
        """
        Check if current context matches any winning patterns.

        Args:
            pair: Trading pair
            current_indicators: Current indicator values

        Returns:
            (confidence_boost, reason) - boost amount and explanation
        """
        if not self._memories:
            return 0.0, None

        best_match = 0
        best_memory = None

        for memory in self._memories:
            # Calculate weighted similarity
            similarity = self._calculate_similarity(
                current_indicators, memory.indicators
            )

            # Bonus for same pair (Legacy: PHI boost implies affinity)
            if memory.pair == pair:
                similarity = min(1.0, similarity * 1.05)  # Slight nudge for same pair

            if similarity > best_match:
                best_match = similarity
                best_memory = memory

        # Require 75% similarity for a match (Legacy standard)
        if best_match >= 0.75 and best_memory:
            # Boost proportional to original profit and similarity
            # Formula: F5 (5) * similarity. Max +5 at 100% match.
            boost = 5.0 * best_match
            reason = f"Similar to {best_memory.pair} (+{best_memory.pnl_pct:.1f}%)"
            logger.info(
                f"🧠 [MEMORY] Pattern match! {best_match * 100:.0f}% similar → +{boost:.1f}"
            )
            return boost, reason

        return 0.0, None

    def check_autoexec(
        self, pair: str, current_indicators: Dict
    ) -> tuple[bool, float, Optional[str]]:
        """
        Check if current context qualifies for auto-execution.

        SOTA 2026: Auto-execute on 89%+ (F89) pattern match.
        Safety: Requires minimum F5 (5) memories before activation.

        Args:
            pair: Trading pair
            current_indicators: Current indicator values

        Returns:
            (should_autoexec, similarity, reason)
        """
        # Safety guard: require minimum F5 memories
        MIN_MEMORIES = 5  # F5
        AUTOEXEC_THRESHOLD = 0.89  # F89/100

        if len(self._memories) < MIN_MEMORIES:
            return (
                False,
                0.0,
                f"Insufficient memories ({len(self._memories)}/{MIN_MEMORIES})",
            )

        best_match = 0.0
        best_memory = None

        for memory in self._memories:
            similarity = self._calculate_similarity(
                current_indicators, memory.indicators
            )

            # Bonus for same pair
            if memory.pair == pair:
                similarity = min(1.0, similarity * 1.05)

            if similarity > best_match:
                best_match = similarity
                best_memory = memory

        if best_match >= AUTOEXEC_THRESHOLD and best_memory:
            reason = f"🧠 AUTOEXEC: {best_match * 100:.0f}% match to {best_memory.pair} (+{best_memory.pnl_pct * 100:.1f}%)"
            logger.success(reason)
            return True, best_match, reason

        return False, best_match, None

    def _calculate_similarity(self, current: Dict, past: Dict) -> float:
        """
        Calculate similarity between current and past indicator sets.
        Uses Weighted Similarity Algorithm (Vector Distance).

        Weights:
        - RSI: 0.382 (Primary momentum)
        - BTC Correlation: 0.236 (Market drag)
        - Hour: 0.146 (Time based patterns)
        - Boolean Structure: 0.236 (MACD/Uptrend/Fib)
        """
        if not current or not past:
            return 0.0

        score = 0.0
        weights = 0.0

        # 1. RSI Similarity (Weight 0.382)
        if "rsi" in current and "rsi" in past:
            rsi_diff = abs(current["rsi"] - past["rsi"])
            # 20 RSI point difference = 0 similarity
            rsi_score = max(0.0, 1.0 - (rsi_diff / 20.0))
            score += rsi_score * 0.382
            weights += 0.382

        # 2. BTC Correlation (Weight 0.236) - Context is key
        if "btc_24h" in current and "btc_24h" in past:
            btc_diff = abs(current["btc_24h"] - past["btc_24h"])
            # 5% difference in BTC 24h change = 0 similarity
            btc_score = max(0.0, 1.0 - (btc_diff / 5.0))
            score += btc_score * 0.236
            weights += 0.236

        # 3. Time Similarity (Weight 0.146)
        if "hour" in current and "hour" in past:
            # Circular time difference (0-24h)
            h_diff = min(
                abs(current["hour"] - past["hour"]),
                24 - abs(current["hour"] - past["hour"]),
            )
            # 6 hours difference = 0 similarity
            hour_score = max(0.0, 1.0 - (h_diff / 6.0))
            score += hour_score * 0.146
            weights += 0.146

        # 4. Boolean Structure (Weight 0.236)
        # Checks: macd_strong, is_uptrend, in_fib_zone
        bool_matches = 0
        bool_total = 0

        for key in ["macd_strong", "is_uptrend", "in_fib_zone"]:
            if key in current and key in past:
                bool_total += 1
                if current[key] == past[key]:
                    bool_matches += 1

        if bool_total > 0:
            bool_score = bool_matches / bool_total
            score += bool_score * 0.236
            weights += 0.236

        return score / weights if weights > 0 else 0.0

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        if not self._memories:
            return {"count": 0, "total_pnl": 0, "avg_pnl": 0}

        total_pnl = sum(m.pnl_eur for m in self._memories)
        return {
            "count": len(self._memories),
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(self._memories),
            "best_trade": max(m.pnl_eur for m in self._memories),
        }


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════
_memory_instance: GoldenMemory | None = None


def create_memory() -> GoldenMemory:
    """Factory function to get GoldenMemory singleton."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = GoldenMemory()
    return _memory_instance
