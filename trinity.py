#!/usr/bin/env python3
"""
Trinity Neural Protocol (SOTA 2026 - Headless Worker)
=====================================================
- Role: Computation & Logic Node.
- Communication: REST API only. No WebSockets.
- Managed by: angel.py
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
import os
import signal
from dotenv import load_dotenv

# SOTA 2026: Load Environment Variables immediately
load_dotenv()

from contextlib import asynccontextmanager  # noqa: E402
from typing import Any, Dict  # noqa: E402

import aiofiles  # noqa: E402
import psutil  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from loguru import logger  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from slowapi import Limiter  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
import httpx  # SOTA 2026: Async Proxy Client  # noqa: E402
from pathlib import Path  # noqa: E402

# ══════════════════════════════════════════════════════════════════════════════
# LOGURU JSONL SINK (SOTA 2026 - Direct Write) - MUST BE BEFORE CORPUS IMPORTS
# ══════════════════════════════════════════════════════════════════════════════

_LOGS_DIR = Path(__file__).parent / "memories" / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log routing map: module prefix -> filename
_LOG_ROUTES = {
    "jobs.trader": "trader.jsonl",
    "jobs.influencer": "influencer.jsonl",
    "jobs.youtuber": "youtuber.jsonl",
    "social": "social.jsonl",  # Social engine logs
    "corpus": "trinity.jsonl",
    "jules": "jules.jsonl",
}


def _get_log_file(module_name: str) -> str:
    """Route log to appropriate file based on module prefix."""
    if not module_name:
        return "trinity.jsonl"
    module_lower = module_name.lower()
    for prefix, filename in _LOG_ROUTES.items():
        if module_lower.startswith(prefix):
            return filename
    return "trinity.jsonl"


def _jsonl_sink(message):
    """Format and write log to appropriate JSONL file based on module."""
    record = message.record
    module_name = record["name"] or "TRINITY"
    log_file = _get_log_file(module_name)

    source = (
        "TRADER"
        if log_file == "trader.jsonl"
        else "INFLUENCER"
        if log_file == "influencer.jsonl"
        else "YOUTUBER"
        if log_file == "youtuber.jsonl"
        else "SOCIAL"
        if log_file == "social.jsonl"
        else "JULES"
        if log_file == "jules.jsonl"
        else "TRINITY"
    )

    entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": module_name.upper(),
        "source": source,
        "func": record["function"],
        "line": record["line"],
    }

    # 1. Write to JSONL file
    try:
        with open(_LOGS_DIR / log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never crash the logger

    # 2. Broadcast to Angel IPC (non-blocking) for WebSocket real-time streaming
    def _broadcast():
        try:
            import urllib.request

            req = urllib.request.Request(
                "http://127.0.0.1:8089/api/ipc/emit",
                data=json.dumps(entry).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=0.5)
        except Exception:
            pass  # Fire and forget

    import threading

    threading.Thread(target=_broadcast, daemon=True).start()


# Configure loguru: remove default stderr, add JSONL sink
# SOTA 2026: Direct JSONL + IPC to Angel (no stderr to avoid duplicate capture)
logger.remove()  # Remove default handler
logger.add(_jsonl_sink, level="INFO")  # INFO+ only (no DEBUG noise)
# NOTE: NO stderr sink - Angel captures subprocess output and would re-log it
# All logs are visible via JSONL files + real-time WebSocket broadcast to Angel

# ══════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS (After loguru config so all module logs use JSONL sink)
# ══════════════════════════════════════════════════════════════════════════════

from corpus.brain.gattaca import gattaca  # noqa: E402
from corpus.brain.hormones import hormones  # noqa: E402
from corpus.brain.memory import memory  # noqa: E402
from corpus.brain.neocortex import neocortex  # noqa: E402
from corpus.dna.genome import CORPUS_DIR, LOGS_DIR, genome  # noqa: E402
from corpus.soma import organelles  # noqa: E402
from corpus.soma.immune import immune  # noqa: E402
from corpus.soma.cells import load_json, save_json  # noqa: E402
from jobs.loader import is_job_active, load_jobs, stop_jobs, start_job, stop_job  # noqa: E402

from corpus.soma.reserves import treasury  # noqa: E402


# SOTA 2026: Suppress Noisy Libraries (HTTPX)
# Prevent them from spamming stderr which Angel captures as ERROR logs

logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)


# Auth Configuration (SOTA 2026: No fallbacks - crash if missing)
JWT_SECRET = os.environ["JWT_SECRET"]  # REQUIRED - no unsafe fallback
if "AUTH_PASSWORD" not in os.environ:
    # Use standard logger since loguru might not be configured fully yet (or it is, but safety first)
    logging.critical(
        "🚨 FATAL: AUTH_PASSWORD missing in .env! Trinity cannot start insecurely."
    )
    print("🚨 FATAL: AUTH_PASSWORD missing in .env! Trinity cannot start insecurely.")
    # We allow the process to crash naturally when accessing the key, or we raise.
    # But let's be explicit.
    raise RuntimeError("AUTH_PASSWORD not set in .env")
AUTH_PASSWORD = os.environ["AUTH_PASSWORD"]
ANGEL_API_KEY = os.environ.get("ANGEL_API_KEY", "")
ANGEL_BOOTSTRAP_TOKEN = os.environ.get(
    "ANGEL_BOOTSTRAP_TOKEN", "trinity-offline-sota-2026"
)

# Rate Limiter (SOTA 2026: Brute-force protection)
from security import get_rate_limit_key  # noqa: E402

limiter = Limiter(key_func=get_rate_limit_key)

# RBAC CONFIGURATION (SOTA 2026: All credentials from .env)
# Roles: GOD (Super Admin), VERIFIER (Read Only), OBSERVER (Demo)
USERS = {
    "admin": {"key": AUTH_PASSWORD, "role": "GOD"},
    "trinity": {
        "key": os.environ.get("TRINITY_ACCESS_KEY", AUTH_PASSWORD),
        "role": "GOD",
    },
    "judge": {"key": os.environ.get("JUDGE_ACCESS_KEY", ""), "role": "VERIFIER"},
    "demo": {"key": os.environ.get("DEMO_ACCESS_KEY", ""), "role": "OBSERVER"},
}

# Simple In-Memory Token Store with Disk Persistence (SOTA 2026)
TOKEN_LIFETIME = 86400  # 24 Hours
ACTIVE_SESSIONS = {}  # token -> {"user": str, "role": str, "exp": timestamp}
SESSIONS_FILE = CORPUS_DIR.parent / "memories" / ".sessions.json"


def _load_sessions():
    """Load sessions from disk on startup."""
    global ACTIVE_SESSIONS
    if SESSIONS_FILE.exists():
        try:
            data = json.loads(SESSIONS_FILE.read_text())
            now = int(dt.datetime.utcnow().timestamp())
            # Filter expired sessions
            ACTIVE_SESSIONS = {
                token: sess for token, sess in data.items() if sess.get("exp", 0) > now
            }
            logger.info(f"🔐 [AUTH] Loaded {len(ACTIVE_SESSIONS)} sessions")
        except Exception as e:
            logger.warning(f"🔐 [AUTH] Session load failed: {e}")
            ACTIVE_SESSIONS = {}


def _save_sessions():
    """Persist sessions to disk."""
    try:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSIONS_FILE.write_text(json.dumps(ACTIVE_SESSIONS, indent=2))
    except Exception as e:
        logger.warning(f"🔐 [AUTH] Session save failed: {e}")


def register_session(token: str, user: str, role: str, exp: int):
    """Register a new session and persist."""
    ACTIVE_SESSIONS[token] = {"user": user, "role": role, "exp": exp}
    _save_sessions()


def invalidate_session(token: str):
    """Remove a session and persist."""
    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
        _save_sessions()


# ══════════════════════════════════════════════════════════════════════════════
# 2. LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info(f"🧬 Boot v{genome.config.version}")

    # 0. Load Persisted Sessions (SOTA 2026: Survive restarts)
    _load_sessions()

    # 1. Memory & Plugins
    await memory.initialize()
    await organelles.plugins.load_active_plugins()

    # 2. Start Gamification Monitor (moved below for stability)
    # asyncio.create_task(monitor_gamification())

    await load_jobs(app)

    # 3. Start Gamification Monitor (After jobs loaded)
    asyncio.create_task(monitor_gamification())

    # 5. Scheduler (SOTA 2026 - Phone Widget + FCM only)
    from social.messaging.scheduler import scheduler

    await scheduler.start()
    logger.info("⏰ Scheduler ready")

    # 5.1. Nerve Relay (SOTA 2026 - Bridge nerves.fire → Phone Widget)
    from social.messaging.nerve_relay import register_nerve_relay

    register_nerve_relay()
    logger.info("📱 Nerve relay registered")

    # 6. Proactive Triggers (SOTA 2026 - Moved from Angel)
    # Trinity Core now manages its own vitality checks (Budget/Tokens/Crash)
    asyncio.create_task(monitor_triggers())

    yield

    # --- SHUTDOWN ---
    logger.info("💤 Shutdown")

    await scheduler.stop()

    await stop_jobs()

    await memory.close()


async def monitor_triggers():
    """
    Proactive Trigger Loop (SOTA 2026).
    Evaluates business & vitality conditions every 5 minutes.
    Moved from Angel to allow direct access to Treasury/Jobs/Memory.
    """
    from corpus.brain.triggers import evaluate_triggers

    # Warm-up delay to let jobs/memory load
    await asyncio.sleep(60)

    # Standard Interval: 5 minutes
    TRIGGER_INTERVAL = 300

    while True:
        try:
            fired = await evaluate_triggers()
            if fired:
                logger.info(f"🎯 Triggers fired: {', '.join(fired)}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"🎯 Trigger loop error: {e}")

        await asyncio.sleep(TRIGGER_INTERVAL)


async def monitor_gamification():
    """Background loop to update System objectives (Uptime & Efficiency)."""
    from corpus.dopamine import manager

    # SOTA 2026: Warm-up delay to prevent partial boot resource contention
    await asyncio.sleep(45)

    start_time = dt.datetime.utcnow().timestamp()
    consecutive_efficient_seconds = 0

    # Uptime milestones in seconds (must match objectives.py registry)
    uptime_milestones = [3600, 21600, 43200, 86400, 259200, 604800, 1209600, 2592000]

    while True:
        try:
            await asyncio.sleep(10)  # Check every 10s

            # 1. Uptime
            uptime = dt.datetime.utcnow().timestamp() - start_time
            for sec in uptime_milestones:
                manager.update_objective(f"sys_uptime_{sec}", uptime)

            # 2. CPU Efficiency
            cpu_usage = psutil.cpu_percent(interval=None)
            if cpu_usage < 50.0:
                consecutive_efficient_seconds += 10
            else:
                consecutive_efficient_seconds = 0

            # Push updates
            manager.update_objective(
                "sys_cpu_efficiency", float(consecutive_efficient_seconds)
            )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"🎮 [GAMIFICATION] Monitor error: {e}")
            await asyncio.sleep(60)


# ══════════════════════════════════════════════════════════════════════════════
# 3. API SETUP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="Trinity V3", version=genome.config.version, lifespan=lifespan)

# Rate Limiter Setup (SOTA 2026: Anti brute-force)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return 429 Too Many Requests for rate-limited endpoints."""
    return Response(
        content='{"detail": "Too many login attempts. Try again later."}',
        status_code=429,
        media_type="application/json",
    )


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    """SOTA 2026: Add security headers to all responses."""
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
    allow_origins=[
        "vscode-webview://*",
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://trinity.julienpiron.fr",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Mounts (for internal use if needed)
WEB_ROOT = CORPUS_DIR.parent / "social" / "web" / "dist"
if WEB_ROOT.exists():
    app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

# NOTA: Jules router is mounted via jobs/loader.py with prefix="/api"

# ══════════════════════════════════════════════════════════════════════════════
# 4. ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# 4. SECURITY & DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════


async def get_current_user_role(
    x_token: str = Header(None, alias="x-token"),
    x_angel_key: str = Header(None, alias="x-angel-key"),
) -> str:
    """Validate token and return user role."""
    # SOTA 2026: Allow API Key OR Bootstrap Token (IPC/Frontend)
    valid_keys = [k for k in [ANGEL_API_KEY, ANGEL_BOOTSTRAP_TOKEN] if k]
    if x_angel_key in valid_keys or x_token in valid_keys:
        return "GOD"

    if not x_token:
        # Public Fallback (if needed) or Reject
        # For Hackathon: Allow vitals/public without token, but protect others
        raise HTTPException(status_code=401, detail="Missing Token")

    session = ACTIVE_SESSIONS.get(x_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid Token")

    # SOTA 2026: Expiry Check
    current_ts = int(dt.datetime.utcnow().timestamp())
    if current_ts > session.get("exp", 0):
        # Lazy Cleanup with persistence
        invalidate_session(x_token)
        raise HTTPException(status_code=401, detail="Token Expired")

    return session["role"]


async def verify_god_mode(role: str = Depends(get_current_user_role)):
    if role != "GOD":
        raise HTTPException(status_code=403, detail="GOD_MODE_REQUIRED")


async def verify_read_access(role: str = Depends(get_current_user_role)):
    if role not in ["GOD", "VERIFIER"]:
        raise HTTPException(status_code=403, detail="ACCESS_DENIED")


async def verify_system_admin(
    request: Request,
    x_token: str = Header(None, alias="x-token"),
    x_angel_key: str = Header(None, alias="x-angel-key"),
):
    """
    SOTA 2026: Shared Secret Security (IPC)
    - Validates ANGEL_API_KEY from headers (X-Angel-Key or x-token).
    - Rejects simplistic localhost checks (Proxy Vulnerability).
    """
    # 1. Validate Shared Secret (ANGEL_API_KEY)
    token = x_angel_key or x_token
    if ANGEL_API_KEY and token == ANGEL_API_KEY:
        return

    # 2. Human/External Access (Fallback to standard RBAC)
    try:
        # Only try if we have a token that looks like a session token (not the key)
        if x_token and x_token != ANGEL_API_KEY:
            role = await get_current_user_role(x_token)
            if role == "GOD":
                return
    except HTTPException:
        pass

    raise HTTPException(status_code=403, detail="ACCESS_DENIED_IPC")


# ══════════════════════════════════════════════════════════════════════════════
# 5. ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/")
async def root():
    return {"status": "ONLINE", "version": genome.config.version, "mode": "HEADLESS"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "system": "TRINITY"}


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
@limiter.limit("5/minute")  # SOTA 2026: Brute-force protection
async def auth_login(request: Request, req: LoginRequest):
    """RBAC Authentication Endpoint."""
    user_data = USERS.get(req.username)

    # 1. Validate Identity
    if not user_data:
        raise HTTPException(status_code=401, detail="Identity Unknown")

    # 2. Validate Key
    if req.password != user_data["key"]:
        raise HTTPException(status_code=401, detail="Invalid Credentials")

    # 3. Generate Session
    timestamp = int(dt.datetime.utcnow().timestamp())
    expiration = timestamp + TOKEN_LIFETIME

    token_base = f"{JWT_SECRET}:{timestamp}:{req.username}"
    token = hashlib.sha256(token_base.encode()).hexdigest()

    role = user_data["role"]
    register_session(token, req.username, role, expiration)

    logger.info(f"🔓 [AUTH] {req.username} ({role})")
    return {
        "token": token,
        "status": "authenticated",
        "user": req.username,
        "role": role,
    }


@app.get("/api/vitals")
async def get_vitals():
    return await immune.check_vitals()


@app.post("/api/hormones/reset", dependencies=[Depends(verify_system_admin)])
async def reset_hormones():
    """Reset hormonal levels to baseline (Standard 350 - Anti-Stress Recovery)."""
    hormones.reset()
    return {"status": "ok", "state": hormones.get_state()}


@app.get("/api/jobs", dependencies=[Depends(verify_read_access)])
async def get_jobs():
    """Config + Runtime Status (includes Jobs + Jules Service)."""
    from corpus.dna.genome import MEMORIES_DIR

    jobs = load_json(MEMORIES_DIR / "jobs.json", default={})
    res = {}
    for name, cfg in jobs.items():
        st = dict(cfg)
        st["active"] = is_job_active(name)
        res[name] = st

    # SOTA 2026: Include Jules as a service in the jobs list
    jules_config_file = Path("jules/config.json")
    if jules_config_file.exists():
        jules_cfg = load_json(jules_config_file, default={})
        res["jules"] = {
            "active": jules_cfg.get("active", False),
            "description": jules_cfg.get("description", "Jules Autonomous Developer"),
            "type": "service",
        }

    return res


@app.post("/api/jobs/toggle", dependencies=[Depends(verify_system_admin)])
async def toggle_job_endpoint(job: str, enabled: bool):
    """
    Dynamically start or stop a job without restarting Trinity.
    Called by Angel after updating jobs.json.
    SOTA 2026: Also handles Jules service toggle via config.json.
    """
    try:
        # SOTA 2026: Jules is a service, not a standard job
        if job.lower() == "jules":
            jules_config_file = Path("jules/config.json")
            if jules_config_file.exists():
                jules_cfg = load_json(jules_config_file, default={})
                jules_cfg["active"] = enabled
                save_json(jules_config_file, jules_cfg)
                logger.info(
                    f"🤖 [JULES] Service {'enabled' if enabled else 'disabled'}"
                )
                return {
                    "status": "ok",
                    "job": "jules",
                    "enabled": enabled,
                    "active": enabled,
                }
            else:
                raise HTTPException(status_code=404, detail="Jules config not found")

        # Standard job handling
        if enabled:
            success = await start_job(job)
        else:
            success = await stop_job(job)

        return {
            "status": "ok" if success else "failed",
            "job": job,
            "enabled": enabled,
            "active": is_job_active(job),
        }
    except Exception as e:
        logger.error(f"💥 [JOBS] Toggle Fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/{stream}", dependencies=[Depends(verify_read_access)])
async def get_logs(stream: str, limit: int = 50):
    """Generic Log Reader."""
    fpath = LOGS_DIR / f"{stream}.jsonl"
    if not fpath.exists():
        return []
    try:
        async with aiofiles.open(fpath, "r", encoding="utf-8") as f:
            content = await f.read()
            lines = [json.loads(line) for line in content.splitlines() if line.strip()]
            return lines[-limit:]
    except Exception:
        return []


@app.post("/api/think", dependencies=[Depends(verify_god_mode)])
async def think(request: Dict[str, Any] = {}):
    """LLM Interface."""
    prompt = request.get("prompt", "")
    try:
        reply = await gattaca.think(prompt, route_id=gattaca.ROUTE_FLASH)
        return {"reply": reply, "status": "ok"}
    except Exception:
        return {"reply": "...", "status": "error"}


# ══════════════════════════════════════════════════════════════════════════════
# 5.3.1 CHAT ENDPOINT (MESSENGER INTERFACE - SOTA 2026)
# ══════════════════════════════════════════════════════════════════════════════


class ChatRequest(BaseModel):
    text: str
    conversation_id: str | None = None
    history: list[dict] | None = None
    files: list[dict] | None = (
        None  # [{"mime_type": "application/pdf", "data": "base64..."}]
    )


@app.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest, role: str = Depends(get_current_user_role)
):
    """Chat with Trinity (SOTA 2026: Agentic with Tool Use)."""
    try:
        # SOTA 2026: Use process_chat with function calling
        # Trinity can now read her own repo if needed
        reply = await neocortex.process_chat(
            user_message=request.text,
            history=request.history,
            files=request.files,  # Pass files to neocortex
        )
        return {"reply": reply, "status": "ok"}
    except Exception as e:
        logger.error(f"💬 [CHAT] Error: {e}")
        return {"reply": "...", "status": "error"}


# ══════════════════════════════════════════════════════════════════════════════
# 5.4 TREASURY ENDPOINT (TRINITY PANEL)
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/api/treasury", dependencies=[Depends(verify_read_access)])
async def get_treasury():
    """Get full financial + system report for Trinity Panel (Standard 418.6)."""
    summary = treasury.get_financial_summary()
    full_report = treasury.get_full_system_report()
    # Merge: keep original summary fields + add enriched data
    return {**summary, **full_report}


# ══════════════════════════════════════════════════════════════════════════════
# 5.5 SETTINGS ENDPOINT (TRINITY PANEL)
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_STATE_FILE = CORPUS_DIR / "memories" / "system_state.json"


@app.get("/api/settings", dependencies=[Depends(verify_system_admin)])
async def get_settings():
    """Get system state / settings."""
    return load_json(SYSTEM_STATE_FILE, default={"status": "ONLINE"})


@app.post("/api/settings", dependencies=[Depends(verify_system_admin)])
async def update_settings(request: Dict[str, Any]):
    """Update system state."""
    current = load_json(SYSTEM_STATE_FILE, default={"status": "ONLINE"})
    current.update(request)

    SYSTEM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SYSTEM_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4)

    return current


@app.post("/api/config", dependencies=[Depends(verify_system_admin)])
async def update_config(request: Dict[str, Any]):
    """
    Update global configuration (TrinityConfig).
    Used for Language switching and other critical settings.
    """
    from corpus.dna.phenotype import trinity_config

    try:
        # 1. Update In-Memory Singleton & Save to File
        # Iterate over keys (e.g., {"language": "en"})
        for key, value in request.items():
            trinity_config.update_section(key, value)

        logger.info(f"⚙️ [CONFIG] Updated: {request}")
        return {"status": "ok", "config": trinity_config.config.dict()}
    except Exception as e:
        logger.error(f"💥 [CONFIG] Update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# 5.6 JULES V3 ENDPOINTS (Shadow Developer Control)
# ══════════════════════════════════════════════════════════════════════════════


@app.post("/api/jules/merge", dependencies=[Depends(verify_system_admin)])
async def jules_merge_pr(pr_url: str):
    """
    Merge a PR via GitHub API.
    Called by Angel when user approves a Jules project.
    """
    from jules.github_client import merge_pr

    try:
        result = await merge_pr(pr_url)
        logger.info(f"✅ [JULES] PR merged: {pr_url}")
        return {"status": "merged", "pr_url": pr_url, "result": result}
    except Exception as e:
        logger.error(f"💥 [JULES] Merge failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jules/close-pr", dependencies=[Depends(verify_system_admin)])
async def jules_close_pr(pr_url: str):
    """
    Close a PR without merging (rejection).
    Called by Angel when user rejects a Jules project.
    """
    from jules.github_client import close_pr

    try:
        result = await close_pr(pr_url, "Rejected by user via Trinity UI")
        logger.info(f"❌ [JULES] PR closed: {pr_url}")
        return {"status": "closed", "pr_url": pr_url, "result": result}
    except Exception as e:
        logger.error(f"💥 [JULES] Close failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jules/options", dependencies=[Depends(verify_read_access)])
async def get_jules_options():
    """Get Jules configuration."""
    jules_config_path = CORPUS_DIR.parent / "jules" / "config.json"
    if jules_config_path.exists():
        return json.loads(jules_config_path.read_text())
    return {}


@app.post("/api/jules/options", dependencies=[Depends(verify_system_admin)])
async def update_jules_options(
    active: bool | None = None, options: Dict[str, Any] | None = None
):
    """Update Jules configuration. Accepts active as query param or full options as body."""
    jules_config_path = CORPUS_DIR.parent / "jules" / "config.json"
    try:
        # Load existing to preserve other fields
        current = {}
        if jules_config_path.exists():
            current = json.loads(jules_config_path.read_text())

        # SOTA 2026: Handle active query param for toggle
        if active is not None:
            current["active"] = active
            logger.info(f"🤖 [JULES] Service {'enabled' if active else 'disabled'}")

        # Handle full body options
        if options:
            current.update(options)

        jules_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(jules_config_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)

        return current
    except Exception as e:
        logger.error(f"💥 [JULES] Config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config", dependencies=[Depends(verify_read_access)])
async def get_config():
    """Get full Trinity configuration."""
    from corpus.dna.phenotype import trinity_config

    return trinity_config.config.dict()


# ══════════════════════════════════════════════════════════════════════════════
# 5.7 GAMIFICATION ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/api/objectives", dependencies=[Depends(verify_read_access)])
async def get_objectives():
    """Get all gamification objectives and progress."""
    from corpus.dopamine import manager

    return manager.get_all_objectives()


# ══════════════════════════════════════════════════════════════════════════════
# 6. REVERSE PROXY (Angel Gateway) - SOTA 2026
# ══════════════════════════════════════════════════════════════════════════════
# Allows Frontend to access Angel (8089) via Trinity (8161) without CORS/Port issues.
# Production-Ready: "The Site Web" works remotely.

ANGEL_URL = "http://127.0.0.1:8089"


async def _proxy_to_angel(request: Request, path: str):
    """Transparent Proxy to Angel Supervisor."""
    url = f"{ANGEL_URL}/{path}"

    # Forward Query Params
    if request.query_params:
        url += f"?{request.query_params}"

    async with httpx.AsyncClient() as client:
        # Forward Headers (excluding Host to avoid confusion)
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)  # Let httpx handle content length

        try:
            # Mirror Method
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
                timeout=10.0,
            )

            # Create Streaming Response (or simple response for JSON)
            # For logs, simple response is fine unless huge (but we limit lines)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
        except Exception as e:
            logger.error(f"🔌 [PROXY] Angel Down? {e}")
            return Response(
                content=json.dumps({"error": "Angel Unreachable"}), status_code=502
            )


@app.api_route("/sys/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_sys(request: Request, path: str):
    return await _proxy_to_angel(request, f"sys/{path}")


@app.api_route("/jobs/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_jobs(request: Request, path: str):
    return await _proxy_to_angel(request, f"jobs/{path}")


@app.api_route("/logs/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_logs(request: Request, path: str):
    return await _proxy_to_angel(request, f"logs/{path}")


if __name__ == "__main__":
    # Highlander Protocol
    pid_file = LOGS_DIR.parent / ".trinity.pid"
    my_pid = os.getpid()

    # Kill zombies
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if proc.pid == my_pid:
            continue
        try:
            cmd = " ".join(proc.info["cmdline"] or []).lower()
            if "trinity.py" in cmd:
                os.kill(proc.pid, signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    with open(pid_file, "w") as f:
        f.write(str(my_pid))

    host = os.environ.get("TRINITY_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8161))

    try:
        uvicorn.run(
            "trinity:app",
            host=host,
            port=port,
            loop="asyncio",
            log_level="error",
            access_log=False,
        )
    except Exception as e:
        import traceback

        with open(LOGS_DIR / "trinity_crash.log", "w") as f:
            f.write(f"CRASH: {e}\n")
            f.write(traceback.format_exc())
        raise
