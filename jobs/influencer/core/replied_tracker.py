"""
JOBS/INFLUENCER/REPLIED_TRACKER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CENTRALIZED INTERACTION TRACKER 🔒
PURPOSE: Unified tracking of ALL tweet interactions (replied, skipped, etc.)
         Single source of truth for mentions.py and grok_banter.py.
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime
from typing import Set, Optional, Literal
from loguru import logger

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

from jobs.influencer.core.rules import Limits
from jobs.influencer.core.config import config_manager

# Shared state file
DATA_DIR = MEMORIES_DIR / "influencer"
REPLIED_STATE_FILE = DATA_DIR / "replied_tweets.json"

# Maximum interactions to retain (rolling window)
MAX_INTERACTION_HISTORY = Limits.MAX_REPLIED_HISTORY

# Interaction statuses
InteractionStatus = Literal["replied", "skipped"]


class RepliedTracker:
    """
    Centralized tracker for ALL tweet interactions.

    UNIFIED SYSTEM (V2 Refactor):
    - Tracks both "replied" and "skipped" tweets in one place
    - Replaces the old dual system (processed_ids + replied_tracker)
    - Single source of truth for all modules

    Used by:
    - mentions/worker.py
    - grok/core.py
    """

    # Maximum replies allowed per conversation thread
    # MAX_REPLIES_PER_THREAD used to be here, now dynamic in config

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = load_json(
            REPLIED_STATE_FILE,
            default={
                "interactions": {},  # {tweet_id: {status, reason?, at}}
                "thread_reply_counts": {},  # {conversation_id: count}
                # Legacy support - will be migrated
                "replied_tweet_ids": [],
            },
        )
        self._migrate_legacy()

    def _migrate_legacy(self):
        """Migrate old replied_tweet_ids[] to new interactions{} format."""
        legacy_ids = self.state.get("replied_tweet_ids", [])
        if legacy_ids and not self.state.get("interactions"):
            logger.info(f"🔒 [TRACKER] Migrating {len(legacy_ids)} legacy entries...")
            self.state["interactions"] = {}
            for tid in legacy_ids:
                self.state["interactions"][str(tid)] = {
                    "status": "replied",
                    "at": "2026-01-01T00:00:00",  # Unknown original time
                }
            self.state["replied_tweet_ids"] = []  # Clear legacy
            self._save_state()
            logger.success("🔒 [TRACKER] Migration complete")

    def _save_state(self):
        save_json(REPLIED_STATE_FILE, self.state)

    # ════════════════════════════════════════════════════════════════════════
    # UNIFIED TRACKING (NEW)
    # ════════════════════════════════════════════════════════════════════════

    def is_processed(self, tweet_id: str | int) -> bool:
        """
        Check if we have already processed this tweet (replied OR skipped).

        This is the MAIN entry point for checking if a tweet should be handled.
        Replaces the old processed_ids check in mentions.json.
        """
        tweet_id_str = str(tweet_id)
        return tweet_id_str in self.state.get("interactions", {})

    def mark_skipped(self, tweet_id: str | int, reason: str = "unknown") -> None:
        """
        Mark a tweet as seen but not replied to (spam, daily limit, etc.)

        Args:
            tweet_id: The tweet ID
            reason: Why it was skipped (spam, daily_limit, error, etc.)
        """
        tweet_id_str = str(tweet_id)

        if self.is_processed(tweet_id_str):
            return

        if "interactions" not in self.state:
            self.state["interactions"] = {}

        self.state["interactions"][tweet_id_str] = {
            "status": "skipped",
            "reason": reason,
            "at": datetime.now().isoformat(),
        }

        self._trim_interactions()
        self._save_state()
        logger.debug(f"🔒 [TRACKER] Skipped {tweet_id_str} (reason: {reason})")

    def get_interaction(self, tweet_id: str | int) -> Optional[dict]:
        """Get interaction details for a tweet."""
        tweet_id_str = str(tweet_id)
        return self.state.get("interactions", {}).get(tweet_id_str)

    def _trim_interactions(self):
        """Keep interactions dict under max size (FIFO)."""
        interactions = self.state.get("interactions", {})
        if len(interactions) > MAX_INTERACTION_HISTORY:
            # Sort by timestamp and keep newest
            sorted_items = sorted(
                interactions.items(), key=lambda x: x[1].get("at", ""), reverse=True
            )
            self.state["interactions"] = dict(sorted_items[:MAX_INTERACTION_HISTORY])

    # ════════════════════════════════════════════════════════════════════════
    # REPLIED TRACKING (Original API preserved)
    # ════════════════════════════════════════════════════════════════════════

    def has_replied(self, tweet_id: str | int) -> bool:
        """
        Check if we have already REPLIED to this tweet.

        Note: Use is_processed() to check if tweet was seen at all (replied OR skipped).
        """
        tweet_id_str = str(tweet_id)
        interaction = self.state.get("interactions", {}).get(tweet_id_str)
        return interaction is not None and interaction.get("status") == "replied"

    def mark_replied(self, tweet_id: str | int) -> None:
        """Mark a tweet as replied to."""
        tweet_id_str = str(tweet_id)

        if self.has_replied(tweet_id_str):
            logger.debug(f"🔒 [TRACKER] Tweet {tweet_id_str} already marked as replied")
            return

        if "interactions" not in self.state:
            self.state["interactions"] = {}

        self.state["interactions"][tweet_id_str] = {
            "status": "replied",
            "at": datetime.now().isoformat(),
        }

        self._trim_interactions()
        self._save_state()
        logger.debug(f"🔒 [TRACKER] Marked {tweet_id_str} as replied")

    def get_all_replied(self) -> Set[str]:
        """Get all tweet IDs that have been replied to."""
        return set(
            tid
            for tid, data in self.state.get("interactions", {}).items()
            if data.get("status") == "replied"
        )

    # ════════════════════════════════════════════════════════════════════════
    # THREAD LIMITING (Unchanged)
    # ════════════════════════════════════════════════════════════════════════

    def get_thread_count(self, root_tweet_id: str | int) -> int:
        """Get the number of replies we've sent in a thread."""
        root_id_str = str(root_tweet_id)
        return self.state.get("thread_reply_counts", {}).get(root_id_str, 0)

    def can_reply_to_thread(self, root_tweet_id: str | int) -> bool:
        """Check if we can still reply to this thread (under MAX_REPLIES_PER_THREAD)."""
        count = self.get_thread_count(root_tweet_id)
        config = config_manager.load()
        limit = config.max_replies_per_thread
        can_reply = count < limit

        if not can_reply:
            logger.warning(
                f"🔒 [TRACKER] Thread {root_tweet_id} at limit ({count}/{limit})"
            )

        return can_reply

    def increment_thread_count(self, root_tweet_id: str | int) -> int:
        """Increment the reply count for a thread."""
        root_id_str = str(root_tweet_id)

        if "thread_reply_counts" not in self.state:
            self.state["thread_reply_counts"] = {}

        current = self.state["thread_reply_counts"].get(root_id_str, 0)
        self.state["thread_reply_counts"][root_id_str] = current + 1
        self._save_state()

        config = config_manager.load()
        logger.debug(
            f"🔒 [TRACKER] Thread {root_id_str} count: {current + 1}/{config.max_replies_per_thread}"
        )

        return current + 1


# Singleton
replied_tracker = RepliedTracker()
