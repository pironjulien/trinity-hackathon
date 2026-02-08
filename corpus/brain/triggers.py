"""
CORPUS/BRAIN/TRIGGERS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: PROACTIVE MODE - TRIGGER FRAMEWORK 🎯
PURPOSE: Enable Trinity to initiate contact on important events.
USAGE: Run `evaluate_triggers()` periodically (e.g., in scheduler or Angel loop).
══════════════════════════════════════════════════════════════════════════════
"""

import json
from datetime import datetime, timezone
from typing import Callable, Optional
from dataclasses import dataclass, field
from loguru import logger

# REMOVED: These lines were causing global logger corruption
# logger.remove()
# logger.add(sys.stdout, level="INFO")

from corpus.dna.genome import MEMORIES_DIR


@dataclass
class Trigger:
    """A proactive trigger definition."""

    name: str
    condition: Callable[[], bool]  # Returns True if trigger should fire
    message: Callable[[], str]  # Returns the notification message
    source: str = "SYSTEM"  # Notification source
    cooldown_minutes: int = 60  # Minimum time between triggers
    priority: str = "INFO"  # INFO, WARNING, CRITICAL, ALERT
    enabled: bool = True

    # State
    last_fired: Optional[datetime] = field(default=None, repr=False)


class TriggerEngine:
    """
    Proactive Trigger Framework (SOTA 2026).

    Enables Trinity to monitor conditions and initiate contact
    when important events occur.
    """

    def __init__(self):
        self.triggers: list[Trigger] = []
        self._state_file = MEMORIES_DIR / "trinity" / "trigger_state.json"
        self._load_state()
        self._register_default_triggers()

    def _load_state(self) -> None:
        """Load trigger state from disk."""
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                self._last_fired: dict[str, str] = data.get("last_fired", {})
            else:
                self._last_fired = {}
        except Exception as e:
            logger.warning(f"🎯 Failed to load trigger state: {e}")
            self._last_fired = {}

    def _save_state(self) -> None:
        """Persist trigger state to disk."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps(
                    {
                        "last_fired": self._last_fired,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                )
            )
        except Exception as e:
            logger.warning(f"🎯 Failed to save trigger state: {e}")

    def register(self, trigger: Trigger) -> None:
        """Register a new trigger."""
        # Restore state
        if trigger.name in self._last_fired:
            try:
                trigger.last_fired = datetime.fromisoformat(
                    self._last_fired[trigger.name]
                )
            except Exception:
                pass

        self.triggers.append(trigger)
        logger.info(f"🎯 Registered trigger: {trigger.name}")

    def _register_default_triggers(self) -> None:
        """Register built-in triggers."""

        # === TRIGGER 1: Budget Critical ===
        def check_budget_critical() -> bool:
            try:
                budget_path = MEMORIES_DIR / "trinity" / "budget.json"
                if not budget_path.exists():
                    return False
                data = json.loads(budget_path.read_text())
                credits = data.get("credits_gcp", {})
                total = sum(c.get("valeur_restante", 0) for c in credits.values())
                burn_rate = 0.50  # $ par jour
                days_left = total / burn_rate if burn_rate > 0 else 999
                return days_left < 3
            except Exception:
                return False

        def budget_message() -> str:
            try:
                budget_path = MEMORIES_DIR / "trinity" / "budget.json"
                data = json.loads(budget_path.read_text())
                credits = data.get("credits_gcp", {})
                total = sum(c.get("valeur_restante", 0) for c in credits.values())
                return f"⚠️ Budget critique : ${total:.2f} restants. Action requise."
            except Exception:
                return "⚠️ Budget critique détecté."

        self.register(
            Trigger(
                name="budget_critical",
                condition=check_budget_critical,
                message=budget_message,
                source="SYSTEM",
                cooldown_minutes=240,  # 4 hours
                priority="CRITICAL",
            )
        )

        # === TRIGGER 2: Job Failure ===
        def check_job_failure() -> bool:
            try:
                log_path = MEMORIES_DIR / "logs" / "system.jsonl"
                if not log_path.exists():
                    return False

                # Check last 10 lines for errors
                lines = log_path.read_text().strip().split("\n")[-10:]
                for line in lines:
                    try:
                        entry = json.loads(line)
                        if entry.get("level", "").upper() == "ERROR":
                            ts = entry.get("timestamp", "")
                            if ts:
                                error_time = datetime.fromisoformat(
                                    ts.replace("Z", "+00:00")
                                )
                                age = (
                                    datetime.now(timezone.utc) - error_time
                                ).total_seconds()
                                if age < 300:  # Error in last 5 minutes
                                    return True
                    except Exception:
                        continue
                return False
            except Exception:
                return False

        def job_failure_message() -> str:
            try:
                log_path = MEMORIES_DIR / "logs" / "system.jsonl"
                lines = log_path.read_text().strip().split("\n")[-5:]
                for line in reversed(lines):
                    entry = json.loads(line)
                    if entry.get("level", "").upper() == "ERROR":
                        msg = entry.get("message", "Unknown error")[:100]
                        return f"🔴 Erreur système détectée: {msg}"
                return "🔴 Erreur système détectée."
            except Exception:
                return "🔴 Erreur système détectée."

        self.register(
            Trigger(
                name="job_failure",
                condition=check_job_failure,
                message=job_failure_message,
                source="SYSTEM",
                cooldown_minutes=30,
                priority="ALERT",
            )
        )

        # === TRIGGER 3: High Token Usage ===
        def check_high_token_usage() -> bool:
            try:
                tokens_path = MEMORIES_DIR / "logs" / "tokens.jsonl"
                if not tokens_path.exists():
                    return False

                today = datetime.now(timezone.utc).date()
                total = 0

                for line in tokens_path.read_text().strip().split("\n")[-100:]:
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        if ts:
                            entry_date = datetime.fromisoformat(
                                ts.replace("Z", "+00:00")
                            ).date()
                            if entry_date == today:
                                total += entry.get("in", 0) + entry.get("out", 0)
                    except Exception:
                        continue

                return total > 500_000  # 500K tokens/day threshold
            except Exception:
                return False

        def token_usage_message() -> str:
            return "📊 Consommation tokens élevée aujourd'hui (>500K). Considère l'optimisation."

        self.register(
            Trigger(
                name="high_token_usage",
                condition=check_high_token_usage,
                message=token_usage_message,
                source="SYSTEM",
                cooldown_minutes=480,  # 8 hours
                priority="WARNING",
            )
        )

    async def evaluate(self) -> list[str]:
        """
        Evaluate all triggers and send notifications for those that fire.
        Returns list of trigger names that fired.
        """
        # Guard: social is peripheral, Trinity must boot without it
        try:
            from social.messaging.notification_client import notify
        except ImportError:
            logger.debug(
                "🎯 [TRIGGERS] social.messaging unavailable - skipping evaluation"
            )
            return []

        fired: list[str] = []
        now = datetime.now(timezone.utc)

        for trigger in self.triggers:
            if not trigger.enabled:
                continue

            # Check cooldown
            if trigger.last_fired:
                elapsed = (now - trigger.last_fired).total_seconds() / 60
                if elapsed < trigger.cooldown_minutes:
                    continue

            # Evaluate condition
            try:
                if trigger.condition():
                    message = trigger.message()

                    # Send notification
                    success = await notify.send(
                        source=trigger.source,
                        message=message,
                        priority=trigger.priority,
                        dedup_key=f"TRIGGER_{trigger.name.upper()}",
                    )

                    if success:
                        trigger.last_fired = now
                        self._last_fired[trigger.name] = now.isoformat()
                        fired.append(trigger.name)
                        logger.info(f"🎯 Trigger fired: {trigger.name}")

            except Exception as e:
                logger.warning(f"🎯 Trigger {trigger.name} evaluation failed: {e}")

        if fired:
            self._save_state()

        return fired

    def get_status(self) -> list[dict]:
        """Get status of all triggers."""
        return [
            {
                "name": t.name,
                "enabled": t.enabled,
                "priority": t.priority,
                "cooldown_min": t.cooldown_minutes,
                "last_fired": t.last_fired.isoformat() if t.last_fired else None,
            }
            for t in self.triggers
        ]


# Singleton
trigger_engine = TriggerEngine()


# Convenience function for integration
async def evaluate_triggers() -> list[str]:
    """Evaluate all registered triggers. Call this periodically."""
    return await trigger_engine.evaluate()
