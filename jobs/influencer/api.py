"""
JOBS/INFLUENCER/API.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: Influencer API Endpoints (Dynamic Mount)
PURPOSE: Provides REST endpoints for InfluencerPanel UI.
ARCHI: SOTA 2026 (Uses Core Config & Sovereign Modules)
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Union
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger
from pydantic import BaseModel

from corpus.soma.cells import load_json
from corpus.dna.genome import MEMORIES_DIR

# Core Imports
from jobs.influencer.core.config import config_manager
from jobs.influencer.core.approval_queue import approval_queue
from jobs.influencer.core.x_client import x_client
from jobs.influencer.core.rules import SpamFilter, Priorities

# Modules State Access (Direct read for status)
# We read state files directly for performance to avoid waking up modules if not needed
DATA_DIR = MEMORIES_DIR / "influencer"
ORCHESTRATOR_STATE = (
    DATA_DIR / "orchestrator_state.json"
)  # Legacy tracking? No, main.py doesn't write state yet.
MENTIONS_STATE = DATA_DIR / "mentions.json"
GROK_STATE = DATA_DIR / "grok_banter.json"  # Storage uses grok_banter.json
YOUTUBE_STATE = DATA_DIR / "youtube_state.json"


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/api/influencer", tags=["influencer"])


# =============================================================================
# MODELS
# =============================================================================
class InfluencerConfigUpdate(BaseModel):
    # Only expose fields we want UI to edit
    enabled: Optional[bool] = None
    silent_mode: Optional[bool] = None
    approval_mode: Optional[bool] = None
    priority_only: Optional[bool] = None

    enable_grok: Optional[bool] = None
    banter_enabled: Optional[bool] = None  # Alias for enable_grok
    enable_mentions: Optional[bool] = None
    # auto_reply: Optional[bool] = None # Alias for enable_mentions
    # Note: Using aliases in Pydantic is cleaner but explicit mapping in route is safer for now

    enable_youtube: Optional[bool] = None

    notify_mentions: Optional[bool] = None
    notify_replies: Optional[bool] = None
    notify_approvals_trinity: Optional[bool] = None
    notify_approvals_grok: Optional[bool] = None

    max_replies_per_thread: Optional[int] = None
    spam_filter_enabled: Optional[bool] = None
    spam_filter: Optional[bool] = None  # Alias

    trinity_interval_hours: Optional[int] = None  # Divine Frequency
    grok_interval_hours: Optional[int] = None  # Romance Frequency

    # Missing Limits
    max_posts_per_day: Optional[int] = None
    max_replies_per_day: Optional[int] = None
    post_cooldown_minutes: Optional[int] = None
    cooldown_minutes: Optional[int] = None  # Alias
    heartbeat_interval_minutes: Optional[int] = None
    heartbeat_minutes: Optional[int] = None  # Alias

    visuals_enabled: Optional[bool] = None

    # UI Compat
    auto_reply: Optional[bool] = None


class TweetSubmit(BaseModel):
    text: str


# =============================================================================
# STATE HELPERS
# =============================================================================
def _load_json_safe(path: Path, default: Dict) -> Dict:
    try:
        return load_json(path, default=default)
    except Exception as e:
        logger.error(f"Failed to load JSON {path}: {e}")
        return default


def _format_time_ago(iso_time: str) -> str:
    """Format ISO timestamp as 'Xm ago' etc."""
    if not iso_time:
        return "N/A"
    try:
        # Handle simple ISO (naive) or offset
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        # If naive, assume local/UTC? Let's assume passed string is local if no TZ.
        # Ensure we compare apples to apples.
        now = datetime.now()

        # Naive check
        if dt.tzinfo and not now.tzinfo:
            now = now.astimezone()  # Make now aware
        elif not dt.tzinfo and now.tzinfo:
            dt = dt.astimezone()  # Make dt aware (assuming local) or strip now?
            # Easier: strip both
            dt = dt.replace(tzinfo=None)
            now = now.replace(tzinfo=None)
        elif dt.tzinfo is None and now.tzinfo is None:
            pass  # Both naive

        delta = now - dt
        seconds = delta.total_seconds()

        if seconds < 0:
            return "Future"
        if seconds < 60:
            return f"{int(seconds)}s ago"
        if seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        if seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        return f"{int(seconds / 86400)}d ago"
    except Exception:
        return "N/A"


def _safe_timestamp(val: Union[str, float, int, None]) -> float:
    """Safely convert ISO string or number to float timestamp."""
    try:
        if val is None:
            return 0.0
        if isinstance(val, (float, int)):
            return float(val)
        if isinstance(val, str):
            # Handle empty strings
            if not val.strip():
                return 0.0
            return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
        return 0.0
    except Exception as e:
        logger.warning(f"Timestamp conversion failed for {val}: {e}")
        return 0.0


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/status")
async def get_influencer_status():
    """
    Get influencer status for UI.
    """
    try:
        # Load Config
        config = config_manager.load()

        # Load States
        mentions_state = _load_json_safe(MENTIONS_STATE, {})
        grok_state = _load_json_safe(GROK_STATE, {})
        trinity_state = _load_json_safe(
            DATA_DIR / "trinity_state.json", {}
        )  # Trinity State
        youtube_state = _load_json_safe(YOUTUBE_STATE, {})
        queue_state = _load_json_safe(DATA_DIR / "approval_queue.json", {"history": []})

        # Determine Status
        # NOTE: Job is always ACTIVE if loaded (enabled is controlled by jobs.json)
        status = "ACTIVE"
        if config.silent_mode:
            status = "SILENT"

        # Key Metrics
        posts_today = youtube_state.get("posts_today", 0)

        # SOTA 2026: View-Time Correction for Daily Counters
        # If the state file hasn't been touched today (worker lag), force 0.
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        state_date = mentions_state.get("today_date")

        if state_date == current_date_str:
            replies_today = mentions_state.get("replies_today", 0)
        else:
            replies_today = 0

        # Calculate Next Banter (Grok)
        last_banter = grok_state.get("last_banter")
        next_banter_str = "Soon"
        if last_banter:
            try:
                dt_last = datetime.fromisoformat(last_banter)
                next_date = dt_last + timedelta(hours=config.grok_interval_hours)

                # Check Pending
                if approval_queue.has_pending("grok_banter"):
                    next_banter_str = "0h"
                else:
                    delta = next_date - datetime.now()
                    hours = int(delta.total_seconds() / 3600)
                    # If elapsed (<0), show 0h
                    next_banter_str = f"{max(0, hours)}h"
            except Exception:
                next_banter_str = "Unknown"
        else:
            # If never posted, check if pending
            if approval_queue.has_pending("grok_banter"):
                next_banter_str = "0h"
            else:
                next_banter_str = f"{config.grok_interval_hours}h"

        # Calculate Next Trinity Post (Divine Logic)
        last_trinity = trinity_state.get("last_post")
        next_trinity_str = "Soon"
        if last_trinity:
            try:
                dt_last = datetime.fromisoformat(last_trinity)
                next_date = dt_last + timedelta(hours=config.trinity_interval_hours)

                # Check Pending
                if approval_queue.has_pending("trinity_logic"):
                    next_trinity_str = "0h"
                else:
                    delta = next_date - datetime.now()
                    hours = int(delta.total_seconds() / 3600)
                    next_trinity_str = f"{max(0, hours)}h"
            except Exception:
                next_trinity_str = "Unknown"
        else:
            if approval_queue.has_pending("trinity_logic"):
                next_trinity_str = "0h"
            else:
                next_trinity_str = f"{config.trinity_interval_hours}h"

        # Recent Activity (From Approval Queue History - Last 5 items)
        activity_log = []
        raw_history = queue_state.get("history", [])
        # Sort by posted_at desc (if available) or created_at - use _safe_timestamp for type safety
        sorted_history = sorted(
            raw_history,
            key=lambda x: _safe_timestamp(x.get("posted_at") or x.get("created_at")),
            reverse=True,
        )[:50]

        for item in sorted_history:
            # Frontend relies on 'time' being a TIMESTAMP (seconds)
            ts_str = item.get("posted_at") or item.get("created_at")
            ts = _safe_timestamp(ts_str)

            # Determine Type (convert legacy backfill to reply/post)
            t_type = item.get("type")
            if not t_type or t_type == "backfill":
                t_type = (
                    "reply" if item.get("text", "").strip().startswith("@") else "post"
                )

            activity_log.append(
                {
                    "id": item.get("id"),
                    "type": t_type,
                    "text": item.get("text", ""),  # Frontend uses 'text' field (L630)
                    "in_reply_to": item.get("meta", {}).get(
                        "reply_to_user"
                    ),  # Helper for L627
                    "time": ts,  # RAW TIMESTAMP
                    "status": item.get("status", "unknown"),
                }
            )

        # Get Last timestamps - FROM APPROVAL QUEUE (real data, not youtube fake)
        last_posted = None
        for item in sorted_history:
            if item.get("status") == "POSTED":
                last_posted = item
                break  # First POSTED in desc order = most recent

        last_post_ts = (
            _safe_timestamp(last_posted.get("posted_at")) if last_posted else None
        )

        # For mentions, we return formatted string for "Last Mention" display?
        # Frontend L449 just displays status.last_mention.
        # Let's return the string since it's just a label in the UI section
        last_mention_str = _format_time_ago(
            mentions_state.get("last_check")
        )  # Or last actual mention time?
        if not mentions_state.get("last_check"):
            last_mention_str = "N/A"

        # Calculate Last Reply Time from replied_tweets.json
        replied_state = _load_json_safe(
            DATA_DIR / "replied_tweets.json", {"interactions": {}}
        )
        last_reply_ts = 0.0
        replied_tweets = replied_state.get("interactions", {})
        for tweet_id, info in replied_tweets.items():
            if info.get("status") == "replied" and info.get("at"):
                # Use _safe_timestamp to ensure we always compare floats
                ts = _safe_timestamp(info["at"])
                if ts > last_reply_ts:
                    last_reply_ts = ts

        # SOTA 2026: Real Viral Score Calculation (Read from persisted metrics)
        viral_score_file = DATA_DIR / "viral_score.json"

        # Call Profile Followers safely (Async SOTA 2026)
        # SOTA v5.6: Read from cache to avoid API spam (2 calls/day limit)
        followers = 0
        try:
            metrics_cache = _load_json_safe(DATA_DIR / "x_metrics_cache.json", {})
            followers = metrics_cache.get("data", {}).get("followers", 0)
        except Exception:
            pass

        viral_score = 0.0
        if viral_score_file.exists():
            try:
                viral_score = load_json(viral_score_file).get("score", 0.0)
            except Exception:
                pass

        return {
            "status": status,
            # Root Metrics
            "posts_today": posts_today,
            "replies_today": replies_today,
            # Flattened Grok
            "next_banter": next_banter_str,
            "next_trinity": next_trinity_str,  # New Field
            "banter_count": grok_state.get("banter_count", 0),
            # SOTA 2026: Real Viral Score
            "viral_score": viral_score,
            "followers_count": followers,
            # Times
            "last_post_time": last_post_ts,
            "last_reply_time": last_reply_ts,
            "last_mention": last_mention_str,
            "config": config.dict(),
            # Rules & Limits
            "rules": {
                "max_replies_per_day": config.max_replies_per_day,
                "max_posts_per_day": config.max_posts_per_day,
                "heartbeat_minutes": config.heartbeat_interval_minutes,
                "cooldown_minutes": config.post_cooldown_minutes,
                "max_replies_per_thread": config.max_replies_per_thread,
                "spam_filter_enabled": config.spam_filter_enabled,
                "spam_words_count": len(SpamFilter.get_keywords()),
            },
            # Priority accounts
            "priorities": Priorities.get_all(),
            # Spam Keywords (New)
            "spam_keywords": SpamFilter.get_keywords(),
            "recent_activity": activity_log,
            "pending_tweets": [
                {**v, "id": k} for k, v in queue_state.get("pending", {}).items()
            ],
        }
    except Exception as e:
        logger.error(f"💥 Status check failed: {e}")
        return {"status": "ERROR", "error": str(e)}


@router.post("/config")
async def update_influencer_config(update: InfluencerConfigUpdate):
    """Update config via Manager."""
    try:
        # Filter None values
        raw_updates = {k: v for k, v in update.dict().items() if v is not None}

        # MAP ALIASES (UI -> Backend)
        updates = raw_updates.copy()

        # Auto Reply -> Enable Mentions
        if "auto_reply" in updates:
            updates["enable_mentions"] = updates.pop("auto_reply")

        # Banter -> Enable Grok
        if "banter_enabled" in updates:
            updates["enable_grok"] = updates.pop("banter_enabled")

        # Spam Filter
        if "spam_filter" in updates:
            updates["spam_filter_enabled"] = updates.pop("spam_filter")

        # Cooldown
        if "cooldown_minutes" in updates:
            updates["post_cooldown_minutes"] = updates.pop("cooldown_minutes")

        # Heartbeat
        if "heartbeat_minutes" in updates:
            updates["heartbeat_interval_minutes"] = updates.pop("heartbeat_minutes")

        new_config = config_manager.update(updates)
        logger.info(f"📱 Config updated: {updates}")
        return {"status": "ok", "config": new_config.dict()}
    except Exception as e:
        logger.error(f"💥 Config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit")
async def submit_tweet(payload: TweetSubmit):
    """Submit a new tweet to the approval queue."""
    try:
        if not payload.text or len(payload.text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Tweet text is required")

        item_id = approval_queue.add(
            content_type="manual_tweet",
            text=payload.text.strip(),
            meta={"source": "web_ui"},
        )
        logger.info(f"📱 Tweet submitted: {item_id}")
        return {"status": "ok", "id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _process_approved_tweet(item_id: str):
    """
    Background Task: Immediately process/post an approved tweet.
    Ensures SOTA responsiveness without waiting for Main Loop (89m sleep).
    """
    try:
        item = (
            approval_queue.get_next_approved()
        )  # Warning: This gets ANY approved, but likely ours is first.
        # Better: get specific item if approval_queue supports it?
        # approval_queue.get(item_id) returns item, checks status?
        item = approval_queue.get(item_id)

        if not item or item.get("status") != "APPROVED":
            logger.warning(f"⚠️ [API] Process skipped for {item_id}: Not approved/found")
            return

        logger.info(f"🚀 [API] Immediate Processing: {item_id}")

        success = False
        tweet_id = None
        c_type = item.get("type") or item.get("content_type")

        # DISPATCH
        if c_type == "grok_banter":
            from jobs.influencer.modules.grok.core import grok_module

            tweet_id = await grok_module.post_banter(item.get("meta", {}))
            success = tweet_id is not None

        elif c_type == "manual_tweet":
            # Already imported x_client
            tweet_id = await x_client.post_tweet_async(item["text"])
            success = tweet_id is not None

        elif c_type == "trinity_logic":
            from jobs.influencer.modules.trinity.core import trinity_module

            text = item.get("text") or item.get("meta", {}).get("text")
            if text:
                tweet_id = await trinity_module.post_thought(text)
                success = tweet_id is not None

        elif c_type == "mentions_reply":
            meta = item.get("meta", {})
            reply_to_id = meta.get("reply_to_tweet_id")
            if reply_to_id:
                tweet_id = await x_client.post_tweet_async(
                    item["text"], in_reply_to_tweet_id=reply_to_id
                )
                success = tweet_id is not None

        # FINALIZE
        if success:
            logger.success(f"✅ [API] Posted: {item_id} -> {tweet_id}")
            approval_queue.mark_posted(item_id, tweet_id=tweet_id)
        else:
            logger.error(f"❌ [API] Failed to post {item_id}")
            # We can optionally mark it as ERROR or leave APPROVED to retry?
            # Leave APPROVED so loop might retry? Or user can retry.

    except Exception as e:
        logger.error(f"💥 [API] Process task failed: {e}")


@router.post("/approve/{item_id}")
async def approve_tweet(item_id: str, background_tasks: BackgroundTasks):
    """Approve a pending tweet and trigger immediate posting."""
    try:
        item = approval_queue.approve(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        logger.info(f"📱 Tweet approved: {item_id}")

        # SOTA 2026: Immediate Execution
        background_tasks.add_task(_process_approved_tweet, item_id)

        return {"status": "ok", "item": item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/priorities")
async def update_priorities(payload: Dict[str, list]):
    """Update priority accounts list."""
    try:
        priorities = payload.get("priorities", [])
        if not isinstance(priorities, list):
            raise HTTPException(status_code=400, detail="Priorities must be a list")

        Priorities.save(priorities)
        logger.info(f"📋 Priorities updated: {len(priorities)} accounts")
        return {"status": "ok", "count": len(priorities)}
    except Exception as e:
        logger.error(f"Failed to update priorities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spam-words")
async def update_spam_words(keywords: Dict[str, list]):
    """Update spam keyword list."""
    try:
        words = keywords.get("keywords", [])
        if not isinstance(words, list):
            raise HTTPException(status_code=400, detail="Keywords must be a list")

        SpamFilter.save(words)
        logger.info(f"🚫 Spam keywords updated: {len(words)} words")
        return {"status": "ok", "count": len(words)}
    except Exception as e:
        logger.error(f"Failed to update spam words: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject/{item_id}")
async def reject_tweet(item_id: str):
    """Reject a pending tweet."""
    try:
        approval_queue.reject(item_id)
        logger.info(f"📱 Tweet rejected: {item_id}")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate/{item_id}")
async def regenerate_item(item_id: str):
    """
    Regenerate content for a pending item using High-IQ Routes.
    Supports: trinity_logic, grok_banter, mentions_reply.
    """
    try:
        item = approval_queue.get(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        content_type = item.get("type")
        new_text = None

        if content_type == "trinity_logic":
            from jobs.influencer.modules.trinity.core import trinity_module

            # Trinity monologues don't need history in this context
            new_text = await trinity_module.generator.generate_thought([])

        elif content_type == "mentions_reply":
            from jobs.influencer.modules.mentions.worker import mentions_module
            from jobs.influencer.core.rules import Priorities

            meta = item.get("meta", {})
            original_text = meta.get("original_text", "")
            user = meta.get("reply_to_user", "Unknown")

            # Reconstruct minimal tweet dict for generator
            tweet_mock = {"text": original_text, "username": user}
            priority = Priorities.get_priority(user)

            # Access internal generator (exposed via hack or we make it public? It's Python, it's open)
            new_text = await mentions_module._generate_reply(tweet_mock, priority)

        elif content_type == "grok_banter":
            from jobs.influencer.modules.grok.core import grok_module
            # Determine if Opening or Reply
            # Meta might help, or we infer?
            # Creating a unified regenerate method in GrokModule would be cleaner, but let's try direct access

            # If it has 'in_reply_to' in meta?
            # Actually GrokModule.generate_content returns dict with text/image
            # GrokModule.check_and_reply returns nothing (it posts).
            # Wait, Grok logic is complex.
            # If type is grok_banter, likely it's an OPENING (from heartbeat).
            # Replies are usually immediate? NO, approval mode applies to replies too?
            # In `grok/core.py` line 68: `action: proposal, content: content` (from generate_content = Opening).
            # So `grok_banter` in queue currently = Opening.

            generated = await grok_module.generate_content()
            if generated:
                new_text = generated.get("text")
                # Handle Image regeneration? Too complex for now, keep text regen.

        if new_text:
            # Update Queue directly
            # We need a method in ApprovalQueue to update text? Or just modify dict reference?
            # ApprovalQueue.get returns the dict reference from self.queue["pending"]?
            # Yes usually.

            # Verify reference
            item["text"] = new_text
            item["regenerated_at"] = datetime.now().isoformat()
            approval_queue._save()  # Need to save! _save is private.
            # Let's add an update method or call save via hack if needed.
            # Better: approval_queue.update(item_id, text=new_text)

            # Since I can't easily modify ApprovalQueue class right now without tool switch,
            # and I know Python mutablity:
            approval_queue.queue["pending"][item_id]["text"] = new_text
            approval_queue.queue["pending"][item_id]["regenerated_at"] = (
                datetime.now().isoformat()
            )
            approval_queue._save()

            logger.info(f"🔄 Regenerated {item_id} ({content_type})")
            return {"status": "ok", "text": new_text}
        else:
            raise HTTPException(status_code=500, detail="Generation failed")

    except Exception as e:
        logger.error(f"Regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tweet")
async def influencer_tweet(tweet: TweetSubmit):
    """Manual tweet from UI (Immediate)."""
    try:
        # We need to use x_client directly
        result = await x_client.post_tweet_async(tweet.text)
        if result:
            return {"status": "ok", "tweet_id": result}
        else:
            raise HTTPException(status_code=500, detail="Failed to post")
    except Exception as e:
        logger.error(f"Post failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_influencer_logs(lines: int = 50):
    """
    Get recent logs for the UI.
    Reads from memories/logs/influencer.jsonl
    """
    log_path = MEMORIES_DIR / "logs" / "influencer.jsonl"
    if not log_path.exists():
        return {"logs": []}

    try:
        data = []
        # Efficient tail reading (naive implementation for <10MB files is fine)
        # Using encoding='utf-8' is critical
        with open(log_path, "r", encoding="utf-8") as f:
            # Read all lines then slice? Or seek?
            # For 10MB rotation, reading all is acceptable usually, but let's be safe-ish
            all_lines = f.readlines()

        # Parse last N lines
        for line in all_lines[-lines:]:
            try:
                # Loguru JSON format
                # {"text": "...", "record": {"time": {"repr": ...}, "level": {"name": "INFO"}, "message": "..."}}
                # Wait, serialize=True output needs parsing?
                # Actually commonly loguru JSON is: {"text": "2026... INFO ... \n", "record": {...}}
                import json

                entry = json.loads(line)
                record = entry.get("record", {})

                # Format for UI
                # UI likely expects: { time, level, module, function, message }
                ts = record.get("time", {}).get("timestamp", time.time())
                # Convert timestamp to ISO string if needed, or UI handles number?
                # Let's assume UI handles ISO or TS. Loguru provides 'timestamp' as float.

                data.append(
                    {
                        "time": ts,
                        "level": record.get("level", {}).get("name", "UNKNOWN"),
                        "module": record.get("module", "?"),
                        "function": record.get("function", "?"),
                        "message": record.get("message", ""),
                    }
                )
            except Exception:
                continue

        # Return reversed (newest first)
        return {"logs": data[::-1]}

    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {"logs": []}


@router.get("/mentions")
async def get_recent_mentions():
    """Fetch recent mentions from persisted feed."""
    try:
        feed_file = DATA_DIR / "mentions_feed.json"
        if not feed_file.exists():
            return {"mentions": []}
        return load_json(feed_file)
    except Exception as e:
        logger.error(f"Failed to load mentions: {e}")
        return {"mentions": []}


@router.get("/x-metrics")
async def get_x_metrics(background_tasks: BackgroundTasks, force: bool = False):
    """
    Fetch public metrics from X for posted tweets (ASYNC / NON-BLOCKING).
    SOTA 2026: Implements Stale-While-Revalidate pattern.
    - Always returns cached data immediately (instant response).
    - Triggers background refresh if cache is old (>12h) or missing.
    Protects Gateway from Timeouts and preserves Free Tier limits.
    """
    CACHE_FILE = DATA_DIR / "x_metrics_cache.json"

    # 1. Load Cache (Fast Disk Read)
    cache_data = {
        "totals": {},
        "weekly": {},
        "alltime": {},
        "metrics": [],
        "followers": 0,
        "updated": "2000-01-01T00:00:00",
    }

    logger.debug(f"🔍 [API] Checking cache at: {CACHE_FILE}")
    if CACHE_FILE.exists():
        try:
            loaded = load_json(CACHE_FILE)
            if loaded and "data" in loaded:
                cache_data = loaded["data"]
                updated_str = loaded.get("updated", "2000-01-01T00:00:00")
                cache_data["updated"] = updated_str  # Pass generic time to UI if needed
                logger.debug("✅ [API] Cache loaded successfully.")

                # Check 12h expiry (Logic preserved but irrelevant since trigger disabled)
                # last_update = datetime.fromisoformat(updated_str)
            else:
                logger.warning(
                    "⚠️ [API] Cache file loaded but 'data' key missing or empty."
                )
        except Exception as e:
            logger.error(f"💥 [API] Failed to load cache: {e}")
    else:
        logger.warning("⚠️ [API] Cache file NOT FOUND on disk.")

    # 2. Trigger Background Refresh (Smart SOTA: 12h Interval + Backoff)
    # Re-enabled with silenced errors (INFO level) for quota limit handling.
    # Checks 12h interval.
    should_refresh = False
    if force:
        should_refresh = True
        logger.info("🔄 [INFLUENCER] Refresh triggered (Manual Force=True)")
    elif CACHE_FILE.exists():
        try:
            loaded = load_json(CACHE_FILE)
            updated_str = loaded.get("updated", "2000-01-01T00:00:00")
            last_update = datetime.fromisoformat(updated_str)
            if datetime.now() - last_update >= timedelta(hours=12):
                should_refresh = True
                logger.info("🔄 [INFLUENCER] Refresh triggered (Auto 12h)")
        except Exception:
            pass
    else:
        # Cache file missing? Trigger fetch to initialize (silenced if quota exceeded)
        should_refresh = True
        logger.info("🔄 [INFLUENCER] Refresh triggered (Cache Missing)")

    if should_refresh:
        background_tasks.add_task(_refresh_x_metrics_background)

    # 3. Return what we have immediately
    logger.debug(f"📊 [API] Returning metrics: {cache_data.get('totals', 'UNKNOWN')}")
    return cache_data


async def _refresh_x_metrics_background():
    """
    Heavy lifting: Fetch metrics from X API and update cache.
    Runs in background, doesn't block UI.
    """
    import time

    CACHE_FILE = DATA_DIR / "x_metrics_cache.json"

    try:
        # Load Status (Approvals History)
        status_file = DATA_DIR / "approval_queue.json"

        if not status_file.exists():
            return

        status = load_json(status_file)
        history = status.get("history", [])

        # Filter for recent posted tweets (limit 50 to save tokens)
        tweet_ids = [item["tweet_id"] for item in history if item.get("tweet_id")][:50]

        if not tweet_ids:
            return

        logger.info(f"📉 [BG] Fetching metrics for {len(tweet_ids)} tweets...")

        # CALL API (Slow)
        fresh_metrics = await x_client.get_tweets_metrics_async(tweet_ids)

        # Fetch Profile (Slow)
        me = await x_client.get_me_async()
        followers = me.get("followers_count", 0) if me else 0

        # Abort if data is empty (Quota Exceeded or Error)
        if not fresh_metrics:
            # SOTA: Raise exception to trigger Backoff Logic in except block
            # This ensures we update the timestamp and don't retry immediately (Loop Protection)
            raise Exception("Quota Limit or Empty Data returned from X API")

        # ... Processing ...
        metrics_by_id = {m.get("id"): m for m in fresh_metrics}

        # Self-Healing Logic (Backfilled Tweets)
        dirty = False
        for item in history:
            tid = item.get("tweet_id")
            if tid and tid in metrics_by_id:
                real = metrics_by_id[tid]
                # Update text/time if missing
                if "[Backfilled" in item.get("text", "") or not item.get("text"):
                    if real.get("text"):
                        item["text"] = real["text"]
                        dirty = True
                if real.get("created_at"):
                    try:
                        # Normalize time
                        dt = datetime.fromisoformat(
                            real["created_at"].replace("Z", "+00:00")
                        )
                        if abs(item.get("posted_at", 0) - dt.timestamp()) > 60:
                            item["posted_at"] = dt.timestamp()
                            dirty = True
                    except Exception:
                        pass

        if dirty:
            try:
                from corpus.soma.cells import save_json

                save_json(status_file, status)
            except Exception:
                pass

        # Statistics Calculation
        now = time.time()
        week_ago = now - (7 * 24 * 3600)

        weekly_metrics = []
        alltime_metrics = fresh_metrics  # Last 50

        # Determine weekly set
        for item in history:
            if item.get("status") == "POSTED" and item.get("tweet_id"):
                try:
                    if float(item.get("posted_at", 0)) >= week_ago:
                        tid = item["tweet_id"]
                        if tid in metrics_by_id:
                            weekly_metrics.append(metrics_by_id[tid])
                except Exception:
                    pass

        def safe_sum(key, src):
            return sum(int(m.get(key, 0) or 0) for m in src)

        metrics_keys = [
            "impressions",
            "likes",
            "retweets",
            "replies",
            "quotes",
            "bookmarks",
        ]

        weekly_totals = {k: safe_sum(k, weekly_metrics) for k in metrics_keys}
        alltime_totals = {k: safe_sum(k, alltime_metrics) for k in metrics_keys}

        # Viral Score
        total_eng = (
            alltime_totals["likes"]
            + alltime_totals["retweets"]
            + alltime_totals["replies"]
        )
        total_imp = alltime_totals["impressions"]
        viral_score = (total_eng / total_imp * 1000) if total_imp > 0 else 0.0

        # Save Viral Score
        try:
            from corpus.soma.cells import save_json

            save_json(
                DATA_DIR / "viral_score.json",
                {"score": round(viral_score, 1), "updated": datetime.now().isoformat()},
            )
        except Exception:
            pass

        # Final Payload
        result_data = {
            "totals": alltime_totals,  # Legacy compat
            "weekly": weekly_totals,
            "alltime": alltime_totals,
            "metrics": fresh_metrics,
            "followers": followers,
        }

        # Save to Cache
        from corpus.soma.cells import save_json

        save_json(
            CACHE_FILE, {"data": result_data, "updated": datetime.now().isoformat()}
        )

        logger.success(f"📉 [BG] Metrics Refreshed (Viral: {viral_score:.1f})")

        # SOTA 2026: Viral Alert Notification (Standard 362.18)
        # Check for tweets with 100+ likes and notify
        config = config_manager.load()
        if config.notify_viral:
            for m in fresh_metrics:
                likes = int(m.get("likes", 0) or 0)
                if likes >= 100:
                    try:
                        from social.messaging.notification_client import notify

                        # SOTA 2026: Intelligent truncation (Standard 362.102)
                        tweet_text = m.get("text", "")
                        preview = (
                            tweet_text[:100].rsplit(" ", 1)[0]
                            if len(tweet_text) > 100
                            else tweet_text
                        )
                        ellipsis = "..." if len(tweet_text) > 100 else ""
                        await notify.influencer(
                            f"🔥 Tweet Viral!\n{likes} ❤️ sur: {preview}{ellipsis}",
                            dedup_key="INFLUENCER_VIRAL",
                        )
                        break  # One notification per refresh to avoid spam
                    except Exception:
                        pass

    except Exception as e:
        logger.error(f"💥 [BG] Metrics Refresh Failed: {e}")

        # SOTA: COOL DOWN PATTERN (Safe Version)
        # If we failed (Rate Limit or other), update the timestamp ANYWAY to prevent spam.
        # BUT ONLY IF we can preserve existing data. NEVER overwrite with zeros.
        try:
            fallback = None
            if CACHE_FILE.exists():
                # Use _load_json_safe locally or import carefully
                try:
                    fallback = load_json(CACHE_FILE)
                except Exception:
                    fallback = None

            if fallback and "data" in fallback and fallback["data"].get("totals"):
                # Only update if we have valid data
                fallback["updated"] = datetime.now().isoformat()
                from corpus.soma.cells import save_json

                save_json(CACHE_FILE, fallback)
                logger.warning(
                    "🛡️ [BG] Backoff applied: Cache timestamp updated to prevent retry loops."
                )
            else:
                logger.error(
                    "🛑 [BG] Could not load old cache to apply backoff. Skipping save to avoid data loss."
                )

        except Exception as e_inner:
            logger.error(f"💥 [BG] Backoff Logic Failed: {e_inner}")
