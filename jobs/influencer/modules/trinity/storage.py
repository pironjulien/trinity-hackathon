"""
JOBS/INFLUENCER/MODULES/TRINITY/STORAGE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TRINITY STORAGE 💾
PURPOSE: Persistence for Divine Logic Posts.
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from corpus.dna.genome import MEMORIES_DIR
from corpus.soma.cells import load_json, save_json
from jobs.influencer.core.config import config_manager
from jobs.influencer.core.approval_queue import approval_queue


class TrinityStorage:
    """Manages persistence for Trinity posts."""

    def __init__(self):
        self.data_dir = MEMORIES_DIR / "influencer"
        self.state_file = self.data_dir / "trinity_state.json"

        # Ensure dir exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # State structure:
        # {
        #   "last_post": "ISO_TIMESTAMP",
        #   "posts": [ { "id": "...", "text": "...", "created_at": "..." } ]
        # }

    def _load(self) -> Dict:
        return load_json(self.state_file, {"last_post": None, "posts": []})

    def _save(self, data: Dict):
        save_json(self.state_file, data)

    def get_last_post_time(self) -> Optional[datetime]:
        """Get timestamp of last Trinity post."""
        data = self._load()
        last = data.get("last_post")
        if last:
            try:
                return datetime.fromisoformat(last)
            except ValueError:
                return None
        return None

    def can_post(self) -> bool:
        """Check if enough time has passed since last post."""
        # 0. Check Pending (Don't spam)
        if approval_queue.has_pending("trinity_logic"):
            return False

        config = config_manager.load()
        interval = timedelta(hours=config.trinity_interval_hours)

        last_post = self.get_last_post_time()
        if not last_post:
            return True  # never posted

        if datetime.now() - last_post > interval:
            return True

        return False

    def add_event(self, text: str, tweet_id: str):
        """Record a successful post."""
        data = self._load()
        now_str = datetime.now().isoformat()

        data["last_post"] = now_str

        # Add to history
        if "posts" not in data:
            data["posts"] = []

        data["posts"].append({"id": tweet_id, "text": text, "created_at": now_str})

        # Limit history size
        if len(data["posts"]) > 50:
            data["posts"] = data["posts"][-50:]

        self._save(data)
