"""
JOBS/INFLUENCER/RULES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INFLUENCER RULES (SSOT) 📜
PURPOSE: Single Source of Truth for all limits, timings, priorities, and spam filters.
PHILOSOPHY: Defense-first (strict limits), organic timing (Fibonacci).
══════════════════════════════════════════════════════════════════════════════
"""

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

PRIORITIES_FILE = MEMORIES_DIR / "influencer" / "priorities.json"


class Limits:
    """Hard constraints to prevent API bans and spam."""

    # Mentions (Reading)
    MAX_READS_PER_DAY = 2
    MAX_MENTION_AGE_DAYS = 233  # F233 (Fibonacci) ~8 months

    # Replies (Writing)
    MAX_REPLIES_PER_DAY = 10
    # MAX_REPLIES_PER_THREAD moved to config.py

    # Posts (Original Content)
    MAX_POSTS_PER_DAY = 5  # F5

    # History Tracking
    MAX_REPLIED_HISTORY = 500  # Rolling window size


class Timings:
    """Fibonacci-based intervals for organic behavior."""

    # Orchestrator Heartbeat
    HEARTBEAT_INTERVAL_MINUTES = 89  # F89

    # Mentions Routine
    CHECK_INTERVAL_HOURS = 12  # 2x/day

    # Posting Cooldown
    POST_COOLDOWN_MINUTES = 21  # F21

    # Grok Banter
    BANTER_INTERVAL_DAYS = 2  # F2


class Priorities:
    """Hierarchy of attention."""

    _ACCOUNTS = None  # Cache

    DEFAULTS = [
        {"username": "julienpironfr", "description": "Father"},
        {"username": "grok", "description": "Running Gag"},
    ]

    @staticmethod
    def _ensure_loaded():
        if Priorities._ACCOUNTS is None:
            # Ensure dir exists
            PRIORITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
            Priorities._ACCOUNTS = load_json(
                PRIORITIES_FILE, default=Priorities.DEFAULTS
            )

    @staticmethod
    def get_all() -> list:
        """Get list of priority accounts."""
        Priorities._ensure_loaded()
        return Priorities._ACCOUNTS

    @staticmethod
    def save(accounts: list):
        """Save new priority list."""
        Priorities._ACCOUNTS = accounts
        save_json(PRIORITIES_FILE, accounts)

    @staticmethod
    def get_priority(username: str) -> int:
        """Get priority score for a user (lower = higher priority)."""
        Priorities._ensure_loaded()
        username_lower = username.lower()

        for i, acc in enumerate(Priorities._ACCOUNTS):
            if acc["username"].lower() == username_lower:
                return i

        return 999  # Low priority for others


SPAM_KEYWORDS_FILE = MEMORIES_DIR / "influencer" / "spam_words.json"


class SpamFilter:
    """Blocklists to ignore (Dynamic)."""

    _KEYWORDS = None  # Cache

    DEFAULTS = [
        "sales",
        "sale",
        "discount",
        "offer",
        "deal",  # Sales
        "crypto",
        "nft",
        "token",
        "coin",
        "airdrop",
        "whitelist",
        "presale",  # Crypto/Scam
        "dm me",
        "send dm",
        "inbox me",
        "check dm",  # Bot engagement
        "promotion",
        "promote",
        "grow your account",
        "marketing",  # Services
        "messaging",
        "whatsapp",
        "t.me/",  # redirect
        "investment",
        "profit",
        "passive income",  # scams
        "followers",
        "views",
        "likes",  # growth services
    ]

    @staticmethod
    def _ensure_loaded():
        if SpamFilter._KEYWORDS is None:
            # Ensure dir exists
            SPAM_KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SpamFilter._KEYWORDS = load_json(
                SPAM_KEYWORDS_FILE, default=SpamFilter.DEFAULTS
            )

    @staticmethod
    def get_keywords() -> list:
        """Get list of spam keywords."""
        SpamFilter._ensure_loaded()
        return SpamFilter._KEYWORDS

    @staticmethod
    def save(keywords: list):
        """Save new spam keywords list."""
        SpamFilter._KEYWORDS = keywords
        save_json(SPAM_KEYWORDS_FILE, keywords)

    @staticmethod
    def is_spam(text: str) -> bool:
        """Check if text contains spam keywords."""
        SpamFilter._ensure_loaded()
        text_lower = text.lower()
        keywords = SpamFilter._KEYWORDS or []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True
        return False
