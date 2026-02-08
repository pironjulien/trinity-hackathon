#!/usr/bin/env python3
"""
Angel Supervisor v3.1 (SOTA 2026 - Direct Architecture)
=======================================================
- Responsibility: Lifecycle Management & HTTP Proxy.
- Philosophy: "Disk Truth" & "Self-Healing".
- No WebSockets. No Polling. Direct Process Control.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os

import subprocess
import sys
import threading

from contextlib import asynccontextmanager
from pathlib import Path

import psutil
import uvicorn
import httpx  # Async HTTP client
from fastapi import (
    FastAPI,
    Request,
    Response,
    Header,
    HTTPException,
    Depends,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from typing import Set, Optional, List, Dict
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(BASE_DIR / ".env")

LOGS_DIR = BASE_DIR / "memories" / "logs"
STOP_FLAG_FILE = BASE_DIR / "memories" / ".angel_stop"

ANGEL_PORT = 8089
TRINITY_PORT = 8161
TRINITY_HOST = "127.0.0.1"
MCP_PORT = 8090

# Fibonacci Watchdog Interval (5s is F5)
WATCHDOG_INTERVAL = 5

# Log Paths
os.makedirs(LOGS_DIR, exist_ok=True)
ANGEL_LOG = LOGS_DIR / "angel.jsonl"
ALERTS_LOG = LOGS_DIR / "alerts.jsonl"
TRINITY_LOG = LOGS_DIR / "trinity.jsonl"

# Security: API Key for external access (localhost always allowed)
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")

# Import security utilities
from security import get_real_ip, get_rate_limit_key  # noqa: E402

# Rate Limiter (SOTA 2026: Protect against DoS/brute-force)
limiter = Limiter(key_func=get_rate_limit_key)

# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET HUB (SOTA 2026 - Real-time Logs)
# ══════════════════════════════════════════════════════════════════════════════


class LogsWebSocketHub:
    """Broadcast log events to connected WebSocket clients."""

    def __init__(self):
        self.clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.clients.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.clients.discard(websocket)

    async def broadcast(self, message: dict):
        """Send to all connected clients. Remove dead connections."""
        if not self.clients:
            return

        dead = []
        async with self._lock:
            for client in self.clients:
                try:
                    await client.send_json(message)
                except Exception:
                    dead.append(client)
            for d in dead:
                self.clients.discard(d)

    async def broadcast_clear(self, tab: str):
        """Notify clients that logs were cleared."""
        await self.broadcast({"type": "clear", "tab": tab})

    def client_count(self) -> int:
        return len(self.clients)


ws_hub = LogsWebSocketHub()


# ══════════════════════════════════════════════════════════════════════════════
# 2. LOGGING ENGINE (JSONL Stream)
# ══════════════════════════════════════════════════════════════════════════════

# Shared HTTP Client (Singleton) - SOTA 2026
HTTP_CLIENT: Optional[httpx.AsyncClient] = None


# Level Icons for Console Output
LEVEL_ICONS = {
    "INFO": "🟢",
    "WARNING": "🟡",
    "ERROR": "🔴",
    "DEBUG": "🔵",
    "CRITICAL": "💀",
}


def _format_console_log(timestamp: str, level: str, module: str, message: str) -> str:
    """Format log entry for clean console output."""
    # Extract time portion (HH:MM:SS.mmm)
    try:
        if "T" in timestamp:
            time_part = timestamp.split("T")[1][:12]  # Get HH:MM:SS.mmm
        else:
            time_part = timestamp[:12]
    except Exception:
        time_part = timestamp[:12]

    icon = LEVEL_ICONS.get(level.upper(), "⚪")
    module_str = module[:14].ljust(14)  # Pad/truncate to 14 chars

    # Truncate long messages for console (keep full in JSONL)
    display_msg = message[:80] + "..." if len(message) > 83 else message

    return f"[{time_part}] {icon} {level:<7} │ {module_str} │ {display_msg}"


def log_event(level: str, message: str, stream: str = "angel", **kwargs):
    """Atomic append to JSONL logs. Zero-latency visibility for Extension + WebSocket."""
    timestamp = kwargs.pop("timestamp", None) or datetime.now().isoformat()
    module = kwargs.pop("module", stream.upper())

    entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "module": module,
        "source": stream.upper(),
        **kwargs,
    }

    # SOTA 2026: Dynamic Log Dispatch
    # Map 'stream' to specific file. Fallback to ANGEL_LOG.
    file_map = {
        "angel": ANGEL_LOG,
        "trinity": TRINITY_LOG,
        "alerts": LOGS_DIR / "alerts.jsonl",
        "trader": LOGS_DIR / "trader.jsonl",
        "influencer": LOGS_DIR / "influencer.jsonl",
        "youtuber": LOGS_DIR / "youtuber.jsonl",
        "tokens": LOGS_DIR / "tokens.jsonl",
        "social": LOGS_DIR / "social.jsonl",
    }

    target_file = file_map.get(stream, ANGEL_LOG)

    try:
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # SOTA 2026: Log Rotation (Fibonacci) - Keep 987 lines when exceeding 1597
        _rotate_log_if_needed(target_file, max_lines=1597, keep_lines=987)

        # SOTA 2026: Broadcast to WebSocket clients (fire-and-forget)
        if ws_hub.client_count() > 0:
            asyncio.create_task(ws_hub.broadcast({"type": "log", **entry}))

    except Exception:
        pass  # Never crash the logger


def _rotate_log_if_needed(filepath: Path, max_lines: int, keep_lines: int):
    """Fibonacci log rotation - truncate when exceeding max, keep last N lines."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines[-keep_lines:])
    except Exception:
        pass


def _kill_zombie_processes():
    """
    SOTA 2026: Surgical Zombie Removal.
    - Angel: Prevents duplicates (HL mode).
    - Trinity: Enforces SINGLETON by killing any PID that is not the managed child.
    """
    try:
        my_pid = os.getpid()
        managed_trinity_pid = (
            trinity_manager.process.pid
            if trinity_manager.process and trinity_manager.is_running()
            else None
        )

        for script_name in ["angel.py", "trinity.py"]:
            # 1. Gather all PIDs running this script
            pids = []
            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    cmdline = " ".join(proc.info["cmdline"] or [])
                    # Strict match to avoid false positives (e.g. metrics_bridge.py)
                    if script_name in cmdline and "python" in cmdline.lower():
                        if proc.info["pid"] != my_pid:
                            pids.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # 2. DECIDE: Kill logic based on type
            if script_name == "angel.py":
                # Angel Logic: Highlander (There can be only one - the newest)
                if len(pids) > 1:
                    pids.sort()
                    zombies = pids[:-1]  # Keep newest (assumed self), kill older
                    for z_pid in zombies:
                        # Self-preservation: Don't kill myself if I was in the list (already filtered above)
                        _kill_pid(z_pid, "angel", "🧟 Angel Duplicate")

            elif script_name == "trinity.py":
                # Trinity Logic: The Chosen One
                # If we manage a Trinity, ANY other Trinity PID is a zombie.
                # If we don't manage a Trinity, ALL Trinity PIDs are zombies.
                for z_pid in pids:
                    if z_pid != managed_trinity_pid:
                        _kill_pid(z_pid, "trinity", "🧟 Trinity Orphan")
    except Exception:
        pass


def _kill_pid(pid: int, heuristic: str, reason: str):
    """Helper to kill a PID with logging."""
    try:
        proc = psutil.Process(pid)
        log_event(
            "WARNING",
            f"{reason} killed",
            "angel",
            module="ANGEL",
            pid=pid,
            target=heuristic,
        )
        proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 3. SUBPROCESS MANAGER (The Puppet Master)
# ══════════════════════════════════════════════════════════════════════════════


class SubProcessManager:
    def __init__(self, name: str, script: str, port: Optional[int] = None):
        self.name = name
        self.script = script
        self.port = port
        self.process = None
        self.stop_requested = False

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self):
        if self.is_running():
            return

        # 1. Cleanup
        if self.port:
            self._kill_port_holder(self.port)
        subprocess.run(["pkill", "-f", f"python.*{self.script}"], check=False)

        # 2. Spawn
        log_event("INFO", f"🚀 {self.name} spawn", "angel", module="ANGEL")
        cmd = [sys.executable, self.script]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        # 3. Attach Log Streamers
        if self.process.stdout:
            threading.Thread(
                target=self._stream_reader,
                args=(self.process.stdout, "INFO"),
                daemon=True,
            ).start()
        if self.process.stderr:
            threading.Thread(
                target=self._stream_reader,
                args=(self.process.stderr, "ERROR"),
                daemon=True,
            ).start()

    def stop(self):
        self.stop_requested = True
        if self.process and self.is_running():
            log_event("INFO", f"⏹️ {self.name} stop", "angel", module="ANGEL")
            try:
                self.process.terminate()
                self.process.wait(
                    timeout=5
                )  # F5: Give time for graceful cleanup (DuckDB)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def _kill_port_holder(self, port):
        """Force kill anything hogging the port."""
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                for conn in proc.connections(kind="inet"):
                    if conn.laddr.port == port:
                        if proc.pid != os.getpid():
                            proc.kill()
            except Exception:
                pass

    def _stream_reader(self, stream, default_level):
        """Capture subprocess output. Trinity logs directly to JSONL now."""
        import re

        # SOTA 2026: ANSI Strip Pattern (Vital for Loguru colors)
        ansi_escape = re.compile(r"\x1B\[[0-9;]*[mK]")

        # SOTA 2026: Loguru level pattern (e.g., "| INFO |", "| ERROR |")
        loguru_level_pattern = re.compile(
            r"\|\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\|"
        )
        # SOTA 2026: Standard/Uvicorn level pattern (e.g., "INFO:", "WARNING:")
        standard_level_pattern = re.compile(r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL):\s*")

        if not stream:
            return
        for line in iter(stream.readline, ""):
            line = line.strip()
            if not line:
                continue

            # Filter IPC noise
            if "/api/ipc/emit" in line or "/api/vitals" in line:
                continue

            # SOTA 2026: Strip ANSI for logic, keep for log?
            # Actually, we want to log the CLEAN line to JSONL for readability/parsing downstream.
            # The console output (human) might want colors, but _format_console_log handles that separately?
            # Start by using clean_line for detection.
            clean_line = ansi_escape.sub("", line)

            # SOTA 2026: Extract true log level from Loguru format
            # Loguru sends all logs to stderr, so we parse the actual level
            level = default_level
            level_match = loguru_level_pattern.search(clean_line)
            if level_match:
                level = level_match.group(1)
            else:
                # Fallback: Check standard/Uvicorn format (INFO:, WARNING:, etc.)
                # Use clean_line here too
                standard_match = standard_level_pattern.match(clean_line)
                if standard_match:
                    level = standard_match.group(1)

            # SOTA 2026: Trinity logs directly to JSONL now
            # Only capture actual errors/crashes for visibility (not INFO on stderr)
            if self.name == "Trinity" and level not in ("ERROR", "CRITICAL", "WARNING"):
                continue

            # SOTA 2026: Skip logs from jobs that have their own sinks
            # Trinity routes JOBS.TRADER/INFLUENCER/YOUTUBER to their own JSONL files
            # Re-logging them here would create duplicates
            job_prefixes = ("JOBS.TRADER", "JOBS.INFLUENCER", "JOBS.YOUTUBER")
            if self.name == "Trinity" and any(p in clean_line for p in job_prefixes):
                continue

            # Route to subprocess's own log file (trinity → trinity.jsonl)
            target_stream = (
                self.name.lower()
                if self.name.lower() in ["trinity", "trader", "influencer", "youtuber"]
                else "angel"
            )
            # Log the CLEAN line to avoid junk in JSONL
            log_event(
                level,
                clean_line,
                target_stream,
                module=self.name,
                source="ANGEL",
                func="_stream_reader",
            )


# Instantiate Managers
trinity_manager = SubProcessManager("Trinity", "trinity.py", TRINITY_PORT)
trinity_manager.stop_requested = True  # User must click GO to start Trinity
metrics_manager = SubProcessManager("Metrics", "metrics_bridge.py")
mcp_manager = SubProcessManager("MCP", "corpus/brain/mcp_server.py", MCP_PORT)
mcp_manager.stop_requested = True  # SOTA 2026: Disabled, kept for future use

# ══════════════════════════════════════════════════════════════════════════════
# 4. SUPERVISOR APP (FastAPI)
# ══════════════════════════════════════════════════════════════════════════════

ZOMBIE_CHECK_COUNTER = (
    0  # Counter for zombie check (F12=144 iterations = ~12 min at 5s interval)
)

# ══════════════════════════════════════════════════════════════════════════════
# CANARY ROLLBACK SYSTEM (Post-Jules Merge Protection)
# ══════════════════════════════════════════════════════════════════════════════

CRASH_COUNTER = 0  # Consecutive crashes since last Jules merge
LAST_JULES_MERGE_TIME = None  # Timestamp of last Jules merge
CANARY_WINDOW_SECONDS = 300  # 5 minutes window for crash detection
MAX_CRASHES_BEFORE_REVERT = 3  # Trigger revert after 3 crashes
MAX_REVERTS = 2  # Stop after 2 reverts and notify user
REVERT_COUNTER_FILE = BASE_DIR / "memories" / "jules" / ".revert_count"
CANARY_REVERT_IN_PROGRESS = False  # Reentrant guard to prevent multiple triggers


def _get_revert_count() -> int:
    """Get current revert count from disk."""
    if REVERT_COUNTER_FILE.exists():
        try:
            return int(REVERT_COUNTER_FILE.read_text().strip())
        except Exception:
            return 0
    return 0


def _increment_revert_count() -> int:
    """Increment and persist revert count."""
    count = _get_revert_count() + 1
    REVERT_COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    REVERT_COUNTER_FILE.write_text(str(count))
    return count


def _reset_revert_count():
    """Reset revert count (call after successful stability)."""
    if REVERT_COUNTER_FILE.exists():
        REVERT_COUNTER_FILE.unlink()


def _check_last_jules_merge():
    """Check if there was a recent Jules merge by reading heart state."""
    global LAST_JULES_MERGE_TIME
    merge_marker = BASE_DIR / "memories" / "jules" / ".last_merge"
    if merge_marker.exists():
        try:
            timestamp_str = merge_marker.read_text().strip()
            LAST_JULES_MERGE_TIME = datetime.fromisoformat(timestamp_str)
        except Exception:
            pass


def _is_in_canary_window() -> bool:
    """Check if we're within the 5-minute canary window after a Jules merge."""
    if LAST_JULES_MERGE_TIME is None:
        return False
    elapsed = (datetime.now() - LAST_JULES_MERGE_TIME).total_seconds()
    return elapsed < CANARY_WINDOW_SECONDS


async def _send_system_alert(message: str):
    """Send system alert (Unified Notification System)."""
    # SOTA 2026: Route to Notification Hub (WS + FCM)
    await _dispatch_notification(
        source="ANGEL", message=message, priority="ALERT", title="🚨 SYSTEM ALERT"
    )


async def _perform_canary_revert():
    """Emergency rollback: git revert HEAD and restart Trinity."""
    global CRASH_COUNTER, LAST_JULES_MERGE_TIME, CANARY_REVERT_IN_PROGRESS

    # GUARD 1: Reentrant protection - prevent multiple triggers
    if CANARY_REVERT_IN_PROGRESS:
        log_event(
            "WARNING",
            "🔄 Revert skipped",
            "angel",
            module="ANGEL",
            reason="already in progress",
        )
        return

    # GUARD 2: Sanity check - must have actual crashes to revert
    if CRASH_COUNTER < MAX_CRASHES_BEFORE_REVERT:
        log_event(
            "ERROR",
            "⚠️ Revert aborted",
            "angel",
            module="ANGEL",
            crashes=CRASH_COUNTER,
            threshold=MAX_CRASHES_BEFORE_REVERT,
        )
        return

    CANARY_REVERT_IN_PROGRESS = True
    crashes_at_trigger = CRASH_COUNTER  # Capture before any reset

    try:
        # Check revert limit
        current_reverts = _get_revert_count()
        if current_reverts >= MAX_REVERTS:
            log_event(
                "CRITICAL",
                "🛑 Max reverts hit",
                "angel",
                module="ANGEL",
                count=MAX_REVERTS,
            )

            # Send System alert
            await _send_system_alert(
                f"🚨 <b>CANARY ALERT - INTERVENTION REQUISE</b>\n\n"
                f"Trinity a crash {MAX_CRASHES_BEFORE_REVERT}x après un merge Jules.\n"
                f"<b>{MAX_REVERTS} reverts</b> ont déjà été effectués sans succès.\n\n"
                f"⚠️ L'auto-revert est désactivé.\n"
                f"Action manuelle requise."
            )

            # Clear markers to stop the loop
            merge_marker = BASE_DIR / "memories" / "jules" / ".last_merge"
            if merge_marker.exists():
                merge_marker.unlink()
            CRASH_COUNTER = 0
            LAST_JULES_MERGE_TIME = None
            return

        log_event(
            "CRITICAL",
            "🚨 Canary rollback",
            "angel",
            module="ANGEL",
            attempt=current_reverts + 1,
            max_attempts=MAX_REVERTS,
            crashes=crashes_at_trigger,
        )

        # Get HEAD before revert to verify later
        head_before = await asyncio.to_thread(
            subprocess.run,
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            timeout=10,
        )
        head_before_sha = (
            head_before.stdout.strip() if head_before.returncode == 0 else None
        )

        # SOTA 2026: Stash dirty working tree before revert (prevents conflicts)
        await asyncio.to_thread(
            subprocess.run,
            ["git", "stash", "--include-untracked", "-m", "canary-auto-stash"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            timeout=15,
        )

        # Git Revert - run in thread to avoid blocking loop
        result = await asyncio.to_thread(
            subprocess.run,
            ["git", "revert", "--no-edit", "HEAD"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            timeout=30,
        )

        # Log revert result for debugging
        if result.returncode != 0:
            log_event(
                "ERROR",
                "🔴 Revert failed",
                "angel",
                module="ANGEL",
                stderr=result.stderr[:200],
            )

        if result.returncode == 0:
            # GUARD 3: Verify git actually created a new commit
            head_after = await asyncio.to_thread(
                subprocess.run,
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=BASE_DIR,
                timeout=10,
            )
            head_after_sha = (
                head_after.stdout.strip() if head_after.returncode == 0 else None
            )

            if head_before_sha and head_after_sha and head_before_sha == head_after_sha:
                log_event(
                    "ERROR",
                    "🔴 Revert no-op",
                    "angel",
                    module="ANGEL",
                    head=head_before_sha[:8],
                )
                return

            revert_num = _increment_revert_count()
            log_event(
                "INFO",
                "✅ Revert success",
                "angel",
                module="ANGEL",
                attempt=revert_num,
                head_before=head_before_sha[:8] if head_before_sha else None,
                head_after=head_after_sha[:8] if head_after_sha else None,
            )

            # Log to alerts for visibility
            alert_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": "CRITICAL",
                "message": f"🚨 CANARY ROLLBACK #{revert_num}: Reverted Jules merge after {crashes_at_trigger} crashes",
                "module": "ANGEL",
                "action": "git_revert",
                "head_before": head_before_sha[:8] if head_before_sha else None,
                "head_after": head_after_sha[:8] if head_after_sha else None,
            }
            try:
                with open(ALERTS_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(alert_entry) + "\n")
            except Exception:
                pass

            # Send System notification
            await _send_system_alert(
                f"⚠️ <b>CANARY REVERT #{revert_num}</b>\n\n"
                f"Trinity a crash {crashes_at_trigger}x après un merge Jules.\n"
                f"Git revert effectué automatiquement.\n"
                f"Reverts restants: {MAX_REVERTS - revert_num}"
            )
        else:
            log_event(
                "ERROR",
                "🔴 Revert failed",
                "angel",
                module="ANGEL",
                stderr=result.stderr[:150],
            )
    except Exception as e:
        log_event(
            "ERROR",
            "💥 Revert error",
            "angel",
            module="ANGEL",
            error=str(e),
        )
    finally:
        # ALWAYS clear merge marker to prevent infinite loop (even if revert failed)
        merge_marker = BASE_DIR / "memories" / "jules" / ".last_merge"
        if merge_marker.exists():
            try:
                merge_marker.unlink()
            except Exception:
                pass
        # Reset crash counter (but keep revert counter)
        CRASH_COUNTER = 0
        LAST_JULES_MERGE_TIME = None
        CANARY_REVERT_IN_PROGRESS = False


async def watchdog_loop():
    """Self-Healing Mechanism (Golden Ratio Interval: 5s)."""
    global ZOMBIE_CHECK_COUNTER, CRASH_COUNTER

    # Initial check for recent Jules merge
    _check_last_jules_merge()

    while True:
        await asyncio.sleep(WATCHDOG_INTERVAL)
        ZOMBIE_CHECK_COUNTER += 1

        # Refresh Jules merge status periodically
        if ZOMBIE_CHECK_COUNTER % 12 == 0:  # Every ~60s
            _check_last_jules_merge()

        # 1. Metrics Bridge (Critical for UI Stats)
        if not metrics_manager.is_running() and not metrics_manager.stop_requested:
            log_event(
                "WARNING",
                "🔄 Bridge resurrect",
                "angel",
                module="ANGEL",
            )
            metrics_manager.start()

        # 1.5. MCP Server - DISABLED (SOTA 2026: Kept for future use, no resurrect)

        # 2. Trinity (Worker) - With Canary Protection
        if not trinity_manager.is_running() and not trinity_manager.stop_requested:
            log_event(
                "WARNING",
                "🔄 Trinity resurrect",
                "angel",
                module="ANGEL",
            )

            # CANARY CHECK: If in canary window, increment crash counter
            if _is_in_canary_window():
                CRASH_COUNTER += 1
                log_event(
                    "WARNING",
                    "🐤 Canary crash",
                    "angel",
                    module="ANGEL",
                    count=CRASH_COUNTER,
                    threshold=MAX_CRASHES_BEFORE_REVERT,
                )

                if CRASH_COUNTER >= MAX_CRASHES_BEFORE_REVERT:
                    await _perform_canary_revert()
                    # Don't resurrect yet, let the revert settle
                    await asyncio.sleep(5)
            else:
                # Outside canary window, reset crash counter
                CRASH_COUNTER = 0

            trinity_manager.start()

        # 2b. Trinity STABLE CHECK: Reset revert counter if running well
        # (Trinity running + outside canary window + every 120 checks = ~10 min)
        if trinity_manager.is_running() and not _is_in_canary_window():
            if ZOMBIE_CHECK_COUNTER % 120 == 0 and _get_revert_count() > 0:
                _reset_revert_count()
                log_event(
                    "INFO",
                    "✅ Canary stable",
                    "angel",
                    module="ANGEL",
                )

        # 3. Zombie Check (Every ~12 min = F12=144 * 5s)
        if ZOMBIE_CHECK_COUNTER % 144 == 0:  # F12 ~ 12 minutes
            _kill_zombie_processes()

        # Reset counter to avoid overflow (though unlikely)
        if ZOMBIE_CHECK_COUNTER >= 14400:
            ZOMBIE_CHECK_COUNTER = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_event(
        "INFO",
        "👼 Angel online",
        "angel",
        module="ANGEL",
    )

    if not ANGEL_API_KEY:
        log_event(
            "WARNING",
            "⚠️ ANGEL_API_KEY missing! Remote access is unsecured/limited.",
            "angel",
            module="SECURITY",
        )

    # Init: Honor user's stop request from previous session
    # If STOP_FLAG_FILE exists, user explicitly stopped Trinity - keep it stopped
    if STOP_FLAG_FILE.exists():
        trinity_manager.stop_requested = True
        log_event(
            "INFO",
            "🛑 Trinity paused",
            "angel",
            module="ANGEL",
        )
        # NOTE: Don't delete the file - it's deleted by /sys/start when user clicks GO

    # SOTA 2026: Init Shared HTTP Client
    # Optimize for local proxy + external API calls
    global HTTP_CLIENT
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=40)
    HTTP_CLIENT = httpx.AsyncClient(limits=limits, timeout=30.0)

    # Purge Zombies on Startup (Clean Slate)
    _kill_zombie_processes()

    # Start Children (Metrics ONLY - Trinity is started via /sys/start)
    metrics_manager.start()
    # NOTE: Trinity is NOT auto-started. User must click "GO" button.

    # Enable Watchdog
    asyncio.create_task(watchdog_loop())

    # Enable Proactive Triggers

    yield

    # Shutdown
    if HTTP_CLIENT:
        await HTTP_CLIENT.aclose()
        HTTP_CLIENT = None

    trinity_manager.stop()
    metrics_manager.stop()
    log_event("INFO", "💀 Angel stop", "angel", module="ANGEL")


app = FastAPI(title="Angel Supervisor", lifespan=lifespan)

# Rate Limiting
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    SOTA 2026: Add security headers to all responses.
    Protects against clickjacking, MIME sniffing, XSS.
    """
    response = await call_next(request)
    # SOTA 2026 FIX: Allow embedding in VS Code Webview
    # response.headers["X-Frame-Options"] = "DENY"  # BLOCKS IFRAME
    # SOTA 2026 FIX: Allow embedding in VS Code Webview (Explicit Schemes)
    # response.headers["X-Frame-Options"] = "DENY"  # BLOCKS IFRAME
    # SOTA 2026: NO frame-ancestors - Allow VSCode Extension webview embedding
    # VSCode uses dynamic vscode-webview:// origins that cannot be whitelisted
    # Security maintained via CORS + auth tokens
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # SOTA 2026: Allow Google OAuth popup flow (Standard 432.6)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    return response


app.add_middleware(
    CORSMiddleware,
    # SOTA 2026 Security: Restrict CORS to trusted origins
    allow_origins=[
        "vscode-webview://*",
        "https://vscode-webview.net",
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://trinity.julienpiron.fr",
        "https://julienpiron.fr",
        # SOTA 2026: Mobile (Capacitor) Origins
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINTS (SOTA 2026 - Real-time Logs)
# ══════════════════════════════════════════════════════════════════════════════


def _load_history(lines: int = 89) -> list:
    """
    Load last N lines from all log files (Golden Ratio = 89).
    SOTA 2026: Guarantee minimum per stream so no tab is empty.
    """
    allowed_logs = {
        "angel": ANGEL_LOG,
        "trinity": TRINITY_LOG,
        "alerts": LOGS_DIR / "alerts.jsonl",
        "social": LOGS_DIR / "social.jsonl",
        "jules": LOGS_DIR / "jules.jsonl",
        "trader": LOGS_DIR / "trader.jsonl",
        "influencer": LOGS_DIR / "influencer.jsonl",
        "youtuber": LOGS_DIR / "youtuber.jsonl",
        "tokens": LOGS_DIR / "tokens.jsonl",
    }

    # Fibonacci minimum per stream to guarantee visibility
    min_per_stream = 21

    all_logs = []
    for stream, filepath in allowed_logs.items():
        if not filepath.exists():
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                # Read more lines per file to ensure we have enough
                file_lines = f.readlines()[-(min_per_stream * 3) :]
            stream_logs = []
            for line in file_lines:
                try:
                    entry = json.loads(line.strip())
                    entry.setdefault("source", stream.upper())
                    stream_logs.append(entry)
                except json.JSONDecodeError:
                    pass
            # Take last min_per_stream from this stream
            all_logs.extend(stream_logs[-min_per_stream:])
        except Exception:
            pass

    # Sort by timestamp and return ALL (each stream already limited to min_per_stream)
    all_logs.sort(key=lambda x: x.get("timestamp", ""))
    return all_logs


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket, token: Optional[str] = None):
    """
    SOTA 2026: Real-time log streaming via WebSocket.
    - Auth: ?token=xxx query param (bootstrap token)
    - On connect: Send 89 lines of history (Golden Ratio)
    - Live: Push each new log as it's written
    """
    # Auth Check
    bootstrap_token = os.getenv("ANGEL_BOOTSTRAP_TOKEN")
    client_ip = websocket.client.host if websocket.client else ""

    # Allow localhost OR valid token
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
    is_valid_token = bootstrap_token and token == bootstrap_token

    if not is_localhost and not is_valid_token:
        await websocket.close(code=4003, reason="Unauthorized")
        return

    # Accept and register
    await ws_hub.connect(websocket)

    try:
        # SOTA 2026: Send history FIRST before any log_event (avoids race condition)
        history = _load_history(89)
        await websocket.send_json({"type": "history", "logs": history})

        # Keep alive loop - wait for client disconnect
        while True:
            try:
                # Wait for any message (ping/pong or close)
                await asyncio.wait_for(websocket.receive_text(), timeout=300)
            except asyncio.TimeoutError:
                # Send ping to check if client is alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ws_hub.disconnect(websocket)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ROUTES
# ══════════════════════════════════════════════════════════════════════════════


async def verify_api_key(request: Request, x_angel_key: str = Header(None)):
    """Security: Allow localhost OR Bootstrap Token (SOTA 2026: Real IP behind proxy)."""
    client_ip = get_real_ip(request)
    # SOTA 2026: Bootstrap Token (Shared Secret for Offline UI)
    bootstrap_token = os.getenv("ANGEL_BOOTSTRAP_TOKEN")

    # 1. Allow Localhost (VS Code extension / Internal)
    if client_ip in ("127.0.0.1", "::1", "localhost"):
        return True

    # 2. Check for Bootstrap Token (Frontend) OR Admin API Key (External)
    has_valid_admin_key = ANGEL_API_KEY and x_angel_key == ANGEL_API_KEY
    has_valid_bootstrap = bootstrap_token and x_angel_key == bootstrap_token

    if not has_valid_admin_key and not has_valid_bootstrap:
        log_event(
            "WARNING",
            "🛡️ Access denied",
            "angel",
            module="ANGEL",
            ip=client_ip,
            provided_key=x_angel_key[:4] + "***" if x_angel_key else "None",
        )
        raise HTTPException(status_code=403, detail="Invalid Credentials")

    return True


@app.post("/sys/start", dependencies=[Depends(verify_api_key)])
async def sys_start():
    # Clear stop flag (user wants Trinity to run)
    trinity_manager.stop_requested = False
    if STOP_FLAG_FILE.exists():
        try:
            os.remove(STOP_FLAG_FILE)
        except Exception:
            pass

    # Proactive cleanup before start (Highlander Rule)
    _kill_zombie_processes()

    trinity_manager.start()
    return {"status": "started"}


@app.post("/sys/stop", dependencies=[Depends(verify_api_key)])
async def sys_stop():
    trinity_manager.stop()

    # Ensure nothing was left behind (Double Tap)
    _kill_zombie_processes()

    with open(STOP_FLAG_FILE, "w") as f:
        f.write("User Requested Stop")
    return {"status": "stopped"}


@app.get("/sys/status")
async def sys_status():
    # SOTA 2026: Include language for 8810 extension sync
    lang = "en"
    try:
        if TRINITY_CONFIG_PATH.exists():
            config = json.loads(TRINITY_CONFIG_PATH.read_text())
            lang = config.get("language", "en")
    except Exception:
        pass
    return {
        "angel": "online",
        "trinity": "running" if trinity_manager.is_running() else "stopped",
        "language": lang,
    }


@app.post("/api/ipc/emit")
async def ipc_emit(request: Request):
    """
    SOTA 2026: IPC Endpoint for Trinity to broadcast logs to WebSocket clients.
    Trinity writes to JSONL files and calls this to push to real-time viewers.
    """
    try:
        entry = await request.json()
        # Broadcast to WebSocket clients
        if ws_hub.client_count() > 0:
            await ws_hub.broadcast({"type": "log", **entry})
        return {"status": "ok"}
    except Exception:
        return {"status": "error"}


@app.get("/logs/read", dependencies=[Depends(verify_api_key)])
async def read_logs(
    log: str = "trinity", lines: int = 100, since: Optional[str] = None
):
    """
    SOTA 2026: Read logs from disk (JSONL source of truth).
    Allowed logs: angel, trinity, alerts, trader, influencer, youtuber, tokens.
    Args:
        log: Log type or "all" for aggregated stream.
        lines: Max lines to return if 'since' is not used (default 100)
        since: ISO timestamp. If provided, returns ALL logs after this time.
    """
    allowed_logs = {
        "angel": "angel.jsonl",
        "trinity": "trinity.jsonl",
        "alerts": "alerts.jsonl",
        "trader": "trader.jsonl",
        "influencer": "influencer.jsonl",
        "youtuber": "youtuber.jsonl",
        "tokens": "tokens.jsonl",
        "jules": "jules.jsonl",
        "social": "social.jsonl",
    }

    if log != "all" and log not in allowed_logs:
        raise HTTPException(status_code=400, detail="Invalid log type")

    # Helper to read a single file
    def read_file(filepath: Path, limit: int, since_ts: Optional[str]):
        if not filepath.exists():
            return []

        results = []
        try:
            # Optimization: Read more lines if we need deep history for a merge
            # If 'all' mode, we might need smaller chunks per file to avoid huge payloads,
            # but we filter by 'since' anyway.
            with open(filepath, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            # If we rely on lines limit, we take tail.
            # If 'since', we scan deeper (e.g. 2000 lines).
            scan_lines = 2000 if since_ts else limit

            for line in all_lines[-scan_lines:]:
                try:
                    entry = json.loads(line.strip())
                    entry_ts = entry.get("timestamp", "")

                    if since_ts:
                        if entry_ts > since_ts:
                            results.append(entry)
                    else:
                        results.append(entry)
                except json.JSONDecodeError:
                    pass

            # If no cursor, limit count
            if not since_ts and len(results) > limit:
                results = results[-limit:]

            return results
        except Exception:
            return []

    try:
        final_logs = []

        if log == "all":
            # Aggregate ALL files
            for log_type, filename in allowed_logs.items():
                # Skip tokens for general log stream (handled separately by UI mostly, but extension includes them?)
                # user Request says "same as extension". Extension ProcessManager reads tokens.jsonl too.
                # So we include everything.
                file_logs = read_file(LOGS_DIR / filename, lines, since)
                final_logs.extend(file_logs)

            # Sort aggregated logs by timestamp
            final_logs.sort(key=lambda x: x.get("timestamp", ""))

            # Cap global limit if not using since (prevent returning 7000 lines)
            if not since and len(final_logs) > lines * 2:
                final_logs = final_logs[-(lines * 2) :]

        else:
            # Single file mode
            final_logs = read_file(LOGS_DIR / allowed_logs[log], lines, since)

        return {"logs": final_logs}

    except Exception as e:
        log_event("ERROR", f"Failed to read logs: {e}", "angel", module="API")
        return {"logs": [], "error": str(e)}


# SOTA 2026: Jobs status endpoint - read from memories/jobs.json
JOBS_FILE = BASE_DIR / "memories" / "jobs.json"


@app.get("/logs/clear", dependencies=[Depends(verify_api_key)])
async def clear_logs(tab: str = "TRINITY"):
    """
    Clear logs for a specific tab/stream.
    """
    tab = tab.upper()

    files_to_clear = []

    if tab == "ANGEL":
        files_to_clear.append(LOGS_DIR / "angel.jsonl")
    elif tab == "ALERTS":
        files_to_clear.append(LOGS_DIR / "alerts.jsonl")
    elif tab == "TRINITY":
        # Trinity tab usually shows trinity.jsonl, but sometimes system stuff.
        # Safest is just trinity.jsonl
        files_to_clear.append(LOGS_DIR / "trinity.jsonl")
    elif tab in ["TRADER", "YOUTUBER", "INFLUENCER"]:
        files_to_clear.append(LOGS_DIR / f"{tab.lower()}.jsonl")
    elif tab == "TOKENS":
        files_to_clear.append(LOGS_DIR / "tokens.jsonl")

    try:
        for p in files_to_clear:
            if p.exists():
                # Truncate file
                with open(p, "w", encoding="utf-8") as f:
                    f.write("")

        log_event("INFO", f"🧹 Logs cleared for {tab}", "angel", module="API")
        return {"status": "cleared", "tab": tab}

    except Exception as e:
        log_event("ERROR", f"Failed to clear logs: {e}", "angel", module="API")
        return {"error": str(e)}


@app.get("/jobs/status")
async def jobs_status():
    """Return current jobs state - only true if Trinity is running AND job enabled"""
    try:
        # Jobs are only ACTIVE if Trinity is running
        trinity_running = trinity_manager.is_running()

        if JOBS_FILE.exists():
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                jobs_data = json.load(f)

            def get_enabled(job_name):
                job = jobs_data.get(job_name, {})
                if isinstance(job, dict):
                    return job.get("enabled", False)
                return bool(job)

            # SOTA 2026: Read Jules state from its config file (different from jobs.json)
            jules_active = False
            jules_config_path = BASE_DIR / "jules" / "config.json"
            if jules_config_path.exists():
                try:
                    jules_cfg = json.loads(jules_config_path.read_text())
                    jules_active = jules_cfg.get("active", False)
                except Exception:
                    pass

            # Only return True if Trinity running AND enabled in config
            return {
                "trader": trinity_running and get_enabled("trader"),
                "youtuber": trinity_running and get_enabled("youtuber"),
                "influencer": trinity_running and get_enabled("influencer"),
                "jules": trinity_running and jules_active,
            }
    except Exception as e:
        log_event(
            "ERROR",
            "🔴 Jobs read error",
            "angel",
            module="ANGEL",
            error=str(e),
        )
    return {"trader": False, "youtuber": False, "influencer": False, "jules": False}


@app.post("/jobs/toggle", dependencies=[Depends(verify_api_key)])
async def jobs_toggle(job: str, enabled: bool):
    """Toggle a job's enabled state and notify Trinity for immediate effect."""
    try:
        # 1. Update jobs.json (persistent state)
        if JOBS_FILE.exists():
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                jobs_data = json.load(f)

            if job in jobs_data and isinstance(jobs_data[job], dict):
                jobs_data[job]["enabled"] = enabled
            else:
                jobs_data[job] = {"enabled": enabled}

            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(jobs_data, f, indent=4)

        # 2. Notify Trinity for immediate start/stop (if running)
        trinity_result = None
        if trinity_manager.is_running():
            try:
                # SOTA 2026: Reuse shared client
                if HTTP_CLIENT:
                    resp = await HTTP_CLIENT.post(
                        f"http://{TRINITY_HOST}:{TRINITY_PORT}/api/jobs/toggle",
                        params={"job": job, "enabled": enabled},
                        headers={"X-Token": ANGEL_API_KEY},
                    )
                else:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            f"http://{TRINITY_HOST}:{TRINITY_PORT}/api/jobs/toggle",
                            params={"job": job, "enabled": enabled},
                            headers={"X-Token": ANGEL_API_KEY},
                            timeout=30.0,
                        )

                if resp.status_code == 200:
                    trinity_result = resp.json()
                    log_event(
                        "INFO",
                        "⚡ Job toggled",
                        "angel",
                        module="ANGEL",
                        job=job,
                        enabled=enabled,
                    )
                else:
                    # SOTA 2026: Rollback on Runtime Failure (Integrity)
                    log_event(
                        "ERROR",
                        f"⚠️ Toggle rejected by Trinity ({resp.status_code}). Rolling back.",
                        "angel",
                        module="ANGEL",
                        job=job,
                    )
                    # Revert config
                    if JOBS_FILE.exists():
                        with open(JOBS_FILE, "r", encoding="utf-8") as f:
                            jobs_data = json.load(f)
                        if job in jobs_data and isinstance(jobs_data[job], dict):
                            jobs_data[job]["enabled"] = not enabled  # Invert back
                            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                                json.dump(jobs_data, f, indent=4)

                    raise HTTPException(
                        status_code=502, detail=f"Runtime refused toggle: {resp.text}"
                    )

            except Exception as e:
                # SOTA 2026: Rollback on Connection Failure
                log_event(
                    "ERROR",
                    "⚠️ Toggle deferred (Trinity unreachable). Rolling back.",
                    "angel",
                    module="ANGEL",
                    job=job,
                    error=str(e),
                )
                # Revert config
                if JOBS_FILE.exists():
                    with open(JOBS_FILE, "r", encoding="utf-8") as f:
                        jobs_data = json.load(f)
                    if job in jobs_data and isinstance(jobs_data[job], dict):
                        jobs_data[job]["enabled"] = not enabled  # Invert back
                        with open(JOBS_FILE, "w", encoding="utf-8") as f:
                            json.dump(jobs_data, f, indent=4)

                raise HTTPException(
                    status_code=502, detail=f"Trinity unreachable: {str(e)}"
                )

        log_event(
            "INFO",
            "✅ Job updated",
            "angel",
            module="ANGEL",
            job=job,
            enabled=enabled,
        )
        return {
            "status": "ok",
            "job": job,
            "enabled": enabled,
            "trinity_response": trinity_result,
        }
    except Exception as e:
        log_event(
            "ERROR",
            "🔴 Toggle failed",
            "angel",
            module="ANGEL",
            job=job,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "error"}


# ══════════════════════════════════════════════════════════════════════════════
# TRIGGERS API (Proactive Mode - SOTA 2026)
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/api/triggers", dependencies=[Depends(verify_api_key)])
async def get_triggers():
    """Get all proactive triggers with their status."""
    try:
        from corpus.brain.triggers import trigger_engine

        triggers = trigger_engine.get_status()
        return {"status": "ok", "triggers": triggers}
    except ImportError:
        return {"status": "error", "error": "Triggers module not available"}
    except Exception as e:
        log_event("ERROR", f"Failed to get triggers: {e}", "angel", module="API")
        return {"status": "error", "error": str(e)}


@app.post("/api/triggers/toggle", dependencies=[Depends(verify_api_key)])
async def toggle_trigger(name: str, enabled: bool):
    """Toggle a specific trigger on/off."""
    try:
        from corpus.brain.triggers import trigger_engine

        for trigger in trigger_engine.triggers:
            if trigger.name == name:
                trigger.enabled = enabled
                trigger_engine._save_state()
                log_event(
                    "INFO",
                    f"🎯 Trigger toggled: {name} = {enabled}",
                    "angel",
                    module="TRIGGERS",
                )
                return {"status": "ok", "name": name, "enabled": enabled}

        return {"status": "error", "error": f"Trigger '{name}' not found"}
    except ImportError:
        return {"status": "error", "error": "Triggers module not available"}
    except Exception as e:
        log_event("ERROR", f"Failed to toggle trigger: {e}", "angel", module="API")
        return {"status": "error", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# TRINITY CORE CONFIG API (SOTA 2026)
# ══════════════════════════════════════════════════════════════════════════════

TRINITY_CONFIG_PATH = BASE_DIR / "memories" / "trinity" / "config.json"


@app.get("/api/trinity/config", dependencies=[Depends(verify_api_key)])
async def get_trinity_config():
    """Get Trinity Core configuration (notifications, boot, scheduler)."""
    try:
        if TRINITY_CONFIG_PATH.exists():
            config = json.loads(TRINITY_CONFIG_PATH.read_text())
            return {"status": "ok", "config": config}
        return {"status": "error", "error": "Config file not found"}
    except Exception as e:
        log_event("ERROR", f"Failed to get Trinity config: {e}", "angel", module="API")
        return {"status": "error", "error": str(e)}


@app.post("/api/trinity/config", dependencies=[Depends(verify_api_key)])
async def update_trinity_config(request: Request):
    """Update Trinity Core configuration (notifications, boot, scheduler)."""
    try:
        updates = await request.json()

        # Load current config
        if TRINITY_CONFIG_PATH.exists():
            config = json.loads(TRINITY_CONFIG_PATH.read_text())
        else:
            config = {}

        # Merge updates (deep merge for nested sections)
        for section, values in updates.items():
            if section in [
                "notifications",
                "boot",
                "scheduler",
                "axon",
                "avatar",
            ]:
                if section not in config:
                    config[section] = {}
                if isinstance(values, dict):
                    config[section].update(values)
                else:
                    config[section] = values

        # Save
        TRINITY_CONFIG_PATH.write_text(json.dumps(config, indent=2))
        log_event(
            "INFO",
            f"✅ Trinity config updated: {list(updates.keys())}",
            "angel",
            module="API",
        )

        return {"status": "ok", "config": config}
    except Exception as e:
        log_event(
            "ERROR", f"Failed to update Trinity config: {e}", "angel", module="API"
        )
        return {"status": "error", "error": str(e)}


@app.post("/logs/clear", dependencies=[Depends(verify_api_key)])
async def logs_clear(tab: Optional[str] = None):
    """Truncate log files on disk and broadcast clear to WebSocket clients."""
    files = [ANGEL_LOG, TRINITY_LOG, ALERTS_LOG]
    clear_tab = tab.upper() if tab is not None else "ALL"

    if tab:
        t = tab.upper()
        if t == "ANGEL":
            files = [ANGEL_LOG]
        elif t == "TRINITY":
            files = [TRINITY_LOG]
        elif t == "ALERTS":
            files = [ALERTS_LOG]
        elif t == "TOKENS":
            files = [LOGS_DIR / "tokens.jsonl"]
        elif t == "TRADER":
            files = [LOGS_DIR / "trader.jsonl"]
        elif t == "YOUTUBER":
            files = [LOGS_DIR / "youtuber.jsonl"]
        elif t == "INFLUENCER":
            files = [LOGS_DIR / "influencer.jsonl"]
        elif t == "JULES":
            files = [LOGS_DIR / "jules.jsonl"]
        elif t == "SOCIAL":
            files = [LOGS_DIR / "social.jsonl"]

    count = 0
    for lf in files:
        try:
            with open(lf, "w") as f:
                f.truncate(0)
            count += 1
        except Exception:
            pass

    # SOTA 2026: Broadcast clear to WebSocket clients
    await ws_hub.broadcast_clear(clear_tab)

    return {"status": "cleared", "count": count}


# ══════════════════════════════════════════════════════════════════════════════
# JULES V3 API (User Control)
# ══════════════════════════════════════════════════════════════════════════════

# Jules configuration
MORNING_BRIEF_FILE = BASE_DIR / "memories" / "jules" / "morning_brief.json"


@app.get("/jules/morning-brief", dependencies=[Depends(verify_api_key)])
async def jules_morning_brief():
    """Get the current morning brief with project proposals."""
    if not MORNING_BRIEF_FILE.exists():
        return {
            "status": "empty",
            "candidates": [],
            "message": "No morning brief available",
        }

    try:
        data = json.loads(MORNING_BRIEF_FILE.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        log_event(
            "ERROR", f"Failed to read morning brief: {e}", "angel", module="JULES"
        )
        return {"status": "error", "error": str(e)}


@app.get("/jules/pending", dependencies=[Depends(verify_api_key)])
async def jules_list_pending():
    """List all pending projects awaiting review."""
    from jules.pending_manager import pending_manager

    try:
        projects = pending_manager.list_pending()
        return {"status": "ok", "count": len(projects), "projects": projects}
    except Exception as e:
        log_event("ERROR", f"Failed to list pending: {e}", "angel", module="JULES")
        return {"status": "error", "error": str(e)}


@app.get("/jules/status", dependencies=[Depends(verify_api_key)])
async def jules_status():
    """Get Jules system status (idle/working/done)."""
    from jules.pending_manager import pending_manager

    # Check morning brief for waiting decisions
    has_waiting = False
    waiting_count = 0
    if MORNING_BRIEF_FILE.exists():
        try:
            data = json.loads(MORNING_BRIEF_FILE.read_text(encoding="utf-8"))
            for candidate in data.get("candidates", []):
                if candidate.get("status") == "WAITING_DECISION":
                    has_waiting = True
                    waiting_count += 1
        except Exception:
            pass

    pending_count = pending_manager.count_pending()

    # Determine status
    if has_waiting:
        status = "done"  # Projects ready for decision
    elif pending_count > 0:
        status = "pending"  # Projects in review queue
    else:
        status = "idle"

    return {
        "status": status,
        "waiting_count": waiting_count,
        "pending_count": pending_count,
        "active": True,  # Jules is always available
    }


@app.get("/jules/stats", dependencies=[Depends(verify_api_key)])
async def jules_stats():
    """
    IMPROVEMENT 3: Get Jules decision statistics for UI feedback.
    Returns counts of merged, pending, rejected projects.
    """
    from jules.pending_manager import pending_manager
    from jules.cortex import cortex

    # Get cortex stats (wins/losses/streak)
    cortex_stats = cortex.get_stats()

    # Count pending projects
    pending_list = pending_manager.list_pending()
    pending_count = len(pending_list)

    # Count rejected projects
    rejected_list = pending_manager.list_rejected()
    rejected_count = len(rejected_list)

    # Count merged (from morning brief history if available)
    merged_count = 0
    if MORNING_BRIEF_FILE.exists():
        try:
            data = json.loads(MORNING_BRIEF_FILE.read_text(encoding="utf-8"))
            for candidate in data.get("candidates", []):
                if candidate.get("status") == "MERGED":
                    merged_count += 1
        except Exception:
            pass

    return {
        "merged_count": merged_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "cortex": {
            "wins": cortex_stats.get("wins", 0),
            "losses": cortex_stats.get("losses", 0),
            "streak": cortex_stats.get("streak", 0),
        },
        "pending_projects": [
            {"id": p.get("id"), "title": p.get("project", {}).get("title", p.get("id"))}
            for p in pending_list[:5]  # Limit to 5 for UI
        ],
        "recent_rejected": [
            {"id": r.get("id"), "title": r.get("title"), "reason": r.get("reason")}
            for r in rejected_list[:5]  # Last 5 rejections
        ],
    }


@app.get("/jules/nightwatch", dependencies=[Depends(verify_api_key)])
async def jules_nightwatch_status():
    """
    IMPROVEMENT 4: Get Nightwatch (Guardian Angel) status.

    Nightwatch is the autonomous failsafe system that:
    - Monitors logs every 5s for CRITICAL errors during probation
    - Auto-reverts last commit on crash detection
    - Records failure in Cortex for cooldown
    - Notifies via Phone Widget on blacklist
    """
    from jules.options_manager import is_nightwatch_enabled
    from corpus.dna.genome import ROOT_DIR

    probation_lock = ROOT_DIR / ".probation_lock"
    is_in_probation = probation_lock.exists()

    # Get recent activity from current attempt
    current_attempt_file = ROOT_DIR / "memories/jules/.current_attempt"
    current_task = None
    if current_attempt_file.exists():
        current_task = current_attempt_file.read_text().strip()

    return {
        "enabled": is_nightwatch_enabled(),
        "in_probation": is_in_probation,
        "current_task": current_task,
        "description": (
            "Nightwatch is the Guardian Angel. When a Jules task starts, "
            "it creates a .probation_lock file. Nightwatch monitors logs "
            "every 5 seconds for CRITICAL errors. If detected, it auto-reverts "
            "the last commit and records the failure in Cortex."
        ),
    }


@app.post("/jules/decision", dependencies=[Depends(verify_api_key)])
async def jules_decision(project_id: str, action: str, pr_url: Optional[str] = None):
    """
    Handle user decision for a project.
    action: MERGE | PENDING | REJECT
    """
    from jules.pending_manager import pending_manager
    from jules.cortex import cortex

    valid_actions = ["MERGE", "PENDING", "REJECT"]
    if action.upper() not in valid_actions:
        raise HTTPException(
            status_code=400, detail=f"Invalid action. Use: {valid_actions}"
        )

    action = action.upper()
    log_event(
        "INFO", f"📋 Jules decision: {action} for {project_id}", "angel", module="JULES"
    )

    try:
        # Get project data from morning brief
        project_data = None
        if MORNING_BRIEF_FILE.exists():
            brief = json.loads(MORNING_BRIEF_FILE.read_text(encoding="utf-8"))
            for candidate in brief.get("candidates", []):
                if candidate.get("id") == project_id:
                    project_data = candidate
                    break

        if action == "MERGE":
            # Trigger actual merge via GitHub
            if pr_url:
                # Forward to Trinity for actual merge
                if trinity_manager.is_running() and HTTP_CLIENT:
                    try:
                        resp = await HTTP_CLIENT.post(
                            f"http://{TRINITY_HOST}:{TRINITY_PORT}/api/jules/merge",
                            params={"pr_url": pr_url},
                            headers={"X-Token": ANGEL_API_KEY},
                            timeout=30.0,
                        )
                        result = (
                            resp.json()
                            if resp.status_code == 200
                            else {"error": "Merge failed"}
                        )
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"warning": "Trinity not running, merge queued"}
            else:
                result = {"warning": "No PR URL provided"}

            # Update morning brief status
            _update_brief_status(project_id, "MERGED")

            log_event(
                "SUCCESS", f"✅ Project merged: {project_id}", "angel", module="JULES"
            )
            return {"status": "merged", "project_id": project_id, "result": result}

        elif action == "PENDING":
            # Move to pending folder for later review
            folder = pending_manager.move_to_pending(
                project_id=project_id,
                project_data=project_data or {"id": project_id},
                pr_url=pr_url,
            )
            _update_brief_status(project_id, "PENDING")

            log_event(
                "INFO",
                f"⏳ Project moved to pending: {project_id}",
                "angel",
                module="JULES",
            )
            return {
                "status": "pending",
                "project_id": project_id,
                "folder": str(folder),
            }

        elif action == "REJECT":
            # Archive rejection for future reference (prevents re-proposal)
            folder = pending_manager.move_to_rejected(
                project_id=project_id,
                project_data=project_data or {"id": project_id},
                reason="User explicitly rejected",
                pr_url=pr_url,
            )

            # Also record in cortex memory (belt and suspenders)
            signature = f"JULES:{project_id}"
            cortex.record_outcome(
                signature, "REJECTED_BY_USER", "User explicitly rejected"
            )

            # Close PR if URL provided
            if pr_url and trinity_manager.is_running() and HTTP_CLIENT:
                try:
                    await HTTP_CLIENT.post(
                        f"http://{TRINITY_HOST}:{TRINITY_PORT}/api/jules/close-pr",
                        params={"pr_url": pr_url},
                        headers={"X-Token": ANGEL_API_KEY},
                        timeout=15.0,
                    )
                except Exception:
                    pass

            _update_brief_status(project_id, "REJECTED")

            log_event(
                "WARNING", f"❌ Project rejected: {project_id}", "angel", module="JULES"
            )
            return {
                "status": "rejected",
                "project_id": project_id,
                "folder": str(folder),
            }

    except Exception as e:
        log_event("ERROR", f"Decision failed: {e}", "angel", module="JULES")
        raise HTTPException(status_code=500, detail=str(e))


def _update_brief_status(project_id: str, status: str):
    """Update project status in morning brief file."""
    try:
        if not MORNING_BRIEF_FILE.exists():
            return
        brief = json.loads(MORNING_BRIEF_FILE.read_text(encoding="utf-8"))
        for candidate in brief.get("candidates", []):
            if candidate.get("id") == project_id:
                candidate["status"] = status
                break
        MORNING_BRIEF_FILE.write_text(json.dumps(brief, indent=2, ensure_ascii=False))
    except Exception:
        pass


@app.get("/jules/options", dependencies=[Depends(verify_api_key)])
async def get_jules_options():
    """Get Jules configuration options."""
    from jules.options_manager import get_options

    return get_options()


@app.post("/jules/options", dependencies=[Depends(verify_api_key)])
async def set_jules_options(
    active: Optional[bool] = None,
    self_review: Optional[bool] = None,
    self_evolution: Optional[bool] = None,
    nightwatch: Optional[bool] = None,
    sandbox_mode: Optional[bool] = None,
):
    """Update Jules configuration options."""
    from jules.options_manager import set_options, get_options

    # Build update dict from provided values
    updates = {}
    if active is not None:
        updates["active"] = active
    if self_review is not None:
        updates["self_review"] = self_review
    if self_evolution is not None:
        updates["self_evolution"] = self_evolution
    if nightwatch is not None:
        updates["nightwatch"] = nightwatch
    if sandbox_mode is not None:
        updates["sandbox_mode"] = sandbox_mode

    if updates:
        success = set_options(updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save options")
        log_event("INFO", f"Jules options updated: {updates}", "angel", module="JULES")

    return get_options()


# SOTA 2026: Staged Projects API (for 8810 extension)
STAGING_DIR = BASE_DIR / "memories" / "jules" / "staging"


@app.get("/jules/staged-projects", dependencies=[Depends(verify_api_key)])
async def jules_staged_projects():
    """
    Get all staged projects ready for human review.
    These are projects that Jules has executed and pushed as PRs.
    """
    projects = []

    if not STAGING_DIR.exists():
        return {"status": "ok", "count": 0, "projects": []}

    try:
        for session_dir in STAGING_DIR.iterdir():
            if not session_dir.is_dir():
                continue

            session_id = session_dir.name
            # SOTA 2026: Use metadata.json (actual filename used by forge)
            manifest_file = session_dir / "metadata.json"

            if manifest_file.exists():
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                projects.append(
                    {
                        "id": session_id,
                        "title": manifest.get("title", f"Project {session_id}"),
                        "status": "STAGED",
                        "staged_at": manifest.get("staged_at", ""),
                        "session_id": session_id,
                        "pr_url": manifest.get("pr_url"),
                        "pr_number": manifest.get("pr_number"),
                        "files_count": manifest.get("files_count", 0),
                        "additions": manifest.get("additions", 0),
                        "deletions": manifest.get("deletions", 0),
                        "files": manifest.get("files", []),
                    }
                )
            else:
                # Fallback: directory exists but no manifest
                projects.append(
                    {
                        "id": session_id,
                        "title": f"Project {session_id}",
                        "status": "STAGED",
                        "staged_at": "",
                        "session_id": session_id,
                        "files_count": 0,
                        "additions": 0,
                        "deletions": 0,
                        "files": [],
                    }
                )

        return {"status": "ok", "count": len(projects), "projects": projects}
    except Exception as e:
        log_event(
            "ERROR", f"Failed to list staged projects: {e}", "angel", module="JULES"
        )
        return {"status": "error", "error": str(e), "projects": []}


@app.get("/jules/project/{project_id}/diff", dependencies=[Depends(verify_api_key)])
async def jules_project_diff(project_id: str):
    """
    Get the diff for a specific staged project.
    """
    project_dir = STAGING_DIR / project_id
    diff_file = project_dir / "changes.diff"

    if not diff_file.exists():
        return {"status": "error", "error": "Diff not found", "diff": None}

    try:
        diff_content = diff_file.read_text(encoding="utf-8")
        return {"status": "ok", "diff": diff_content}
    except Exception as e:
        log_event("ERROR", f"Failed to read project diff: {e}", "angel", module="JULES")
        return {"status": "error", "error": str(e), "diff": None}


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION SYSTEM (Standard 362)
# ══════════════════════════════════════════════════════════════════════════════

NOTIFICATIONS_FILE = BASE_DIR / "memories" / "notifications.json"


def _load_notifications() -> list:
    """Load notifications from disk."""
    if not NOTIFICATIONS_FILE.exists():
        return []
    try:
        data = json.loads(NOTIFICATIONS_FILE.read_text(encoding="utf-8"))
        return data.get("notifications", [])
    except Exception:
        return []


def _save_notifications(notifications: list):
    """Save notifications to disk."""
    try:
        NOTIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "notifications": notifications,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        NOTIFICATIONS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        log_event(
            "ERROR", f"Failed to save notifications: {e}", "social", module="NOTIF"
        )


@app.get("/notifications")
async def get_notifications():
    """Get all notifications."""
    notifications = _load_notifications()
    unread_count = sum(1 for n in notifications if not n.get("read", False))
    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }


@app.post(
    "/notifications/read/{notification_id}", dependencies=[Depends(verify_api_key)]
)
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    notifications = _load_notifications()
    for n in notifications:
        if n.get("id") == notification_id:
            n["read"] = True
            break
    _save_notifications(notifications)
    return {"status": "ok", "id": notification_id}


@app.post("/notifications/action", dependencies=[Depends(verify_api_key)])
async def execute_notification_action(notification_id: str, action_id: str):
    """Execute an action on a notification (button click)."""
    notifications = _load_notifications()

    # Find and remove the notification
    target = None
    for n in notifications:
        if n.get("id") == notification_id:
            target = n
            break

    if not target:
        return {"status": "error", "error": "Notification not found"}

    # Log the action
    log_event(
        "INFO",
        f"📱 Notification action: {action_id}",
        "social",
        module="NOTIF",
        notification_id=notification_id,
        action=action_id,
    )

    # Remove from list after action
    notifications = [n for n in notifications if n.get("id") != notification_id]
    _save_notifications(notifications)

    return {"status": "ok", "action": action_id, "notification_id": notification_id}


@app.post(
    "/notifications/dismiss/{notification_id}", dependencies=[Depends(verify_api_key)]
)
async def dismiss_notification(notification_id: str):
    """Dismiss (delete) a notification."""
    notifications = _load_notifications()
    notifications = [n for n in notifications if n.get("id") != notification_id]
    _save_notifications(notifications)
    return {"status": "ok", "id": notification_id}


async def _dispatch_notification(
    source: str,
    message: str,
    title: Optional[str] = None,
    body: Optional[str] = None,
    actions: Optional[List[Dict]] = None,
    priority: str = "INFO",
    dedup_key: Optional[str] = None,
) -> dict:
    """Core dispatch logic: Persist -> WebSocket -> FCM.

    Args:
        dedup_key: Optional deduplication key. If provided, any existing notification
                   with the same dedup_key will be REPLACED by the new one.
                   Useful for periodic reports (e.g., "TRADER_REPORT", "SCHEDULER_NOON").
    """

    # 1. Persistence
    notifications = _load_notifications()

    # SOTA 2026: Deduplication - Remove existing notification with same dedup_key
    if dedup_key:
        notifications = [n for n in notifications if n.get("dedup_key") != dedup_key]
        # SOTA 2026: Also remove legacy boot notifications without dedup_key (SCHEDULER_BOOT migration)
        if dedup_key == "SCHEDULER_BOOT":
            notifications = [
                n
                for n in notifications
                if not (
                    n.get("source") == "SCHEDULER"
                    and "TRINITY EN LIGNE" in (n.get("title") or "")
                    and not n.get("dedup_key")
                )
            ]

    new_notif = {
        "id": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        "source": source.upper(),
        "title": title or message[:60],
        "message": message,
        "body": body or message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "actions": actions or [],
        "priority": priority,
    }

    # Store dedup_key if provided (for future replacements)
    if dedup_key:
        new_notif["dedup_key"] = dedup_key

    notifications.insert(0, new_notif)
    notifications = notifications[:50]
    _save_notifications(notifications)

    # 2. WebSocket Broadcast
    if "ws_hub" in globals() and ws_hub:
        await ws_hub.broadcast({"type": "notification", "data": new_notif})

    # 3. FCM Broadcast (SOTA 2026)
    try:
        fcm_tokens = _load_fcm_tokens()
        if fcm_tokens:
            from social.messaging.push_client import send_fcm_notification

            # Fire and forget async task
            asyncio.create_task(
                send_fcm_notification(
                    tokens=[t["token"] for t in fcm_tokens],
                    title=new_notif["title"],
                    body=message[:200],  # Limit body for push
                    data={"source": source, "notification_id": new_notif["id"]},
                )
            )
    except Exception as e:
        log_event("WARN", f"FCM Dispatch Error: {e}", "angel", module="NOTIF")

    return new_notif


@app.post("/notifications/add", dependencies=[Depends(verify_api_key)])
async def add_notification(
    request: Request,
    source: str = "",
    message: str = "",
    body: Optional[str] = None,
    title: Optional[str] = None,
    actions: Optional[str] = None,
    dedup_key: Optional[str] = None,
):
    """Add a new notification (API endpoint).

    Args:
        dedup_key: Optional. If provided, any existing notification with this key
                   will be replaced. Prevents notification spam for periodic reports.
    """
    # Parse params from JSON body if query params missing
    if not source or not message:
        try:
            json_body = await request.json()
            source = source or json_body.get("source", "")
            message = message or json_body.get("message", "")
            body = body or json_body.get("body")
            title = title or json_body.get("title")
            actions_raw = actions or json_body.get("actions")
            dedup_key = dedup_key or json_body.get("dedup_key")
            if actions_raw and not actions:
                actions = actions_raw  # Handle if actions passed as list in JSON
        except Exception:
            pass

    if not source or not message:
        from fastapi.responses import JSONResponse

        return JSONResponse({"error": "source and message required"}, status_code=400)

    # Normalize actions (JSON string or list)
    final_actions = []
    if actions:
        if isinstance(actions, str):
            try:
                final_actions = json.loads(actions)
            except Exception:
                pass
        elif isinstance(actions, list):
            final_actions = actions

    new_notif = await _dispatch_notification(
        source=source,
        message=message,
        title=title,
        body=body,
        actions=final_actions,
        dedup_key=dedup_key,
    )

    log_event(
        "INFO",
        f"📱 {source}: {message[:50]}",
        "social",
        module="NOTIF",
    )

    return {"status": "ok", "notification": new_notif}


# ══════════════════════════════════════════════════════════════════════════════
# PUSH NOTIFICATIONS (Standard 362 - FCM)
# ══════════════════════════════════════════════════════════════════════════════

FCM_TOKENS_FILE = BASE_DIR / "memories" / "fcm_tokens.json"


def _load_fcm_tokens() -> list:
    """Load FCM tokens from disk."""
    if FCM_TOKENS_FILE.exists():
        return json.loads(FCM_TOKENS_FILE.read_text())
    return []


def _save_fcm_tokens(tokens: list):
    """Save FCM tokens to disk."""
    FCM_TOKENS_FILE.write_text(json.dumps(tokens, indent=2))


@app.post("/api/push/register", dependencies=[Depends(verify_api_key)])
async def register_push_token(request: Request):
    """Register a device for push notifications (FCM token)."""
    body = await request.json()
    token = body.get("token")
    platform = body.get("platform", "android")

    if not token:
        return JSONResponse({"error": "Missing token"}, status_code=400)

    tokens = _load_fcm_tokens()

    # Check if token already exists
    existing = next((t for t in tokens if t.get("token") == token), None)
    if existing:
        existing["last_seen"] = datetime.now(timezone.utc).isoformat()
    else:
        tokens.append(
            {
                "token": token,
                "platform": platform,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "last_seen": datetime.now(timezone.utc).isoformat(),
            }
        )

    _save_fcm_tokens(tokens)

    log_event("INFO", f"📱 FCM token registered ({platform})", "social", module="PUSH")

    return {"status": "ok", "registered": len(tokens)}


@app.post("/api/push/send", dependencies=[Depends(verify_api_key)])
async def send_push_notification(
    title: str,
    body: str,
    data: Optional[str] = None,  # Optional JSON payload
):
    """Send push notification to all registered devices."""
    tokens = _load_fcm_tokens()

    if not tokens:
        return {"status": "no_devices", "sent": 0}

    # Try to send via FCM
    try:
        from social.messaging.push_client import send_fcm_notification

        results = await send_fcm_notification(
            tokens=[t["token"] for t in tokens],
            title=title,
            body=body,
            data=json.loads(data) if data else None,
        )

        log_event(
            "INFO",
            f"📲 Push sent: {title}",
            "social",
            module="PUSH",
            sent=results.get("success", 0),
        )

        return {
            "status": "ok",
            "sent": results.get("success", 0),
            "failed": results.get("failure", 0),
        }
    except ImportError:
        return {"status": "error", "message": "FCM client not configured"}
    except Exception as e:
        log_event("ERROR", f"Push send failed: {e}", "social", module="PUSH")
        return {"status": "error", "message": str(e)}


@app.get("/api/push/tokens", dependencies=[Depends(verify_api_key)])
async def list_push_tokens():
    """List registered push tokens (admin)."""
    tokens = _load_fcm_tokens()
    return {"tokens": len(tokens), "devices": tokens}


MALICIOUS_PATTERNS = [
    "phpunit",
    "eval-stdin",
    ".php",
    "wp-admin",
    "wp-login",
    "wp-content",
    "shell",
    "backdoor",
    ".env",
    "config.php",
    "admin.php",
    "setup.php",
    "phpmyadmin",
    "mysql",
    "cgi-bin",
    ".git",
    ".svn",
    "terraform",
]


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
)
async def gateway(path: str, request: Request):
    # 0. SECURITY: Block malicious scan requests
    # SOTA 2026: Debug Gateway Routing
    log_event(
        "DEBUG", f"Gateway Hit: {request.method} /{path}", "angel", module="GATEWAY"
    )

    path_lower = path.lower()
    query_lower = str(request.query_params).lower()
    if any(
        pattern in path_lower or pattern in query_lower
        for pattern in MALICIOUS_PATTERNS
    ):
        client_ip = request.client.host if request.client else "unknown"
        log_event(
            "INFO",
            f"🛡️ Blocked: /{path[:60]} from {client_ip}",
            "angel",
            module="ANGEL",
            func="security",
        )
        raise HTTPException(status_code=404, detail="Not Found")

    # SOTA 2026: Route notifications directly (prevent catch-all shadowing)
    if path.startswith("notifications"):
        # Route to notification handlers based on path and method
        if path == "notifications" and request.method == "GET":
            # get_notifications doesn't take request, it takes no args
            return await get_notifications()
        elif path == "notifications/add" and request.method == "POST":
            # add_notification takes (request, source, message, actions)
            # We need to extract params manually if we want to call it directly
            # Or better: let FastAPI handle it via internal dispatch, but here we are in a catch-all.
            # Let's invoke it properly:
            source = request.query_params.get("source") or ""
            message = request.query_params.get("message") or ""
            actions = request.query_params.get("actions")
            return await add_notification(request, source, message, actions)
        elif path.startswith("notifications/read/") and request.method == "POST":
            notif_id = path.split("/")[-1]
            return await mark_notification_read(notif_id)
        elif path.startswith("notifications/dismiss/") and request.method == "POST":
            notif_id = path.split("/")[-1]
            return await dismiss_notification(notif_id)
        elif path == "notifications/action" and request.method == "POST":
            body = await request.json()
            return await execute_notification_action(body.get("id"), body.get("action"))
        else:
            raise HTTPException(status_code=404, detail="Not Found")

    # SOTA 2026: Route push endpoints directly
    if path.startswith("api/push"):
        if path == "api/push/register" and request.method == "POST":
            return await register_push_token(request)
        elif path == "api/push/send" and request.method == "POST":
            title = request.query_params.get("title") or ""
            body = request.query_params.get("body") or ""
            data = request.query_params.get("data")
            return await send_push_notification(title, body, data)
        elif path == "api/push/tokens" and request.method == "GET":
            return await list_push_tokens()
        else:
            raise HTTPException(status_code=404, detail="Not Found")

    # SOTA 2026: Explicit System Routes in Gateway (Safety Fallback)
    # Prevents SPA Fallback (index.html) from swallowing API calls if routing fails
    if path.startswith("sys/") or path.startswith("jobs/") or path.startswith("logs/"):
        # SOTA 2026: Trailing Slash Robustness (Android/Capacitor adds it sometimes)
        clean_path = path.rstrip("/")
        log_event(
            "DEBUG",
            f"Gateway Check: '{path}' -> '{clean_path}'",
            "angel",
            module="GATEWAY",
        )

        if clean_path == "sys/status" and request.method == "GET":
            log_event("DEBUG", "Gateway Matched: sys/status", "angel", module="GATEWAY")
            return await sys_status()
        elif clean_path == "jobs/status" and request.method == "GET":
            return await jobs_status()
        elif clean_path == "sys/start" and request.method == "POST":
            return await sys_start()
        elif clean_path == "sys/stop" and request.method == "POST":
            return await sys_stop()
        elif clean_path == "jobs/toggle" and request.method == "POST":
            job = request.query_params.get("job")
            enabled = request.query_params.get("enabled", "true") == "true"
            return await jobs_toggle(job, enabled)
        elif clean_path == "logs/clear" and request.method == "POST":
            tab = request.query_params.get("tab")
            return await clear_logs(tab)
        elif clean_path == "logs/read" and request.method == "GET":
            log_type = request.query_params.get("log", "trinity")
            lines = int(request.query_params.get("lines", 100))
            since = request.query_params.get("since")
            return await read_logs(log_type, lines, since)

    # SOTA 2026: Direct Settings (Angel Managed)
    # Handle settings here to avoid proxy latency/issues for critical UI
    if path == "api/settings":
        # Use the REAL Trinity config file
        state_file = BASE_DIR / "memories" / "trinity" / "config.json"

        if request.method == "GET":
            if not state_file.exists():
                return JSONResponse({"status": "ONLINE"})
            try:
                content = state_file.read_text(encoding="utf-8")
                return JSONResponse(json.loads(content))
            except Exception:
                return JSONResponse({"status": "ONLINE"})

        if request.method == "POST":
            # Verify Auth (same as other admin endpoints)
            key = request.headers.get("X-Angel-Key")
            if not key or (ANGEL_API_KEY and key != ANGEL_API_KEY):
                return JSONResponse({"error": "Access Denied"}, 403)

            try:
                body = await request.json()
                current = {}
                if state_file.exists():
                    try:
                        current = json.loads(state_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass

                # SOTA 2026: Deep Merge for Config Protection
                # We don't want to wipe out sections if frontend sends partial data
                def deep_update(d, u):
                    for k, v in u.items():
                        if isinstance(v, dict):
                            d[k] = deep_update(d.get(k, {}), v)
                        else:
                            d[k] = v
                    return d

                deep_update(current, body)

                state_file.parent.mkdir(parents=True, exist_ok=True)
                state_file.write_text(json.dumps(current, indent=2), encoding="utf-8")

                # SOTA 2026: Reload Trinity Config Signal
                # Code in Trinity ConfigManager reloads on file change?
                # Currently no watcher. We might need to IPC Trinity to reload.
                # But for now, next read will get it.

                return JSONResponse(current)
            except Exception as e:
                return JSONResponse({"error": str(e)}, 500)

    # 1. API Proxy to Trinity
    if path.startswith("api/") or path.startswith("chat"):
        if trinity_manager.is_running():
            url = f"http://{TRINITY_HOST}:{TRINITY_PORT}/{path}"
            # SOTA 2026: Smart Gateway with Retry (Absorb Startup Latency)
            # Try 6 times (spaced by 500ms = 3s total) to allow Trinity to finish booting
            # Reuse shared client for performance
            # local_client = HTTP_CLIENT

            for attempt in range(6):
                try:
                    # SOTA 2026: FORCE NEW CLIENT (Reliability > Perf)
                    # Convert headers to dict and inject auth for Trinity
                    fwd_headers = dict(request.headers)
                    fwd_headers.pop("host", None)  # Remove Host header
                    # SOTA 2026: Ensure Trinity auth token is present
                    api_key = os.getenv("ANGEL_API_KEY") or os.getenv(
                        "ANGEL_BOOTSTRAP_TOKEN"
                    )
                    if api_key:
                        fwd_headers["X-Angel-Key"] = api_key

                    async with httpx.AsyncClient() as temp_client:
                        proxy = await temp_client.request(
                            request.method,
                            url,
                            headers=fwd_headers,
                            params=request.query_params,
                            content=await request.body(),
                            timeout=60.0,
                        )

                    return Response(proxy.content, proxy.status_code, proxy.headers)
                except httpx.ConnectError:
                    # Trinity process exists but port not open yet (typical boot)
                    if attempt < 5:
                        await asyncio.sleep(0.5)
                        continue

                    # Final attempt failed
                    log_event(
                        "INFO",
                        f"⏳ Trinity still booting... ({url})",
                        "angel",
                        module="ANGEL",
                        func="gateway",
                    )
                    return JSONResponse({"error": "Trinity Booting"}, 502)
                except Exception as e:
                    # Other network errors (Timeout, Protocol, etc)
                    log_event(
                        "WARNING",
                        f"💥 Proxy Fail: {url}",
                        "angel",
                        module="ANGEL",
                        func="gateway",
                        error=repr(e),
                    )
                    return JSONResponse({"error": "Trinity Unreachable"}, 502)
        else:
            return JSONResponse({"error": "Trinity Sleeping"}, 503)

    # 1.5. Changelog Endpoint
    if path == "api/changelog":
        changelog_path = BASE_DIR / "CHANGELOG.md"
        if changelog_path.exists():
            content = changelog_path.read_text(encoding="utf-8")
            return JSONResponse({"content": content})
        return JSONResponse({"error": "Changelog not found"}, 404)

    # 2. Static Files (Web UI)
    web_dir = (BASE_DIR / "social" / "web" / "dist").resolve()

    # SOTA 2026 Security: Strict Path Resolution (Prevent LFI)
    try:
        # Strip leading slash to prevent pathlib from treating it as absolute
        clean_path = path.lstrip("/")
        requested_path = (web_dir / clean_path).resolve()
    except Exception:
        raise HTTPException(status_code=403, detail="Access Denied")

    if not str(requested_path).startswith(str(web_dir)):
        # Attack detected (e.g. /../../trinity.py)
        log_event(
            "CRITICAL",
            f"🛡️ LFI Attempt: {path}",
            "angel",
            module="ANGEL",
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=403, detail="Access Denied")

    if requested_path.exists() and requested_path.is_file():
        # SOTA 2026: Network Efficiency - Cache Control
        headers = {}
        str_path = str(requested_path)

        # 1. Hashed Assets (Vite generated) -> Immutable (1 Year)
        if "/assets/" in str_path:
            headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # 2. Media Assets (Images/Videos) -> 1 Year Cache + Immutable (SOTA 2026)
        elif any(
            x in str_path for x in [".webp", ".webm", ".png", ".svg", ".jpg", ".woff2"]
        ):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # 3. Everything else -> No Cache (Safety)
        else:
            headers["Cache-Control"] = "no-cache"

        return FileResponse(requested_path, headers=headers)

    # Root / SPA Fallback -> No Cache (Always revalidate index.html)
    return FileResponse(
        web_dir / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


if __name__ == "__main__":
    # SOTA 2026: Bind localhost only, disable access logs (errors only)
    host = os.getenv("ANGEL_HOST", "127.0.0.1")
    uvicorn.run(
        "angel:app",
        host=host,
        port=ANGEL_PORT,
        reload=False,
        access_log=False,
        log_level="error",
    )
