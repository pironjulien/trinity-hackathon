"""
JOBS/TRADER/REPORTING/GAMIFICATION.PY
==============================================================================
MODULE: GAMIFICATION 🎮
PURPOSE: Convert financial performance into dopamine rewards.
         Integrates with the centralized Corpus Gamification System.
==============================================================================
"""

from typing import Dict

from corpus.dopamine import manager, Objective, RewardType

# Fibonacci-inspired milestones (EUR)
MILESTONES_PROFIT = [10, 21, 55, 89, 144, 233, 500, 1000, 2000, 5000, 10000]


class Gamification:
    """
    Gamified reward system (Trader Adapter).
    Registers trader-specific objectives with the core system.
    """

    def __init__(self):
        self._register_objectives()

    def _register_objectives(self):
        """Register all trader milestones as Objectives."""
        for milestone in MILESTONES_PROFIT:
            obj_id = f"trader_profit_{milestone}"

            # Calculate dynamic reward based on milestone difficulty
            dopamine = min(1.0, max(0.1, milestone / 1000))

            obj = Objective(
                id=obj_id,
                domain="TRADER",
                title=f"Profit Milestone: {milestone}€",
                description=f"Achieve a cumulative profit of {milestone}€.",
                target_value=milestone,
                unit="€",
                reward_amount=dopamine,
                reward_type=RewardType.DOPAMINE,
                icon="TrendingUp",
            )
            manager.register(obj)

        # Register Streak Objectives
        streaks = [
            (3, "Momentum", 0.3, "Flame"),
            (7, "Unstoppable", 0.8, "Zap"),
            (14, "Machine", 1.0, "Cpu"),
            (30, "Legend", 1.0, "Trophy"),
        ]
        for days, title, reward, icon in streaks:
            manager.register(
                Objective(
                    id=f"trader_streak_{days}",
                    domain="TRADER",
                    title=f"{title} ({days} Days)",
                    description=f"Profitable for {days} consecutive days.",
                    target_value=days,
                    unit="days",
                    reward_amount=reward,
                    icon=icon,
                )
            )

        # Register Volume Objectives
        volumes = [
            (10000, "Market Mover", 0.2),
            (50000, "Whale Watcher", 0.4),
            (100000, "Liquidity Provider", 0.6),
            (500000, "Market Maker", 0.8),
            (1000000, "Institutional", 1.0),
        ]
        for vol, title, reward in volumes:
            manager.register(
                Objective(
                    id=f"trader_volume_{vol}",
                    domain="TRADER",
                    title=f"Volume: {title}",
                    description=f"Trade a total volume of {vol}€.",
                    target_value=vol,
                    unit="€",
                    reward_amount=reward,
                    reward_type=RewardType.DOPAMINE,
                    icon="Activity",
                )
            )

    def check_milestones(self, total_profit: float) -> None:
        """
        Check and update profit milestones.

        Args:
            total_profit: Total profit in EUR
        """
        # Update all profit objectives
        for milestone in MILESTONES_PROFIT:
            obj_id = f"trader_profit_{milestone}"
            manager.update_objective(obj_id, total_profit)

    def check_streak(self, is_profitable_day: bool) -> None:
        """Update streak counter."""
        # Note: Streak logic in original file was stateful locally.
        # The new Objective system simply takes a 'value'.
        # We need to maintain the streak count somewhere to pass it to the objective.
        # For simplicity in this migration, we will rely on the caller or a simplified local tracking if needed.
        # However, to be stateless here, we might need to read the current streak from the objective itself if we want.
        # But 'check_streak' usually implies the job cycle runs it.

        # Let's assume the caller manages the 'days' count or we just pass the new value.
        # Since the original implementation tracked streak in a JSON, we might want to keep that logic
        # OR move streak tracking to the GamificationManager entirely?
        # For now, let's act as a pass-through update.
        # CAUTION: The original code loaded streak from disk.
        # We should probably let the Objective store the current value (which persists).
        # Streak logic handled by update_streak(streak_days) method below
        # Caller should maintain streak count and pass it explicitly

    def check_volume(self, total_volume: float) -> None:
        """Update volume objectives."""
        volumes = [10000, 50000, 100000, 500000, 1000000]
        for vol in volumes:
            manager.update_objective(f"trader_volume_{vol}", total_volume)

    def update_streak(self, streak_days: int):
        """Directly update streak objectives with a known count."""
        streaks = [3, 7, 14, 30]
        for days in streaks:
            manager.update_objective(f"trader_streak_{days}", float(streak_days))

    def process_trade(
        self, pair: str, side: str, price: float, amount: float, pnl: float = 0
    ) -> None:
        """
        Instant gratification for trades.
        This doesn't necessarily map to a specific "Objective" (quest),
        but is a direct hormone stimulus.
        """
        # Direct hormone injection is still allowed for micro-events
        from corpus.brain.hormones import hormones

        side = side.upper()
        if side == "SELL" and pnl > 0:
            reward = 0.05
            cost = price * amount
            if cost > 0:
                roi = (pnl / cost) * 100
                if roi > 1.0:
                    reward += 0.05
                if roi > 5.0:
                    reward += 0.1

            hormones.stimulate("dopamine", reward)

        elif side == "BUY":
            hormones.stimulate("dopamine", 0.02)

    def get_stats(self) -> Dict:
        """
        Get current gamification stats for reports.
        """
        stats = {"objectives": [], "total_dopamine": 0.0}

        # Try to fetch from manager if available
        try:
            # We filter objectives starting with 'trader_'
            trader_objs = [
                obj for obj in manager.list_objectives() if obj.domain == "TRADER"
            ]

            for obj in trader_objs:
                stats["objectives"].append(
                    {
                        "title": obj.title,
                        "progress": f"{obj.current_value}/{obj.target_value}",
                        "completed": obj.is_completed,
                        "icon": obj.icon,
                    }
                )

        except Exception:
            # Fallback if manager isn't accessible
            stats["error"] = "Could not fetch detailed stats"

        return stats


def create_gamification() -> Gamification:
    """Factory function."""
    return Gamification()


def check_achievements(performance: Dict) -> None:
    """
    Quick access wrapper.
    """
    total_profit = performance.get("total_profit", 0.0)
    total_volume = performance.get("total_volume", 0.0)
    current_streak = performance.get("current_streak", 0)

    g = create_gamification()
    g.check_milestones(total_profit)
    g.check_volume(total_volume)
    if current_streak > 0:
        g.update_streak(current_streak)
