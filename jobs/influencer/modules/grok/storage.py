"""
JOBS/INFLUENCER/GROK/STORAGE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: GROK STORAGE 💾
PURPOSE: Handles state persistence and frequency rules.
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR
from jobs.influencer.core.config import config_manager
from jobs.influencer.core.approval_queue import approval_queue

# State persistence
DATA_DIR = MEMORIES_DIR / "influencer"
BANTER_STATE_FILE = DATA_DIR / "grok_banter.json"


class GrokStorage:
    """Persistent state manager for Grok interactions."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # Load state, respecting existing file if present
        self.state = load_json(
            BANTER_STATE_FILE,
            default={
                "last_banter": None,
                "last_generated": None,
                "banter_count": 0,
                "conversation_history": [],
            },
        )

    def save(self):
        """Commit state to disk."""
        save_json(BANTER_STATE_FILE, self.state)

    def get_history(self, limit: int = 20) -> list:
        """Get recent conversation history."""
        return self.state.get("conversation_history", [])[-limit:]

    def add_event(
        self, event_type: str, role: str, text: str, tweet_id: str = None, **kwargs
    ):
        """Add an event to history and save."""
        event = {
            "role": role,
            "type": event_type,
            "text": text,
            "timestamp": datetime.now().isoformat(),
        }
        if tweet_id:
            event["tweet_id"] = tweet_id

        event.update(kwargs)

        self.state["conversation_history"].append(event)
        # Keep history manageable
        self.state["conversation_history"] = self.state["conversation_history"][-50:]
        self.save()

    def update_last_banter(self):
        """Mark banter as posted now."""
        self.state["last_banter"] = datetime.now().isoformat()
        self.state["banter_count"] += 1
        self.save()

    def update_last_generated(self):
        """Mark content as generated (throttle)."""
        self.state["last_generated"] = datetime.now().isoformat()
        self.save()

    def can_banter(self) -> bool:
        """
        Check if we are allowed to start a new banter thread.
        Rule: Every F2 days (defined in Timings).
        """
        now = datetime.now()

        # 0. Check Approval Queue (Don't generate if pending)
        if approval_queue.has_pending("grok_banter"):
            return False

        # 1. Check generation throttle (prevent restart spam)
        last_gen = self.state.get("last_generated")
        if last_gen:
            last_gen_dt = datetime.fromisoformat(last_gen)
            if now - last_gen_dt < timedelta(hours=23):  # Safety buffer
                return False

        # 2. Check posted interval
        last = self.state.get("last_banter")
        if not last:
            return True

        last_dt = datetime.fromisoformat(last)
        elapsed = now - last_dt

        config = config_manager.load()
        return elapsed >= timedelta(hours=config.grok_interval_hours)

    def get_root_tweet_id(self) -> str | None:
        """Find the tweet_id of the CURRENT thread's opening (most recent)."""
        # Iterate reverse to find LAST opening (current thread), not first (old thread)
        for item in reversed(self.state.get("conversation_history", [])):
            if item.get("type") == "opening" and item.get("tweet_id"):
                return item["tweet_id"]
        return None
