"""
JULES/PERSISTENCE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: JULES PERSISTENCE 🧠
PURPOSE: Persistence helpers for Healer, Sentinel, and Strike tracking.
         (Refactored from memory.py - Phase 7 Cleanup)
══════════════════════════════════════════════════════════════════════════════
"""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger
from fnmatch import fnmatch

# ════════════════════════════════════════════════════════════════════════════
# PATHS
# ════════════════════════════════════════════════════════════════════════════

JULES_MEMORY_DIR = Path("memories/jules")
HEALER_HISTORY_FILE = JULES_MEMORY_DIR / "healer_history.json"
SENTINEL_QUEUE_FILE = JULES_MEMORY_DIR / "sentinel_queue.json"
BAD_IDEAS_FILE = JULES_MEMORY_DIR / "bad_ideas.json"
FAILURES_DIR = JULES_MEMORY_DIR / "failures"

# ════════════════════════════════════════════════════════════════════════════
# HEALER MEMORY
# ════════════════════════════════════════════════════════════════════════════


class HealerMemory:
    """
    Tracks treated errors to avoid re-healing the same issue.

    Status:
    - PENDING: Being worked on (cooldown 1h)
    - FIXED: Resolved successfully
    - RECURRING: Error came back after fix (escalate to Night Report)
    """

    COOLDOWN_HOURS = 1
    RECURRENCE_THRESHOLD = 2  # After 2 recurrences, escalate

    def __init__(self):
        self._load()

    def _load(self):
        if HEALER_HISTORY_FILE.exists():
            try:
                self.data = json.loads(HEALER_HISTORY_FILE.read_text())
            except Exception:
                self.data = {"treated_errors": {}}
        else:
            self.data = {"treated_errors": {}}

    def _save(self):
        HEALER_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEALER_HISTORY_FILE.write_text(json.dumps(self.data, indent=2))

    @staticmethod
    def hash_error(error_line: str) -> str:
        """Create a semantic hash for an error (ignores timestamps, PIDs, line numbers).

        SOTA 2026: Proper normalization to prevent duplication storms.
        Identical errors produce identical hashes even if log metadata varies.
        """
        import re

        normalized = error_line.strip()

        # 1. Remove ISO timestamps (2026-01-21T14:55:13.123456, 2026-01-21 14:55:13, etc.)
        normalized = re.sub(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*Z?", "", normalized
        )

        # 2. Remove Unix timestamps (1769006547.140772)
        normalized = re.sub(r"\b\d{10,13}(\.\d+)?\b", "", normalized)

        # 3. Remove PIDs, ports, line numbers (PID: 12345, line 42, :8089)
        normalized = re.sub(r"\bPID[:\s]*\d+", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bline\s*\d+", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r":\d{2,5}\b", "", normalized)  # Ports like :8089

        # 4. Remove UUIDs (a3b8d1b6-0b3b-4b1a-9c1a-1a2b3c4d5e6f)
        normalized = re.sub(
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            "",
            normalized,
            flags=re.IGNORECASE,
        )

        # 5. Remove hex hashes (0x12ab, abc123def)
        normalized = re.sub(r"\b0x[a-f0-9]+\b", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\b[a-f0-9]{12,}\b", "", normalized, flags=re.IGNORECASE)

        # 6. Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # 7. Keep only first 200 chars of NORMALIZED content
        normalized = normalized[:200]

        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def should_heal(self, error_line: str) -> bool:
        """Check if this error should be healed (not in cooldown, not recurring)."""
        error_hash = self.hash_error(error_line)
        entry = self.data["treated_errors"].get(error_hash)

        if not entry:
            return True  # New error, heal it

        # Check cooldown
        last_seen = datetime.fromisoformat(entry.get("last_seen", "2000-01-01"))
        if datetime.now() - last_seen < timedelta(hours=self.COOLDOWN_HOURS):
            logger.debug(f"🩸 [HEALER] Error {error_hash} in cooldown, skipping.")
            return False

        # Check recurrence
        if entry.get("status") == "RECURRING":
            logger.warning(
                f"🩸 [HEALER] Error {error_hash} is recurring, escalating to Night Report."
            )
            return False

        return True

    def mark_pending(self, error_line: str, session_id: str):
        """Mark an error as being worked on."""
        error_hash = self.hash_error(error_line)
        now = datetime.now().isoformat()

        entry = self.data["treated_errors"].get(
            error_hash, {"first_seen": now, "count": 0}
        )

        entry["last_seen"] = now
        entry["count"] = entry.get("count", 0) + 1
        entry["status"] = "PENDING"
        entry["session_id"] = session_id
        entry["error_preview"] = error_line[:100]

        self.data["treated_errors"][error_hash] = entry
        self._save()
        logger.info(
            f"🩸 [HEALER] Marked error {error_hash} as PENDING (attempt #{entry['count']})"
        )

    def mark_fixed(self, error_hash: str):
        """Mark an error as fixed."""
        if error_hash in self.data["treated_errors"]:
            self.data["treated_errors"][error_hash]["status"] = "FIXED"
            self._save()
            logger.success(f"🩸 [HEALER] Error {error_hash} marked as FIXED")

    def mark_recurring(self, error_line: str):
        """Mark an error as recurring (will be escalated)."""
        error_hash = self.hash_error(error_line)
        entry = self.data["treated_errors"].get(error_hash)

        if entry and entry.get("count", 0) >= self.RECURRENCE_THRESHOLD:
            entry["status"] = "RECURRING"
            self._save()
            logger.warning(
                f"🩸 [HEALER] Error {error_hash} marked as RECURRING after {entry['count']} attempts"
            )

    def get_recurring_errors(self) -> List[Dict]:
        """Get all recurring errors for Night Report."""
        return [
            {**entry, "hash": h}
            for h, entry in self.data["treated_errors"].items()
            if entry.get("status") == "RECURRING"
        ]


# ════════════════════════════════════════════════════════════════════════════
# SENTINEL MEMORY (File Rotation)
# ════════════════════════════════════════════════════════════════════════════


class SentinelMemory:
    """
    Tracks which files have been refactored and manages rotation queue.
    """

    COOLDOWN_DAYS = 7
    FORBIDDEN_ZONES = [
        "corpus/dna/*",
        "jules/*",
        "memories/**",
        ".env",
        ".git/*",
        ".venv/*",
        "__pycache__/*",
        "*.pyc",
        "tests/*",  # Don't refactor tests
    ]

    def __init__(self):
        self._load()

    def _load(self):
        if SENTINEL_QUEUE_FILE.exists():
            try:
                self.data = json.loads(SENTINEL_QUEUE_FILE.read_text())
            except Exception:
                self.data = {"queue": [], "last_refactored": {}}
        else:
            self.data = {"queue": [], "last_refactored": {}}

    def _save(self):
        SENTINEL_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SENTINEL_QUEUE_FILE.write_text(json.dumps(self.data, indent=2))

    def is_forbidden(self, filepath: str) -> bool:
        """Check if a file is in a forbidden zone."""
        for pattern in self.FORBIDDEN_ZONES:
            if fnmatch(filepath, pattern):
                return True
        return False

    def populate_queue(self, root_dir: Path):
        """Scan for .py files and populate the queue (excluding forbidden zones)."""
        if self.data["queue"]:
            return  # Already populated

        queue = []
        for py_file in root_dir.rglob("*.py"):
            rel_path = str(py_file.relative_to(root_dir))
            if not self.is_forbidden(rel_path):
                queue.append(rel_path)

        self.data["queue"] = queue
        self._save()
        logger.info(f"🛡️ [SENTINEL] Queue populated with {len(queue)} files")

    def get_next_target(self) -> Optional[str]:
        """Get the next file to refactor."""
        now = datetime.now()

        for filepath in self.data["queue"]:
            last = self.data["last_refactored"].get(filepath)
            if last:
                last_date = datetime.fromisoformat(last)
                if now - last_date < timedelta(days=self.COOLDOWN_DAYS):
                    continue  # Still in cooldown
            return filepath

        return None  # All files in cooldown

    def mark_refactored(self, filepath: str):
        """Mark a file as refactored."""
        self.data["last_refactored"][filepath] = datetime.now().isoformat()

        # Move to end of queue
        if filepath in self.data["queue"]:
            self.data["queue"].remove(filepath)
            self.data["queue"].append(filepath)

        self._save()
        logger.info(f"🛡️ [SENTINEL] Marked {filepath} as refactored")

    def get_forbidden_proposals(self) -> List[str]:
        """Return files that Gattaca wanted to touch but are forbidden (for Night Report)."""
        # This would be populated during conscience_check if Gattaca suggests a forbidden file
        return self.data.get("forbidden_proposals", [])

    def add_forbidden_proposal(self, filepath: str, reason: str):
        """Add a forbidden file proposal for Night Report."""
        if "forbidden_proposals" not in self.data:
            self.data["forbidden_proposals"] = []

        self.data["forbidden_proposals"].append(
            {
                "file": filepath,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save()


# ════════════════════════════════════════════════════════════════════════════
# NIGHT REPORT
# ════════════════════════════════════════════════════════════════════════════


class NightReport:
    """
    Generates the nightly report for human review.
    """

    @staticmethod
    def generate() -> str:
        """Generate the night report content."""
        now = datetime.now()
        healer = HealerMemory()
        sentinel = SentinelMemory()

        report = f"""# 🌙 Night Report - {now.strftime("%Y-%m-%d %H:%M")}

## 🩸 Recurring Errors (Need Human Attention)
"""
        recurring = healer.get_recurring_errors()
        if recurring:
            for err in recurring:
                report += f"- **{err['hash']}**: {err.get('error_preview', 'Unknown')[:60]}... (seen {err['count']}x)\n"
        else:
            report += "_No recurring errors._\n"

        report += """
## 🛡️ Forbidden Zone Proposals
"""
        proposals = sentinel.get_forbidden_proposals()
        if proposals:
            for p in proposals:
                report += f"- **{p['file']}**: {p['reason']}\n"
        else:
            report += "_No proposals for forbidden zones._\n"

        report += """
## 💡 Self-Improvement Ideas
_Trinity can suggest improvements to her own code here._

## 🚀 New Project Ideas
_Ideas for new capabilities or integrations._

---
_Generated by Jules Architect_
"""
        return report

    @classmethod
    def save(cls):
        """Save the night report to disk and send via notifications."""
        now = datetime.now()
        report = cls.generate()

        report_path = JULES_MEMORY_DIR / f"night_report_{now.strftime('%Y%m%d')}.md"
        report_path.write_text(report)
        logger.info(f"📝 [NIGHT REPORT] Saved to {report_path}")

        # Send via notifications
        try:
            import asyncio
            from social.messaging.notification_client import notify

            asyncio.get_event_loop().create_task(
                notify.jules(f"🌙 Night Report ready: {report_path}")
            )
        except Exception as e:
            logger.error(f"Failed to send Night Report notification: {e}")

        return report_path


# ════════════════════════════════════════════════════════════════════════════
# JULES SUGGESTIONS → WISHLIST SYNC
# ════════════════════════════════════════════════════════════════════════════


class JulesSuggestionSync:
    """
    Fetches Jules proactive suggestions and adds them to wishlist.md.
    These suggestions are pre-verified by Jules, so they're safe to execute.
    """

    WISHLIST_FILE = Path("memories/wishlist.md")
    SYNCED_FILE = JULES_MEMORY_DIR / "synced_suggestions.json"

    @classmethod
    def _load_synced(cls) -> List[str]:
        """Load list of already synced suggestion IDs."""
        if cls.SYNCED_FILE.exists():
            try:
                return json.loads(cls.SYNCED_FILE.read_text())
            except Exception:
                return []
        return []

    @classmethod
    def _save_synced(cls, synced: List[str]):
        """Save list of synced suggestion IDs."""
        cls.SYNCED_FILE.parent.mkdir(parents=True, exist_ok=True)
        cls.SYNCED_FILE.write_text(json.dumps(synced))

    @classmethod
    def run_sync(cls) -> int:
        """Synchronous wrapper for sync()."""
        import asyncio

        return asyncio.run(cls.sync())

    @classmethod
    async def sync(cls) -> int:
        """
        Fetch Jules suggestions from BOTH API keys and add Trinity-only ones to wishlist.
        Returns number of new suggestions added.
        """
        try:
            from jules.jules_client import JulesClient, JulesMode
        except ImportError:
            logger.error("Cannot import JulesClient")
            return 0

        synced = cls._load_synced()
        added = 0

        # Sync from BOTH keys
        for mode in [JulesMode.GUARDIAN, JulesMode.CREATOR]:
            try:
                async with JulesClient(mode=mode) as client:
                    logger.info(
                        f"📥 [SYNC] Fetching suggestions from {mode.value} key..."
                    )
                    sessions = await client.list_sessions(page_size=20)

                    for session in sessions:
                        # Skip already synced
                        if session.id in synced:
                            continue

                        # Get details to check repo
                        details = await client.get_session(session.id)
                        if not details:
                            continue

                        # FILTER: Only Trinity repo suggestions
                        # Check title for known Trinity modules or skip alpha-specific
                        title_lower = session.title.lower() if session.title else ""
                        alpha_keywords = ["supervisor.py", "alpha/bin"]
                        trinity_keywords = [
                            "gattaca",
                            "panopticon",
                            "stm",
                            "trinity",
                            "corpus",
                            "jules",
                            "8810",
                        ]

                        is_alpha = any(k in title_lower for k in alpha_keywords)
                        is_trinity = any(k in title_lower for k in trinity_keywords)

                        # Skip if it's clearly for alpha repo (not Trinity)
                        if is_alpha and not is_trinity:
                            continue

                        # Only add sessions without PR (suggestions not yet executed)
                        if not details.pr_url:
                            cls._add_to_wishlist(session.title, session.id)
                            synced.append(session.id)
                            added += 1
                            logger.info(
                                f"📥 [SYNC] Added ({mode.value}): {session.title[:50]}"
                            )
            except Exception as e:
                logger.error(f"Sync error for {mode.value}: {e}")

        cls._save_synced(synced)
        return added

    @classmethod
    def _add_to_wishlist(cls, title: str, session_id: str):
        """Add a suggestion to wishlist.md."""
        cls.WISHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not cls.WISHLIST_FILE.exists():
            cls.WISHLIST_FILE.write_text("# Wishlist\n")

        content = cls.WISHLIST_FILE.read_text()

        # Check if already in wishlist
        if session_id in content or title in content:
            return

        # Add new item with Jules badge
        new_item = f"- [ ] 🤖 {title} (Jules: {session_id})\n"
        content += new_item
        cls.WISHLIST_FILE.write_text(content)
