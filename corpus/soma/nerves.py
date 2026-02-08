"""
CORPUS/SOMA/NERVES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CENTRAL NERVOUS SYSTEM (SOTA Logging) ⚡
PURPOSE: Unified logging with dual output: Console (human) + JSONL (API/extension)
══════════════════════════════════════════════════════════════════════════════
"""

import json
import asyncio
from datetime import datetime
from enum import Enum
from loguru import logger
from corpus.dna.genome import LOGS_DIR


# ════════════════════════════════════════════════════════════════════════════
# SIGNAL LEVELS (For NervesSystem pub/sub)
# ════════════════════════════════════════════════════════════════════════════


class SignalLevel(Enum):
    """Signal importance levels for the nervous system."""

    PAIN = "PAIN"  # Critical errors, failures
    PLEASURE = "PLEASURE"  # Success, rewards
    ALERT = "ALERT"  # Warnings, attention needed
    INFO = "INFO"  # General information
    DEBUG = "DEBUG"  # Debug information


# ════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

# JSONL Log Files (must match API endpoints in trinity.py)
JSONL_LOGS = {
    "trinity": LOGS_DIR / "trinity.jsonl",  # /api/logs/trinity
    "alerts": LOGS_DIR / "alerts.jsonl",  # /api/logs/alerts
    "tokens": LOGS_DIR / "tokens.jsonl",  # /api/tokens
    "trader": LOGS_DIR / "trader.jsonl",  # /api/logs/trader
    "youtuber": LOGS_DIR / "youtuber.jsonl",  # /api/logs/youtuber
    "influencer": LOGS_DIR / "influencer.jsonl",  # /api/logs/influencer
    "social": LOGS_DIR / "social.jsonl",  # /api/logs/social
    "jules": LOGS_DIR / "jules.jsonl",  # /api/logs/jules
}

# ════════════════════════════════════════════════════════════════════════════
# 1. RESET LOGURU
# ════════════════════════════════════════════════════════════════════════════

logger.remove()

# ════════════════════════════════════════════════════════════════════════════
# 2. CONSOLE SINK - DISABLED (All logs go to JSONL only)
# ════════════════════════════════════════════════════════════════════════════
# NOTE: No stderr handler = no pollution in VS Code Output panel
# Logs are written to memories/logs/*.jsonl and read via API

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════════════════════════════════
# 3. JSONL SINK (For Extension API - THE ONLY LOG FILES WE NEED)
# ════════════════════════════════════════════════════════════════════════════

# Log Rotation Settings
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_ROTATED_FILES = 7  # Keep 7 days of history


def _rotate_log_if_needed(filepath):
    """Rotate log file if it exceeds MAX_LOG_SIZE_BYTES."""
    try:
        if filepath.exists() and filepath.stat().st_size > MAX_LOG_SIZE_BYTES:
            # Create rotated filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = filepath.with_suffix(f".{timestamp}.jsonl")
            filepath.rename(rotated_path)

            # Cleanup old rotated files (keep only MAX_ROTATED_FILES)
            pattern = filepath.stem + ".*.jsonl"
            rotated_files = sorted(filepath.parent.glob(pattern), reverse=True)
            for old_file in rotated_files[MAX_ROTATED_FILES:]:
                old_file.unlink()
    except Exception:
        pass


def _write_jsonl(filepath, entry):
    """Helper to write a single JSONL entry with auto-rotation."""
    try:
        _rotate_log_if_needed(filepath)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def jsonl_sink(message):
    """
    Custom sink that routes logs to appropriate JSONL files.
    - Each log goes to its module-specific file (trader, youtuber, etc.)
    - WARNING/ERROR/CRITICAL also go to alerts.jsonl
    """
    record = message.record

    # 1. NOISE FILTER: Ignore IPC emit logs (spam) to prevent flooding
    if "/api/ipc/emit" in str(record["message"]):
        return

    # Build structured log entry
    entry = {
        "timestamp": datetime.now().isoformat(),  # CANONICAL: ISO 8601 unique key
        "level": record["level"].name,
        "module": record["name"],
        "function": record["function"],
        "message": record["message"],
    }

    level = record["level"].name
    module = record["name"].lower()

    # SOTA 2026: Also check bound "name" key for direct script execution (__main__)
    bound_name = record.get("extra", {}).get("name", "").lower()

    # 1. Determine the module-specific target file
    # IMPORTANT: Only route jobs.* modules to their specific logs
    # corpus.brain.* should go to trinity (system) logs, not trader!
    if module.startswith("jobs.trader") or bound_name == "trader":
        target = JSONL_LOGS["trader"]
    elif module.startswith("jobs.youtuber") or bound_name == "youtuber":
        target = JSONL_LOGS["youtuber"]
    elif module.startswith("jobs.influencer") or bound_name == "influencer":
        target = JSONL_LOGS["influencer"]
    elif module.startswith("social") or "messaging" in module or bound_name == "social":
        target = JSONL_LOGS["social"]
    elif module.startswith("jules") or bound_name == "jules":
        target = JSONL_LOGS["jules"]
    else:
        target = JSONL_LOGS["trinity"]  # Default: system logs (includes corpus.*)

    # 2. Write to module-specific file (ALL logs)
    _write_jsonl(target, entry)

    # 3. ALSO write to alerts if it's a warning/error
    if level in ["WARNING", "ERROR", "CRITICAL"]:
        _write_jsonl(JSONL_LOGS["alerts"], entry)

    # 4. IPC BROADCAST (DISABLED - Causes Triple Duplication)
    # ══════════════════════════════════════════════════════════════════════════
    # SOTA 2026 FIX: The extension now receives logs via Angel's WebSocket replay.
    # This IPC path was creating duplicate broadcasts:
    #   Path A: nerves → .jsonl file → angel replay → extension
    #   Path B: nerves → IPC → trinity WS broadcast → extension
    #   Path C: angel log_event → WS broadcast → extension
    # SOLUTION: Disable Path B. Angel JSONL replay is the single source of truth.
    # ══════════════════════════════════════════════════════════════════════════
    # try:
    #     payload = {"type": "log", "data": entry}
    #     req = urllib.request.Request(
    #         "http://127.0.0.1:8161/api/ipc/emit",
    #         data=json.dumps(payload).encode('utf-8'),
    #         headers={'Content-Type': 'application/json'}
    #     )
    #     urllib.request.urlopen(req, timeout=0.1)
    # except Exception:
    #     pass


# Add JSONL sink (DEBUG and above - SOTA 2026: Full visibility)
logger.add(jsonl_sink, level="DEBUG", format="{message}")

# ════════════════════════════════════════════════════════════════════════════
# 5. SPECIAL LOGGERS
# ════════════════════════════════════════════════════════════════════════════


def log_tokens(
    model: str,
    route: str,
    prompt_tokens: int,
    completion_tokens: int,
    source: str = "unknown",
    route_id: int = 0,
    icon: str = "🪙",
):
    """Log token usage to tokens.jsonl for tracking."""
    total = prompt_tokens + completion_tokens
    entry = {
        "timestamp": datetime.now().isoformat(),  # CANONICAL: ISO 8601 unique key
        "level": "INFO",  # Required for extension log display
        "model": model,
        "route_id": route_id,
        "route": route,
        "icon": icon,
        "key": "API Key",  # Display name (not actual key)
        "source": source,
        "in": prompt_tokens,
        "out": completion_tokens,
        "total": total,
        "message": f"{icon} {model} | {route} | in:{prompt_tokens} out:{completion_tokens} = {total}",
    }
    try:
        with open(JSONL_LOGS["tokens"], "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    # IPC REMOVED - WebSocket Only Architecture (SOTA 2026)
    # Tokens are read from tokens.jsonl via Angel's WebSocket replay


# ════════════════════════════════════════════════════════════════════════════
# 6. NERVE PUBSUB SYSTEM (For WebSocket broadcasting)
# ════════════════════════════════════════════════════════════════════════════


class NervesSystem:
    """Central nervous system with pub/sub for real-time log streaming."""

    def __init__(self):
        self._subscribers = []

    def subscribe(self, callback):
        """Subscribe to nerve signals."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        """Unsubscribe from nerve signals."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def fire(self, signal: str, level: str, message):
        """Fire a nerve signal (sync version for backward compatibility)."""
        # Log with appropriate level based on signal type
        msg_str = str(message) if not isinstance(message, str) else message
        log_msg = f"[{signal}] {level}"

        if signal in ["WARNING", "URGENT", "CRITICAL"]:
            logger.warning(log_msg)
        elif signal == "SUCCESS":
            logger.success(log_msg)
        else:
            logger.info(log_msg)

        # Safe async broadcast: only if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(signal, level, msg_str))
        except RuntimeError:
            pass  # No event loop yet (startup phase) - skip broadcast

    async def emit(self, signal: str, level: str, message: str):
        """Emit a nerve signal to all subscribers (async)."""
        for callback in self._subscribers:
            try:
                await callback(signal, level, message)
            except Exception:
                pass

    def send(self, level: "SignalLevel", signal: str, message: str):
        """Send a signal with a specific level (convenience method)."""
        self.fire(
            signal,
            level.value if isinstance(level, SignalLevel) else str(level),
            message,
        )


# Singleton
nerves = NervesSystem()

# Make logger available
__all__ = ["logger", "nerves", "log_tokens", "SignalLevel"]
