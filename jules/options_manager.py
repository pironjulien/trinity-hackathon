"""
JULES/OPTIONS_MANAGER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: Jules Options Manager
PURPOSE: Manages Jules configuration options (self-review, nightwatch, etc.)
══════════════════════════════════════════════════════════════════════════════
"""

import json
from pathlib import Path
from typing import TypedDict
from loguru import logger

# Options file path
OPTIONS_FILE = Path("jules/config.json")

# Default options - SOTA 2026: No fake defaults, reflects real intended state
DEFAULT_OPTIONS = {
    "active": False,  # Jules désactivé par défaut, activation explicite requise
    "self_review": True,
    "self_evolution": False,
    # NIGHTWATCH (Guardian Angel): Autonomous failsafe system
    # When enabled + .probation_lock exists:
    #   - Monitors logs every 5s for CRITICAL errors
    #   - Auto-reverts last commit on crash detection
    #   - Records failure in Cortex for cooldown
    #   - Notifies via Phone Widget on blacklist
    "nightwatch": True,
    "sandbox_mode": True,
    "description": "Jules V3 Configuration",
}


class JulesOptions(TypedDict):
    """Type definition for Jules options."""

    active: bool
    self_review: bool
    self_evolution: bool
    nightwatch: bool
    sandbox_mode: bool


def get_options() -> JulesOptions:
    """Load options from config file."""
    try:
        if OPTIONS_FILE.exists():
            data = json.loads(OPTIONS_FILE.read_text())
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_OPTIONS, **data}
        return DEFAULT_OPTIONS.copy()
    except Exception as e:
        logger.error(f"Failed to load Jules options: {e}")
        return DEFAULT_OPTIONS.copy()


def set_options(options: dict) -> bool:
    """Save options to config file."""
    try:
        # Load existing to preserve unknown keys
        current = get_options()
        current.update(options)

        # Write atomically
        OPTIONS_FILE.write_text(json.dumps(current, indent=4))
        logger.info(f"Jules options updated: {options}")
        return True
    except Exception as e:
        logger.error(f"Failed to save Jules options: {e}")
        return False


def is_active() -> bool:
    """Check if Jules is globally active."""
    return get_options().get("active", False)


def is_self_review_enabled() -> bool:
    """Check if self-review is enabled."""
    return get_options().get("self_review", True)


def is_nightwatch_enabled() -> bool:
    """Check if nightwatch is enabled."""
    return get_options().get("nightwatch", True)


def is_sandbox_enabled() -> bool:
    """Check if sandbox mode is enabled."""
    return get_options().get("sandbox_mode", True)


def is_self_evolution_enabled() -> bool:
    """Check if self-evolution is enabled."""
    return get_options().get("self_evolution", False)


# Convenience instance
options_manager = type(
    "OptionsManager",
    (),
    {
        "get": get_options,
        "set": set_options,
        "is_active": is_active,
        "is_self_review_enabled": is_self_review_enabled,
        "is_nightwatch_enabled": is_nightwatch_enabled,
        "is_sandbox_enabled": is_sandbox_enabled,
        "is_self_evolution_enabled": is_self_evolution_enabled,
    },
)()
