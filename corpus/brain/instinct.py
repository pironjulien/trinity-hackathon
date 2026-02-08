"""
CORPUS/BRAIN/INSTINCT.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INSTINCT (SURVIE) 🦎
PURPOSE: Réactions automatiques et protection du système.
      Migré et unifié depuis TrinityOld (reptilian + consolidation).
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from typing import Callable, Dict, Optional
from datetime import datetime
from loguru import logger


class InstinctiveReaction:
    """Une réaction instinctive à un stimulus."""

    def __init__(self, trigger: str, action: Callable, priority: int = 5):
        self.trigger = trigger
        self.action = action
        self.priority = priority  # 1-10, higher = more urgent
        self.last_triggered: Optional[datetime] = None


class SurvivalSystem:
    """
    Le Système de Survie de Trinity.
    Gère les réactions automatiques pour protéger le système.
    """

    def __init__(self):
        self.reactions: Dict[str, InstinctiveReaction] = {}
        self.threat_level: float = 0.0  # 0.0 = safe, 1.0 = critical
        self.defense_mode: bool = False

        # Registrer les réactions par défaut
        self._register_default_reactions()

    def _register_default_reactions(self):
        """Configure les réactions instinctives par défaut."""
        self.register_reaction(
            "memory_full", self._react_to_memory_pressure, priority=8
        )
        self.register_reaction(
            "resource_pressure", self._react_to_memory_pressure, priority=9
        )
        self.register_reaction("error_spike", self._react_to_errors, priority=9)
        self.register_reaction("low_energy", self._react_to_fatigue, priority=5)

    def register_reaction(self, trigger: str, action: Callable, priority: int = 5):
        """Enregistre une nouvelle réaction instinctive."""
        self.reactions[trigger] = InstinctiveReaction(trigger, action, priority)
        logger.debug(f"🦎 [INSTINCT] Registered: {trigger} (priority {priority})")

    async def sense_threat(self, threat_type: str, severity: float):
        """Détecte une menace et déclenche la réaction appropriée."""
        self.threat_level = max(self.threat_level, severity)

        logger.warning(
            f"🦎 [INSTINCT] Threat detected: {threat_type} (severity {severity:.0%})"
        )

        if threat_type in self.reactions:
            reaction = self.reactions[threat_type]
            reaction.last_triggered = datetime.now()

            if asyncio.iscoroutinefunction(reaction.action):
                await reaction.action(severity)
            else:
                reaction.action(severity)

        # Mode défense si menace critique
        if severity > 0.8:
            self.defense_mode = True
            logger.critical("🛡️ [INSTINCT] DEFENSE MODE ACTIVATED")

    async def _react_to_memory_pressure(self, severity: float):
        """Réaction à une pression mémoire."""
        logger.info(
            f"🧹 [INSTINCT] Memory cleanup triggered (severity: {severity:.0%})"
        )
        from corpus.soma.hygiene import hygiene

        hygiene.clean_cycle()

    async def _react_to_errors(self, severity: float):
        """Réaction à une accumulation d'Errors."""
        if severity > 0.7:
            logger.warning("⚠️ [INSTINCT] Error spike - reducing activity")
            # Réduire l'activité pour éviter la cascade d'Errors

    async def _react_to_fatigue(self, severity: float):
        """Réaction à la fatigue (basse énergie)."""
        logger.info("😴 [INSTINCT] Low energy - suggesting rest mode")

    def get_status(self) -> Dict:
        """Returns le status du système de survie."""
        return {
            "threat_level": self.threat_level,
            "defense_mode": self.defense_mode,
            "active_reactions": len(self.reactions),
            "last_alerts": [
                {
                    "trigger": r.trigger,
                    "last": r.last_triggered.isoformat() if r.last_triggered else None,
                }
                for r in self.reactions.values()
                if r.last_triggered
            ],
        }

    async def all_clear(self):
        """Signale que toutes les menaces sont passées."""
        self.threat_level = 0.0
        self.defense_mode = False
        logger.success("🦎 [INSTINCT] All clear - returning to normal operations")


# Singleton
instinct = SurvivalSystem()
