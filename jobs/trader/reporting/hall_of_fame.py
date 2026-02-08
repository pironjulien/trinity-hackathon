"""
JOBS/TRADER/REPORTING/HALL_OF_FAME.PY
==============================================================================
MODULE: HALL OF FAME 🏆
PURPOSE: Track and celebrate best trading achievements.
==============================================================================
"""

import json
from typing import List, Dict
from datetime import datetime
from loguru import logger

from jobs.trader.config import MEMORIES_DIR


LIMIT_ACHIEVEMENTS = 50
HALL_OF_FAME_FILE = MEMORIES_DIR / "trader" / "hall_of_fame.json"


class HallOfFame:
    """
    Hall of Fame for best trades.

    Features:
    - Track best trades by PnL
    - Keep treasures (big wins) forever
    - Prune old achievements
    - Persistence to disk
    """

    def __init__(self):
        self._achievements: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        """Load hall of fame from disk."""
        try:
            if HALL_OF_FAME_FILE.exists():
                with open(HALL_OF_FAME_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"[HALL] Load failed: {e}")
        return []

    def _save(self) -> None:
        """Save hall of fame to disk."""
        try:
            HALL_OF_FAME_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HALL_OF_FAME_FILE, "w", encoding="utf-8") as f:
                json.dump(self._achievements, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[HALL] Save failed: {e}")

    def add_achievement(self, achievement: Dict) -> None:
        """
        Add an achievement to hall of fame.

        Args:
            achievement: {id, description, pnl, pair, ...}
        """
        achievement["date"] = datetime.now().isoformat()
        self._achievements.append(achievement)
        self._prune()
        self._save()
        logger.success(
            f"🏆 [HALL] Achievement: {achievement.get('description', 'Unknown')}"
        )

    def add_best_trade(
        self, pair: str, pnl_eur: float, pnl_pct: float, context: Dict = None
    ) -> None:
        """Add a memorable trade."""
        self.add_achievement(
            {
                "id": f"TRADE_{pair}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                "type": "BEST_TRADE",
                "description": f"Profit {pnl_pct:.1f}% on {pair} (+{pnl_eur:.2f}€)",
                "pair": pair,
                "pnl_eur": pnl_eur,
                "pnl_pct": pnl_pct,
                "reward_dopamine": min(100, int(pnl_eur)),
                "context": context or {},
            }
        )

    def _prune(self) -> None:
        """Keep treasures (dopamine >= 50 or FIRST) and recent."""
        if len(self._achievements) <= LIMIT_ACHIEVEMENTS:
            return

        treasures = []
        others = []

        for a in self._achievements:
            is_treasure = (a.get("reward_dopamine", 0) >= 50) or (
                "FIRST" in str(a.get("id", ""))
            )
            if is_treasure:
                treasures.append(a)
            else:
                others.append(a)

        slots_left = max(0, LIMIT_ACHIEVEMENTS - len(treasures))
        kept_others = others[-slots_left:] if slots_left > 0 else []

        self._achievements = treasures + kept_others
        self._achievements.sort(key=lambda x: x.get("date", ""))

    def get_top(self, n: int = 10) -> List[Dict]:
        """Get top N achievements by PnL."""
        return sorted(
            self._achievements, key=lambda x: x.get("pnl_eur", 0), reverse=True
        )[:n]

    def get_recent(self, n: int = 5) -> List[Dict]:
        """Get N most recent achievements."""
        return sorted(
            self._achievements, key=lambda x: x.get("date", ""), reverse=True
        )[:n]

    def get_stats(self) -> Dict:
        """Get hall of fame stats."""
        if not self._achievements:
            return {"total": 0, "total_pnl": 0, "best_pnl": 0}

        pnls = [a.get("pnl_eur", 0) for a in self._achievements]
        return {
            "total": len(self._achievements),
            "total_pnl": sum(pnls),
            "best_pnl": max(pnls),
            "avg_pnl": sum(pnls) / len(pnls) if pnls else 0,
        }


def create_hall_of_fame() -> HallOfFame:
    """Factory function to create HallOfFame."""
    return HallOfFame()


def prune_hall_of_fame(
    achievements: List[Dict], limit: int = LIMIT_ACHIEVEMENTS
) -> List[Dict]:
    """Standalone function for pruning (compat TrinityOld)."""
    if len(achievements) <= limit:
        return achievements

    treasures = []
    others = []

    for a in achievements:
        is_treasure = (a.get("reward_dopamine", 0) >= 50) or (
            "FIRST" in str(a.get("id", ""))
        )
        if is_treasure:
            treasures.append(a)
        else:
            others.append(a)

    slots_left = max(0, limit - len(treasures))
    kept_others = others[-slots_left:] if slots_left > 0 else []

    return sorted(treasures + kept_others, key=lambda x: x.get("date", ""))
