"""
JOBS/YOUTUBER/API.PY
==============================================================================
MODULE: Youtuber API Endpoints (Dynamic Mount)
PURPOSE: Provides REST endpoints for YoutuberPanel UI.
         Mounted dynamically when youtuber job starts.
         Trinity remains functional without this.
==============================================================================
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Request, BackgroundTasks
from loguru import logger

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

from jobs.youtuber.syncer import YouTubeSyncer
from jobs.youtuber.uploader import uploader_en, uploader_fr
from jobs.youtuber.scheduler import scheduler
from jobs.youtuber.constants import BANNERS
from jobs.youtuber.editor import editor
from pathlib import Path

# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/api/youtuber", tags=["youtuber"])

# State directories
DATA_DIR = MEMORIES_DIR / "youtuber"
STATE_FILE = DATA_DIR / "state.json"
QUEUE_FILE = DATA_DIR / "data" / "queue.json"
ANALYTICS_FILE = DATA_DIR / "data" / "analytics.json"


# =============================================================================
# STATE HELPERS
# =============================================================================
def _get_state() -> Dict:
    """Load youtuber state."""
    return load_json(STATE_FILE, default={"status": "UNKNOWN", "topics": []})


def _get_queue() -> Dict:
    """Load scheduler queue."""
    return load_json(QUEUE_FILE, default={"pending": [], "published": []})


def _get_analytics() -> Dict:
    """Load analytics data."""
    return load_json(ANALYTICS_FILE, default={"videos": []})


def _infer_lang(video: Dict) -> str:
    """
    Infer video language from metadata or title.
    Priority: metadata.lang > video.lang > title analysis
    """
    # 1. Check explicit lang in metadata
    lang = video.get("metadata", {}).get("lang")
    if lang:
        return lang

    # 2. Check explicit lang at video level
    lang = video.get("lang")
    if lang:
        return lang

    # 3. Infer from title (French accents and common patterns)
    title = video.get("metadata", {}).get("title") or video.get("title", "")
    french_indicators = [
        "é",
        "è",
        "ê",
        "ë",
        "à",
        "â",
        "ù",
        "û",
        "ô",
        "î",
        "ï",
        "ç",
        "œ",
        "æ",
    ]
    if any(c in title.lower() for c in french_indicators):
        return "fr"

    # Default to EN (safer for global audience)
    return "en"


def _format_time_ago(iso_time: Optional[str]) -> str:
    """Format ISO timestamp as 'Xm ago' etc."""
    if not iso_time:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        delta = datetime.now() - dt.replace(tzinfo=None)
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s ago"
        if seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        if seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        return f"{int(seconds / 86400)}d ago"
    except Exception:
        return "N/A"


# Output directories
PRODUCER_OUTPUT = MEMORIES_DIR / "youtuber" / "output" / "scripts"
PENDING_SCRIPTS_DIR = MEMORIES_DIR / "youtuber" / "output" / "pending_scripts"

# SOTA 2026: Script Generation Scheduler Constants
SCRIPT_GENERATION_CYCLE_HOURS = 24


def _get_scripts_ready() -> list:
    """Scan for generated scripts ready for production."""
    scripts = []
    if PRODUCER_OUTPUT.exists():
        for f in PRODUCER_OUTPUT.glob("*.json"):
            try:
                data = load_json(f)
                # Extract script text - handle list of segment dicts
                script_raw = data.get("script", [])
                if isinstance(script_raw, list):
                    # Each item is a dict with 'text' key
                    script_text = "\n".join(
                        seg.get("text", "") if isinstance(seg, dict) else str(seg)
                        for seg in script_raw
                    )
                else:
                    script_text = str(script_raw)
                script_preview = (
                    script_text[:500] + "..." if len(script_text) > 500 else script_text
                )
                scripts.append(
                    {
                        "filename": f.name,
                        "title": data.get("title", f.stem),
                        "lang": data.get("_meta", {}).get("lang", "unknown"),
                        "script_preview": script_preview,
                    }
                )
            except Exception:
                pass
    # Sort by filename (no timestamp)
    return sorted(scripts, key=lambda x: x.get("filename", ""), reverse=True)


# Pending scripts awaiting human review (SOTA 2026: Script Generation Card)
PENDING_SCRIPTS_DIR = MEMORIES_DIR / "youtuber" / "output" / "pending_scripts"


def _get_pending_script() -> Optional[Dict]:
    """
    Get pending scripts awaiting human approval.
    Returns both FR and EN versions if available for the same topic.
    SOTA 2026: Bilingual workflow with switch support.
    """
    if not PENDING_SCRIPTS_DIR.exists():
        return None

    pending_files = sorted(PENDING_SCRIPTS_DIR.glob("*.json"))
    if not pending_files:
        return None

    # Group scripts by topic (base name without lang suffix)
    scripts_by_topic = {}
    for f in pending_files:
        try:
            data = load_json(f)
            topic = data.get("_meta", {}).get("topic", f.stem)
            lang = data.get("_meta", {}).get("lang", "fr")

            # Extract script preview
            script_raw = data.get("script", [])
            if isinstance(script_raw, list):
                script_text = "\n".join(
                    seg.get("text", "") if isinstance(seg, dict) else str(seg)
                    for seg in script_raw
                )
            else:
                script_text = str(script_raw)
            preview = (
                script_text[:600] + "..." if len(script_text) > 600 else script_text
            )

            script_info = {
                "id": f.stem,
                "filename": f.name,
                "title": data.get("title", f.stem),
                "lang": lang,
                "preview": preview,
                "created_at": data.get("_meta", {}).get("created_at", None),
            }

            if topic not in scripts_by_topic:
                scripts_by_topic[topic] = {"topic": topic, "versions": {}}
            scripts_by_topic[topic]["versions"][lang] = script_info

        except Exception:
            continue

    if not scripts_by_topic:
        return None

    # Return the first topic's scripts (oldest)
    first_topic = list(scripts_by_topic.values())[0]
    versions = first_topic["versions"]

    # Primary version (prefer FR, fallback to EN)
    primary_lang = "fr" if "fr" in versions else list(versions.keys())[0]

    # CRITICAL: Create a new dict to avoid circular reference
    # (primary is a reference to versions[lang], so primary["versions"] = versions would be circular)
    result = dict(versions[primary_lang])  # Shallow copy
    result["versions"] = {
        lang: dict(info)
        for lang, info in versions.items()  # Copies without circular refs
    }
    result["has_both"] = "fr" in versions and "en" in versions

    return result


def _get_script_scheduler_info() -> Dict:
    """
    SOTA 2026: Get script scheduler status for File d'attente countdown.

    Returns:
        {
            "status": "generating" | "pending" | "waiting",
            "next_script_at": ISO timestamp or None,
            "hours_remaining": float or None,
            "has_pending_script": bool,
            "last_script_generation": ISO timestamp or None
        }
    """
    state = _get_state()
    last_gen = state.get("last_script_generation")

    # Check if pending scripts exist (blocks generation)
    has_pending = PENDING_SCRIPTS_DIR.exists() and bool(
        list(PENDING_SCRIPTS_DIR.glob("*.json"))
    )

    if has_pending:
        return {
            "status": "pending",
            "next_script_at": None,
            "hours_remaining": None,
            "has_pending_script": True,
            "last_script_generation": last_gen,
        }

    # Calculate next generation time
    if not last_gen:
        # Never generated -> due immediately
        return {
            "status": "waiting",
            "next_script_at": None,
            "hours_remaining": 0.0,
            "has_pending_script": False,
            "last_script_generation": None,
        }

    try:
        last_dt = datetime.fromisoformat(last_gen)
        next_gen = last_dt + timedelta(hours=SCRIPT_GENERATION_CYCLE_HOURS)
        now = datetime.now()

        if now >= next_gen:
            hours_remaining = 0.0
        else:
            hours_remaining = (next_gen - now).total_seconds() / 3600

        return {
            "status": "waiting",
            "next_script_at": next_gen.isoformat(),
            "hours_remaining": round(hours_remaining, 1),
            "has_pending_script": False,
            "last_script_generation": last_gen,
        }
    except Exception:
        return {
            "status": "waiting",
            "next_script_at": None,
            "hours_remaining": 0.0,
            "has_pending_script": False,
            "last_script_generation": last_gen,
        }


# =============================================================================
# ENDPOINTS
# =============================================================================
@router.get("/status")
async def get_youtuber_status():
    """
    Get youtuber status for UI.
    Reads from state files for instant response.
    """
    try:
        state = _get_state()

        # DEBUG SOTA: Trace Persistence Issue
        logger.debug(
            f"🔍 [API STATUS] Loaded State from {STATE_FILE}: Placard={state.get('placard_enabled')}"
        )

        queue = _get_queue()
        analytics = _get_analytics()

        # Queue stats
        pending = queue.get("pending", [])
        published = queue.get("published", [])

        # Last published video
        last_published = published[-1] if published else None
        last_publish_time = (
            last_published.get("published_at") if last_published else None
        )

        # Get next scheduled
        next_scheduled = pending[0].get("scheduled_for") if pending else None

        # Video count from analytics
        videos = analytics.get("videos", [])
        total_views = sum(v.get("views", 0) for v in videos)
        avg_retention = (
            sum(v.get("retention", 0) for v in videos) / len(videos) if videos else 0
        )

        channel_stats = analytics.get("channel_stats", {})
        total_subs = sum(s.get("subscriber_count", 0) for s in channel_stats.values())

        return {
            "status": state.get("status", "UNKNOWN"),
            "upload_enabled": state.get("upload_enabled", False),
            # Notification toggles
            "notify_uploads": state.get("notify_uploads", True),
            "notify_milestones": state.get("notify_milestones", True),
            "notify_pipeline": state.get("notify_pipeline", True),
            "notify_viral": state.get("notify_viral", True),
            # Video Production Options (SOTA 2026)
            "subtitles_enabled": state.get("subtitles_enabled", True),
            "placard_enabled": state.get("placard_enabled", False),
            "placard_text_fr": state.get("placard_text_fr", ""),
            "placard_text_en": state.get("placard_text_en", ""),
            # Queue stats
            "pending_count": len(pending),
            "published_count": len(published),
            "next_scheduled": next_scheduled,
            "last_published": _format_time_ago(last_publish_time),
            # System Defaults
            "defaults": {
                "placard_text": BANNERS["fr"][1],  # Default for FR UI (Subtitle part)
                "placard_text_en": BANNERS["en"][1],
            },
            # Analytics
            "total_videos": len(videos),
            "total_views": total_views,
            "subscribers": total_subs,  # NEW
            "avg_retention": round(avg_retention, 1),
            # Recent published (last 5)
            # Recent published (last 20 to ensure coverage)
            # Queue is sorted Newest -> Oldest. We want Newest.
            "recent_videos": [
                {
                    "id": v.get("youtube_id", v.get("id")),
                    "title": v.get("metadata", {}).get("title")
                    or v.get("title", "Untitled"),
                    "published_at": v.get("published_at"),
                    "status": v.get("status", "UNKNOWN"),
                    "lang": v.get("lang", "fr"),
                    "views": v.get("stats", {}).get("views", 0),
                    "likes": v.get("stats", {}).get("likes", 0),  # NEW
                    "comments": v.get("stats", {}).get("comments", 0),  # NEW
                    "type": v.get("type", "VIDEO"),  # ⚡ SOTA: Short vs Video
                }
                for v in published[:20]
            ],
            # Pending (next 3)
            "upcoming_videos": [
                {
                    "id": v.get("id"),
                    "title": v.get("metadata", {}).get("title")
                    or v.get("title", "Untitled"),
                    "scheduled_for": v.get("scheduled_for"),
                    "lang": _infer_lang(v),
                    "type": v.get("type", "VIDEO"),
                }
                for v in pending[:3]
            ],
            # Topics in production
            "topics": state.get("topics", []),
            # Scripts Ready (User Request)
            "scripts_ready": _get_scripts_ready(),
            # Pending Script awaiting human approval (SOTA 2026: Script Generation Card)
            "pending_script": _get_pending_script(),
            # SOTA 2026: Script Scheduler Info (File d'attente countdown)
            "script_scheduler": _get_script_scheduler_info(),
            # Alias for Frontend compatibility (SOTA 2026)
            "pending_videos": [
                {
                    "id": v.get("id"),
                    "title": v.get("metadata", {}).get("title")
                    or v.get("title", "Untitled"),
                    "scheduled_for": v.get("scheduled_for"),
                    "lang": _infer_lang(v),
                    "type": v.get("type", "VIDEO"),
                }
                for v in pending
            ],
        }
    except Exception as e:
        logger.error(f"💥 [YOUTUBER API] Status check failed: {e}")
        return {
            "status": "ERROR",
            "pending_count": 0,
            "published_count": 0,
            "recent_videos": [],
            "upcoming_videos": [],
            "pending_videos": [],
            "error": str(e),
        }


@router.post("/config")
async def update_youtuber_config(request: Request):
    """
    Update configuration (Status PAUSED/ACTIVE, Upload Enabled).
    """
    try:
        data = await request.json()
        state = _get_state()

        # Update Status
        if "status" in data:
            state["status"] = data["status"]  # ACTIVE / PAUSED

        # Update Upload Toggle
        if "upload_enabled" in data:
            state["upload_enabled"] = data["upload_enabled"]

        # Update Notification Toggles (SOTA 2026)
        if "notify_uploads" in data:
            state["notify_uploads"] = data["notify_uploads"]
        if "notify_milestones" in data:
            state["notify_milestones"] = data["notify_milestones"]
        if "notify_pipeline" in data:
            state["notify_pipeline"] = data["notify_pipeline"]
        if "notify_viral" in data:
            state["notify_viral"] = data["notify_viral"]

        # Video Production Options (SOTA 2026)
        if "subtitles_enabled" in data:
            state["subtitles_enabled"] = data["subtitles_enabled"]
        if "placard_enabled" in data:
            state["placard_enabled"] = data["placard_enabled"]
        # Update Placard Text (Dual Language + Auto-Regen)
        if "placard_text_fr" in data:
            new_text = data["placard_text_fr"]
            state["placard_text_fr"] = new_text
            # Trigger Visual Update (SOTA 2026: Real-time Asset Gen)
            try:
                editor._generate_banner("fr", custom_text=new_text)
                logger.info(f"🎨 [API] Regenerated FR Banner: {new_text}")
            except Exception as e:
                logger.error(f"❌ [API] Failed to regenerate FR banner: {e}")

        if "placard_text_en" in data:
            new_text = data["placard_text_en"]
            state["placard_text_en"] = new_text
            try:
                editor._generate_banner("en", custom_text=new_text)
                logger.info(f"🎨 [API] Regenerated EN Banner: {new_text}")
            except Exception as e:
                logger.error(f"❌ [API] Failed to regenerate EN banner: {e}")

        save_json(STATE_FILE, state)
        logger.info(f"⚙️ [YOUTUBER API] Config updated: {data}")
        return {"status": "ok", "state": state}
    except Exception as e:
        logger.error(f"❌ [YOUTUBER API] Config update failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/publish")
async def publish_video(request: Request, background_tasks: BackgroundTasks):
    """
    Manual Publish Trigger (Bypasses Auto-Upload check).
    Expects: { "id": "internal_video_id" }
    """
    try:
        data = await request.json()
        video_id = data.get("id")

        if not video_id:
            return {"status": "error", "message": "Missing video ID"}

        # Find in queue
        queue = _get_queue()
        item = next(
            (x for x in queue.get("pending", []) if x.get("id") == video_id), None
        )

        if not item:
            logger.warning(
                f"⚠️ [API] Publish: Video {video_id} not found in pending queue"
            )
            return {"status": "error", "message": "Video not found in queue"}

        # Metadata extraction
        metadata = item.get("metadata", {})
        path = Path(item.get("path", ""))
        lang = metadata.get("lang", "en")  # Default EN

        # Select Uploader
        prod = uploader_fr if lang == "fr" else uploader_en

        # Define Background Task function
        def _bg_publish():
            logger.info(f"🚀 [API] Starting Manual Publish: {metadata.get('title')}")

            # 1. Upload (Force=True)
            vid_id = prod.upload_video(
                path,
                metadata.get("title", "Untitled"),
                metadata.get("description", ""),
                tags=metadata.get("tags", []),
                privacy="public",  # Manual publish is public by default? Or respect metadata?
                # Ideally privacy should be passed or config. For "Pending Upload" manual check -> Public implies "I approve".
                # Metadata usually doesn't have privacy.
                force=True,
            )

            if vid_id:
                # 2. Mark Published
                scheduler.mark_published(video_id, vid_id)
                logger.success(f"✅ [API] Manual Publish Complete: {vid_id}")
            else:
                logger.error("❌ [API] Manual Publish Failed (Upload returned None)")

        # Launch Task
        background_tasks.add_task(_bg_publish)

        return {"status": "ok", "message": "Publishing started in background"}

    except Exception as e:
        logger.error(f"❌ [YOUTUBER API] Publish trigger failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/topic")
async def add_youtuber_topic(request: Request):
    """
    Add a new topic/idea to the queue.
    """
    try:
        data = await request.json()
        topic = data.get("topic")

        if not topic:
            return {"status": "error", "error": "Missing topic"}

        state = _get_state()
        topics = state.get("topics", [])

        if topic not in topics:
            topics.insert(0, topic)  # Add to top (Priority)
            state["topics"] = topics
            save_json(STATE_FILE, state)
            logger.info(f"💡 [YOUTUBER API] Added topic: {topic}")
            return {"status": "ok", "topics": topics}

        return {"status": "ok", "message": "Topic already exists"}
    except Exception as e:
        logger.error(f"💥 [YOUTUBER API] Add topic failed: {e}")
        return {"status": "error", "error": str(e)}


# =============================================================================
# SCRIPT GENERATION ACTIONS (SOTA 2026: Human-in-the-Loop Approval)
# =============================================================================
@router.post("/script/approve")
async def approve_script(request: Request):
    """
    Approve a pending script - moves it to the production scripts folder.
    """
    try:
        data = await request.json()
        script_id = data.get("script_id")

        if not script_id:
            return {"status": "error", "message": "Missing script_id"}

        source_file = PENDING_SCRIPTS_DIR / f"{script_id}.json"
        if not source_file.exists():
            return {"status": "error", "message": "Script not found"}

        # Move to production scripts folder
        dest_file = PRODUCER_OUTPUT / f"{script_id}.json"
        PRODUCER_OUTPUT.mkdir(parents=True, exist_ok=True)
        source_file.rename(dest_file)

        logger.success(f"✅ [SCRIPT] Approved: {script_id}")
        return {"status": "ok", "message": "Script approved and moved to production"}
    except Exception as e:
        logger.error(f"❌ [SCRIPT] Approve failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/script/retry")
async def retry_script(request: Request, background_tasks: BackgroundTasks):
    """
    Reject current script and request AI to regenerate with different approach.
    """
    try:
        data = await request.json()
        script_id = data.get("script_id")

        if not script_id:
            return {"status": "error", "message": "Missing script_id"}

        source_file = PENDING_SCRIPTS_DIR / f"{script_id}.json"
        if not source_file.exists():
            return {"status": "error", "message": "Script not found"}

        # Load script data to get topic for regeneration
        script_data = load_json(source_file)
        topic = script_data.get("_meta", {}).get("topic") or script_data.get(
            "title", "Unknown topic"
        )
        lang = script_data.get("_meta", {}).get("lang", "fr")

        # Delete the rejected script
        source_file.unlink()
        logger.info(f"🔄 [SCRIPT] Retry requested: {script_id} - Topic: {topic}")

        # Re-queue the topic for regeneration (Background)
        def _regen_script():
            import asyncio

            try:
                # Import producer dynamically to avoid circular imports
                from jobs.youtuber.producer import producer

                asyncio.run(producer.generate_script_single(topic=topic, lang=lang))
                logger.success(f"✅ [SCRIPT] Regeneration complete for: {topic}")
            except Exception as e:
                logger.error(f"❌ [SCRIPT] Regeneration failed: {e}")

        background_tasks.add_task(_regen_script)

        return {"status": "ok", "message": "Script rejected, regeneration started"}
    except Exception as e:
        logger.error(f"❌ [SCRIPT] Retry failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/script/reject")
async def reject_script(request: Request):
    """
    Reject and discard a pending script without regeneration.
    """
    try:
        data = await request.json()
        script_id = data.get("script_id")

        if not script_id:
            return {"status": "error", "message": "Missing script_id"}

        source_file = PENDING_SCRIPTS_DIR / f"{script_id}.json"
        if not source_file.exists():
            return {"status": "error", "message": "Script not found"}

        # Delete the rejected script
        source_file.unlink()

        logger.info(f"🗑️ [SCRIPT] Rejected and discarded: {script_id}")
        return {"status": "ok", "message": "Script rejected and discarded"}
    except Exception as e:
        logger.error(f"❌ [SCRIPT] Reject failed: {e}")
        return {"status": "error", "message": str(e)}


def _run_full_sync():
    """
    Execute full sync sequence (EN + FR) in background.
    Handles potential browser-based auth blocks without freezing API.
    """
    try:
        logger.info("🎬 [BG-SYNC] Starting Full Channel Sync...")

        # Sync EN
        syncer_en = YouTubeSyncer(channel="en")
        syncer_en.run_sync()

        # Sync FR
        syncer_fr = YouTubeSyncer(channel="fr")
        syncer_fr.run_sync()

        logger.success("🏁 [BG-SYNC] Sequence Complete")
    except Exception as e:
        logger.error(f"💥 [BG-SYNC] Sequence failed: {e}")


@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """
    Manually trigger YouTube Data Sync (Catalog & Analytics).
    Async Background Task to allow Auth Flow (Browser) without timeout.
    """
    try:
        background_tasks.add_task(_run_full_sync)
        logger.info("⏳ [YOUTUBER API] Sync Scheduled (Background)")
        return {"status": "ok", "message": "Sync started. Check terminal for Auth."}
    except Exception as e:
        logger.error(f"💥 [YOUTUBER API] Schedule failed: {e}")
        return {"status": "error", "error": str(e)}
