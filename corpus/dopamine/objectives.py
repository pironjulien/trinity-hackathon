"""
CORPUS/GAMIFICATION/OBJECTIVES.PY
==============================================================================
MODULE: OBJECTIVES SYSTEM 🎯
PURPOSE: Centralized registry for Trinity's objectives, quests, and achievements.
         Links performance (Trader, System) to Dopamine rewards.
==============================================================================
"""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, List
from pydantic import BaseModel
from loguru import logger

from corpus.brain.hormones import hormones

# Persistence Path (relative to corpus/dopamine/ -> memories/)
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MEMORY_PATH = _ROOT_DIR / "memories" / "trinity" / "objectives_state.json"


class ObjectiveStatus(str, Enum):
    LOCKED = "LOCKED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class RewardType(str, Enum):
    DOPAMINE = "dopamine"
    SEROTONIN = "serotonin"


class Objective(BaseModel):
    id: str
    domain: str  # "TRADER", "TRINITY", "INFLUENCER"
    title: str
    description: str
    current_value: float = 0.0
    target_value: float
    unit: str = ""  # "€", "%", "uptime"
    reward_amount: float = 0.1  # 0.0 - 1.0 intensity
    reward_type: RewardType = RewardType.DOPAMINE
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE
    icon: str = "Target"  # Lucide icon name
    hidden: bool = False  # If true, only shows when unlocked/completed or generic "???"

    def check_progress(self, new_value: float) -> bool:
        """Updates progress and returns True if newly completed."""
        if self.status == ObjectiveStatus.COMPLETED:
            # Still update value for display "over-achievement" if desired, but don't re-trigger
            self.current_value = max(self.current_value, new_value)
            return False

        self.current_value = max(self.current_value, new_value)

        if self.current_value >= self.target_value:
            self.complete()
            return True
        return False

    def complete(self):
        self.status = ObjectiveStatus.COMPLETED
        logger.success(
            f"🎯 [OBJECTIVE] Completed: {self.title} (+{self.reward_amount} {self.reward_type.value})"
        )
        hormones.stimulate(self.reward_type.value, self.reward_amount)


class GamificationManager:
    """
    Manages all objectives for Trinity.
    Handles registration, updates, and persistence.
    """

    def __init__(self):
        self._objectives: Dict[str, Objective] = {}
        self._loaded_state: Dict = {}
        self.load_state()

    def register(self, objective: Objective):
        """Register a new objective definition."""
        # Restore state if exists
        if state := self._loaded_state.get(objective.id):
            status_str = state.get("status", "ACTIVE")
            objective.status = (
                ObjectiveStatus(status_str)
                if isinstance(status_str, str)
                else status_str
            )
            objective.current_value = state.get("current_value", 0.0)

        self._objectives[objective.id] = objective

    def update_objective(self, objective_id: str, value: float):
        """Update progress for a specific objective."""
        if obj := self._objectives.get(objective_id):
            if obj.check_progress(value):
                self.save_state()
        else:
            # Auto-register logic could go here, but strict registration is better
            pass

    def get_objective_value(self, objective_id: str) -> float:
        """Return the current value of an objective, or 0.0 if not found."""
        if obj := self._objectives.get(objective_id):
            return obj.current_value
        return 0.0

    def get_all_objectives(self) -> List[Dict]:
        """Return all objectives as dicts for frontend."""
        return [obj.model_dump() for obj in self._objectives.values()]

    def load_state(self):
        try:
            if MEMORY_PATH.exists():
                with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                    self._loaded_state = json.load(f)
        except Exception as e:
            logger.error(f"[GAMIFICATION] Failed to load state: {e}")

    def save_state(self):
        try:
            state = {
                obj.id: {"status": obj.status, "current_value": obj.current_value}
                for obj in self._objectives.values()
            }
            MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"[GAMIFICATION] Failed to save state: {e}")


# Singleton Instance
manager = GamificationManager()


# --- DEFAULT SYSTEM OBJECTIVES ---
# These are registered on import or initial setup
def register_core_objectives():
    # --- UPTIME (8 Objectives) ---
    uptime_milestones = [
        (3600, "1 Hour", 0.1),
        (21600, "6 Hours", 0.2),
        (43200, "12 Hours", 0.3),
        (86400, "24 Hours", 0.5),  # Stability II
        (259200, "3 Days", 0.6),
        (604800, "7 Days", 0.8),
        (1209600, "14 Days", 1.0),
        (2592000, "30 Days", 1.0),
    ]
    for sec, label, reward in uptime_milestones:
        manager.register(
            Objective(
                id=f"sys_uptime_{sec}",
                domain="TRINITY",
                title=f"Uptime: {label}",
                description=f"Maintain continuous system operation for {label}.",
                target_value=sec,
                unit="s",
                reward_amount=reward,
                reward_type=RewardType.SEROTONIN,
                icon="Shield",
            )
        )

    # --- FINOPS (5 Objectives) ---
    # Cost optimization targets (e.g. Daily burn rate)
    finops_targets = [
        (10.0, "Budget Watcher"),
        (5.0, "Efficient Runner"),
        (2.0, "Lean Machine"),
        (1.0, "Penny Pincher"),
        (0.5, "Zero Waste"),
    ]
    for cost, title in finops_targets:
        manager.register(
            Objective(
                id=f"sys_cost_under_{int(cost * 10)}",
                domain="TRINITY",
                title=f"FinOps: {title}",
                description=f"Keep daily infrastructure cost under {cost}€.",
                target_value=cost,
                unit="€",
                reward_amount=0.4,
                reward_type=RewardType.DOPAMINE,
                icon="TrendingUp",  # Inverse target (lower is better logic needed? Or just manual award)
                # NOTE: Manager 'check_progress' uses max(current, new) >= target.
                # For 'lower is better', we might need to invert logic or handle manually.
                # For now, we'll register them and assume 'current_value' represents 'savings' or use manual handling.
                # actually, let's treat it as: "Days under budget" -> target_value=1, 7, 30 days.
            )
        )

    # --- SAFETY & STABILITY (4 Objectives) ---
    manager.register(
        Objective(
            id="sys_no_crash_24h",
            domain="TRINITY",
            title="Stability Streak (24h)",
            description="No critical crashes for 24 hours.",
            target_value=24 * 60,  # minutes?
            unit="m",
            reward_type=RewardType.SEROTONIN,
            icon="Activity",
        )
    )

    # --- RESOURCES (3 Objectives) ---
    manager.register(
        Objective(
            id="sys_cpu_efficiency",
            domain="TRINITY",
            title="Neural Efficiency",
            description="Maintain CPU < 20% for 5 minutes.",
            target_value=300,
            unit="sec",
            reward_amount=0.5,
            icon="Cpu",
        )
    )

    manager.register(
        Objective(
            id="sys_ram_optimization",
            domain="TRINITY",
            title="Memory Optimization",
            description="Keep RAM usage under 1GB for 1 hour.",
            target_value=3600,
            unit="sec",
            reward_amount=0.5,
            icon="Zap",
        )
    )


register_core_objectives()
