"""
JULES/CORTEX.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: JULES CORTEX (Semantic Memory) 🧠
PURPOSE: Prevents amnesia. Tracks task history, failures, and architectural state.
         Ensures Jules never makes the same mistake twice.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import time
from typing import Dict, Optional, Literal
from loguru import logger
from corpus.dna import genome

# Persistence
CORTEX_FILE = genome.ROOT_DIR / "memories" / "jules" / "cortex.json"


class Cortex:
    """
    The Semantic Memory of Jules.
    Tracks signatures of tasks to prevent duplicates and loops.
    """

    def __init__(self):
        self._memory: Dict = {
            "signatures": {},  # Task history
            "blueprints": {},  # Architectural plans state
            "stats": {"wins": 0, "losses": 0, "streak": 0},
        }
        self._load()

    def _load(self):
        """Load memory from disk."""
        try:
            if CORTEX_FILE.exists():
                self._memory = json.loads(CORTEX_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"🧠 [CORTEX] Memory load failure: {e}")
            # Keep default empty memory to survive

    def _save(self):
        """Persist memory to disk."""
        try:
            CORTEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            CORTEX_FILE.write_text(json.dumps(self._memory, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"🧠 [CORTEX] Memory save failure: {e}")

    def check_task(self, signature: str) -> bool:
        """
        Consults memory to see if a talk should be attempted.
        Returns:
            True (ALLOW) - Task is safe to proceed.
            False (BLOCK) - Task was recently rejected or failed too often.
        """
        sig_data = self._memory["signatures"].get(signature)

        if not sig_data:
            return True  # New task, go ahead

        status = sig_data.get("status")
        last_attempt = sig_data.get("last_attempt", 0)
        attempts = sig_data.get("attempts", 0)

        # 1. HARD BLOCK for permanently rejected tasks (unless manually cleared)
        if status == "PERMANENT_REJECT":
            logger.warning(f"🧠 [CORTEX] Blocked {signature}: Permanent Reject.")
            return False

        # 1b. HARD BLOCK for user-rejected tasks (never repropose)
        if status == "REJECTED_BY_USER":
            logger.warning(f"🧠 [CORTEX] Blocked {signature}: User Rejection.")
            return False

        # 2. COOL DOWN for failed tasks
        # Exponential backoff: 1h, 4h, 12h, 24h
        if status in ["FAILED", "REJECTED"]:
            delay = 3600 * (2 ** (attempts - 1))
            if time.time() - last_attempt < delay:
                remaining = int((delay - (time.time() - last_attempt)) / 60)
                logger.info(
                    f"🧠 [CORTEX] Cooling down {signature} ({remaining}m remaining)."
                )
                return False

        # 3. MAX ATTEMPTS check
        if attempts >= 5 and status != "SUCCESS":
            logger.warning(
                f"🧠 [CORTEX] Blocked {signature}: Too many failures ({attempts})."
            )
            return False

        return True

    def record_attempt(self, signature: str):
        """Log that we are starting a task."""
        if signature not in self._memory["signatures"]:
            self._memory["signatures"][signature] = {
                "status": "PENDING",
                "attempts": 0,
                "history": [],
            }

        self._memory["signatures"][signature]["attempts"] += 1
        self._memory["signatures"][signature]["last_attempt"] = time.time()
        self._save()

    def record_outcome(
        self,
        signature: str,
        outcome: Literal[
            "SUCCESS", "FAILED", "REJECTED", "PERMANENT_REJECT", "REJECTED_BY_USER"
        ],
        reason: str = "",
    ):
        """Log the result of a task."""
        if signature not in self._memory["signatures"]:
            self.record_attempt(signature)  # Should not happen usually

        self._memory["signatures"][signature]["status"] = outcome
        self._memory["signatures"][signature]["last_reason"] = reason

        history_entry = {"time": time.time(), "outcome": outcome, "reason": reason}
        self._memory["signatures"][signature].setdefault("history", []).append(
            history_entry
        )

        # Update global stats
        if outcome == "SUCCESS":
            self._memory["stats"]["wins"] += 1
            self._memory["stats"]["streak"] += 1
        elif outcome in ["FAILED", "REJECTED", "REJECTED_BY_USER"]:
            self._memory["stats"]["losses"] += 1
            self._memory["stats"]["streak"] = 0

        self._save()
        logger.info(f"🧠 [CORTEX] Recorded {outcome} for {signature}: {reason}")

    def get_stats(self):
        return self._memory["stats"]

    def get_last_failure_reason(self, signature: str) -> Optional[str]:
        """Retrieve the reason for the last failure of this task."""
        sig_data = self._memory["signatures"].get(signature)
        if sig_data and sig_data.get("status") in ["FAILED", "REJECTED"]:
            return sig_data.get("last_reason")
        return None

    def can_retry(self, signature: str) -> bool:
        """
        Check if a failed task is eligible for retry (cooldown passed).
        Returns True if the task can be retried now.
        """
        sig_data = self._memory["signatures"].get(signature)
        if not sig_data:
            return False  # No history = not a retry situation

        status = sig_data.get("status")
        if status == "SUCCESS":
            return False  # Already succeeded
        if status in ["PERMANENT_REJECT", "REJECTED_BY_USER"]:
            return False  # Never retry these

        # Check cooldown
        last_attempt = sig_data.get("last_attempt", 0)
        attempts = sig_data.get("attempts", 0)
        delay = 3600 * (2 ** (attempts - 1))  # Exponential backoff

        return time.time() - last_attempt >= delay

    def build_retry_context(self, signature: str, original_prompt: str) -> str:
        """
        IMPROVEMENT 2: Build an enriched prompt for retry attempts.
        Includes the reason for previous failure to help Jules avoid the same mistake.

        Args:
            signature: Task signature
            original_prompt: The original task instruction

        Returns:
            Enriched prompt with failure context
        """
        sig_data = self._memory["signatures"].get(signature)
        if not sig_data:
            return original_prompt  # First attempt, no enrichment needed

        last_reason = sig_data.get("last_reason", "Unknown")
        attempts = sig_data.get("attempts", 0)
        history = sig_data.get("history", [])

        # Build failure summary from history
        failure_summary = []
        for entry in history[-3:]:  # Last 3 attempts max
            if entry.get("outcome") in ["FAILED", "REJECTED"]:
                failure_summary.append(f"- {entry.get('reason', 'No reason')}")

        enriched_prompt = f"""
{original_prompt}

[RETRY CONTEXT - Attempt #{attempts + 1}]
Previous attempts have FAILED. Learn from these mistakes:
{chr(10).join(failure_summary) if failure_summary else "- Check Quality Gate feedback"}

LAST FAILURE REASON: {last_reason}

CRITICAL: Address these specific issues in your new attempt.
Do not repeat the same mistakes.
"""
        logger.info(
            f"🧠 [CORTEX] Built retry context for {signature} (attempt #{attempts + 1})"
        )
        return enriched_prompt.strip()


# Singleton
cortex = Cortex()
