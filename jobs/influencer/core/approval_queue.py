"""
JOBS/INFLUENCER/APPROVAL_QUEUE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: APPROVAL QUEUE 🛡️
PURPOSE: Store generated content pending human approval via Phone Widget.
FLOW:
  1. Generator (Grok/Poster) creates draft -> add_to_queue()
  2. Orchestrator sends to Phone Widget
  3. User approves -> get_approved() -> Posting
══════════════════════════════════════════════════════════════════════════════
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

from jobs.influencer.core.rules import Limits

DATA_DIR = MEMORIES_DIR / "influencer"
QUEUE_FILE = DATA_DIR / "approval_queue.json"


class ApprovalQueue:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # SOTA: Added 'approved' for deferred posting (autonomous mode)
        self.queue = {"pending": {}, "approved": {}, "history": []}
        self._reload()

    def _reload(self):
        """Force reload from disk to sync across processes (API vs Worker)."""
        self.queue = load_json(
            QUEUE_FILE, default={"pending": {}, "approved": {}, "history": []}
        )

    def _save(self):
        save_json(QUEUE_FILE, self.queue)

    def add(
        self, content_type: str, text: str, image_path: str = None, meta: dict = None
    ) -> str:
        """
        Add content to approval queue.
        Returns: Unique ID for the approval request.
        """

        self._reload()
        item_id = str(uuid.uuid4())[:8]  # Short ID for callbacks

        self.queue["pending"][item_id] = {
            "id": item_id,
            "type": content_type,
            "text": text,
            "image_path": image_path,
            "meta": meta or {},
            "created_at": datetime.now().isoformat(),
            "status": "PENDING",
        }
        self._save()
        return item_id

    def get(self, item_id: str) -> Optional[Dict]:
        """Get pending item by ID."""

        self._reload()
        return self.queue["pending"].get(item_id)

    def has_pending(self, content_type: str) -> bool:
        """Check if there is a pending item of a specific type."""

        self._reload()
        for item in self.queue.get("pending", {}).values():
            if item.get("type") == content_type:
                return True
        return False

    def get_next_approved(self) -> Optional[Dict]:
        """Get the next approved item for publishing (FIFO)."""

        self._reload()
        approved = self.queue.get("approved", {})
        if not approved:
            return None

        # Sort by approved_at to ensure FIFO
        sorted_items = sorted(approved.values(), key=lambda x: x.get("approved_at", ""))
        return sorted_items[0] if sorted_items else None

    def approve(self, item_id: str) -> Optional[Dict]:
        """
        Mark item as approved.
        MOVES item from pending -> approved.
        Caller is responsible for posting OR letting the orchestrator pick it up.
        """
        self._reload()
        if item_id in self.queue["pending"]:
            item = self.queue["pending"].pop(item_id)
            item["status"] = "APPROVED"
            item["approved_at"] = datetime.now().isoformat()

            # Move to approved queue (for deferred posting)
            # Bot will likely post immediately and then call mark_posted
            # But we store it here first to be safe / support async flows
            if "approved" not in self.queue:
                self.queue["approved"] = {}

            self.queue["approved"][item_id] = item
            self._save()
            return item
        return None

    def mark_posted(self, item_id: str, tweet_id: str = None):
        """Move item from any active queue to history after posting.

        Args:
            item_id: Internal approval queue ID
            tweet_id: X/Twitter tweet ID for metrics tracking (optional)
        """
        item = None
        self._reload()

        # Check approved first
        if "approved" in self.queue and item_id in self.queue["approved"]:
            item = self.queue["approved"].pop(item_id)
        # Check pending (direct post)
        elif item_id in self.queue["pending"]:
            item = self.queue["pending"].pop(item_id)

        if item:
            item["status"] = "POSTED"
            item["posted_at"] = datetime.now().isoformat()
            if tweet_id:
                item["tweet_id"] = tweet_id  # Store X tweet ID for metrics
            self.queue["history"].append(item)
            self.queue["history"] = self.queue["history"][-Limits.MAX_REPLIED_HISTORY :]
            self._save()

    def reject(self, item_id: str):
        """Remove item from queue."""

        self._reload()
        if item_id in self.queue["pending"]:
            item = self.queue["pending"].pop(item_id)
            item["status"] = "REJECTED"
            item["rejected_at"] = datetime.now().isoformat()

            self.queue["history"].append(item)
            self._save()


# Singleton
approval_queue = ApprovalQueue()
