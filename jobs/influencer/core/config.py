"""
JOBS/INFLUENCER/CORE/CONFIG.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INFLUENCER CONFIGURATION 🎛️
PURPOSE: Central Source of Truth for all Influencer settings.
PATTERN: Pydantic Model + JSON Persistence.
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from loguru import logger

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

# Persistent Storage
DATA_DIR = MEMORIES_DIR / "influencer"
CONFIG_FILE = DATA_DIR / "config.json"


class InfluencerConfig(BaseModel):
    """
    Master Configuration for Influencer Job.
    Controlled via Web UI or manual JSON edit.
    """

    # ── GLOBAL SWITCHES ──
    # NOTE: 'enabled' is NO LONGER HERE - controlled by memories/jobs.json
    silent_mode: bool = Field(False, description="Run logic but DO NOT post to X")
    approval_mode: bool = Field(
        False, description="Require human approval for ALL tweets"
    )

    # ── MODULE SWITCHES ──
    enable_grok: bool = True
    enable_trinity: bool = True  # Divine Logic Posts
    enable_mentions: bool = True
    enable_youtube: bool = True

    # ── NOTIFICATIONS (Push/UI) ──
    notify_mentions: bool = True
    notify_replies: bool = True
    notify_approvals_trinity: bool = True
    notify_approvals_grok: bool = True
    notify_youtube: bool = True  # SOTA 2026: Alert when YouTube video shared
    notify_viral: bool = True  # SOTA 2026: Alert when tweet goes viral (100+ likes)

    # ── FREQUENCIES (Intervals in minutes/days) ──
    heartbeat_interval_minutes: int = 89  # F89 (Fibonacci)
    grok_interval_hours: int = 24  # 24h
    trinity_interval_hours: int = 24  # 24h
    post_cooldown_minutes: int = 42  # Standard cooldown

    # ── LIMITS ──
    max_posts_per_day: int = 15
    max_replies_per_day: int = 50
    max_replies_per_thread: int = 1  # Standard "One-Shot" rule, now configurable
    spam_filter_enabled: bool = True  # Block crypto/sales spam

    # ── FEATURES ──
    visuals_enabled: bool = False
    priority_only: bool = False


class ConfigManager:
    """Singleton to load/save config."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._cache: Optional[InfluencerConfig] = None

    def load(self) -> InfluencerConfig:
        """Load from disk or return defaults."""
        try:
            raw = load_json(CONFIG_FILE, default={})
            # Validate with Pydantic (fills defaults if missing)
            config = InfluencerConfig(**raw)
            self._cache = config
            return config
        except Exception as e:
            logger.error(f"⚠️ Config load failed, using defaults: {e}")
            return InfluencerConfig()  # type: ignore[call-arg]

    def save(self, config: InfluencerConfig):
        """Save to disk."""
        self._cache = config
        save_json(CONFIG_FILE, config.dict())
        logger.info("💾 Config saved")

    def update(self, updates: Dict) -> InfluencerConfig:
        """Update specific fields."""
        current = self.load()
        # Mix Pydantic copy with update
        updated = current.copy(update=updates)
        self.save(updated)
        return updated


# Global Singleton
config_manager = ConfigManager()
