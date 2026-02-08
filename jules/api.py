"""
JULES/API.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: JULES API ROUTES (SOTA 2026)
PURPOSE: FastAPI routes for Jules staging system.
         Exposes endpoints for project review and decision.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
import json
from loguru import logger
from pathlib import Path

from jules.staging import staging


# ════════════════════════════════════════════════════════════════════════════
# COUNCIL STATE (Manual Control)
# ════════════════════════════════════════════════════════════════════════════

_council_running = False
_council_started_at: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/jules", tags=["jules"])


# ════════════════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════════════════


class DecisionRequest(BaseModel):
    """Request body for project decision."""

    action: Literal["MERGE", "PENDING", "REJECT"]
    reason: Optional[str] = None


class DecisionResponse(BaseModel):
    """Response for project decision."""

    success: bool
    message: str


# ════════════════════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════════════════════


@router.get("/status")
async def get_jules_status():
    """
    Get Jules status summary.
    Used by the extension to show pending count badge.
    """
    staged = staging.list_staged_projects()
    waiting_count = len([p for p in staged if p.status in ("STAGED", "PENDING")])

    # Check morning brief for council ideas
    morning_brief_file = Path("memories/jules/morning_brief.json")
    council_count = 0
    if morning_brief_file.exists():
        try:
            data = json.loads(morning_brief_file.read_text())
            council_count = len(
                [
                    c
                    for c in data.get("candidates", [])
                    if c.get("status") == "WAITING_DECISION"
                ]
            )
        except Exception:
            pass

    return {
        "status": "done" if waiting_count > 0 or council_count > 0 else "idle",
        "waiting_count": waiting_count,
        "council_count": council_count,
        "staged_projects": waiting_count,
        "total_pending": waiting_count + council_count,
    }


@router.get("/morning-brief")
async def get_morning_brief():
    """
    Get the current morning brief (council ideas).
    These are proposals that haven't been executed yet.
    """
    morning_brief_file = Path("memories/jules/morning_brief.json")

    if not morning_brief_file.exists():
        return {"candidates": [], "date": None}

    try:
        data = json.loads(morning_brief_file.read_text())
        return data
    except Exception as e:
        logger.error(f"💥 [JULES-API] Failed to read morning brief: {e}")
        return {"candidates": [], "date": None, "error": str(e)}


@router.get("/staged-projects")
async def list_staged_projects():
    """
    List all projects in staging awaiting human review.
    These are fully executed projects with PR ready.
    """
    projects = staging.list_staged_projects()
    return {
        "projects": [p.model_dump() for p in projects],
        "count": len(projects),
    }


@router.get("/project/{project_id}")
async def get_project(project_id: str):
    """Get details of a specific staged project."""
    project = staging.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project.model_dump()


@router.get("/project/{project_id}/diff")
async def get_project_diff(project_id: str):
    """Get the diff patch for a project."""
    diff = staging.get_project_diff(project_id)
    if diff is None:
        raise HTTPException(status_code=404, detail="Diff not found")

    return {"diff": diff}


@router.get("/project/{project_id}/files")
async def get_project_files(project_id: str):
    """Get the list of modified files for a project."""
    files = staging.get_project_files(project_id)
    return {"files": files}


@router.post("/project/{project_id}/decision", response_model=DecisionResponse)
async def make_decision(project_id: str, request: DecisionRequest):
    """
    Make a decision on a staged project.

    Actions:
    - MERGE: Approve and merge the PR
    - PENDING: Keep for later review
    - REJECT: Move to rejected folder
    """
    logger.info(f"📮 [JULES-API] Decision: {request.action} for {project_id}")

    if request.action == "MERGE":
        result = await staging.accept_project(project_id)
    elif request.action == "PENDING":
        result = staging.set_pending(project_id)
    elif request.action == "REJECT":
        result = await staging.reject_project(project_id, request.reason)
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    return DecisionResponse(**result)


@router.get("/rejected")
async def list_rejected():
    """List projects that were rejected."""
    from jules.staging import REJECTED_DIR

    projects = []
    if not REJECTED_DIR.exists():
        return {"projects": [], "count": 0}

    for project_dir in REJECTED_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        metadata_file = project_dir / "metadata.json"
        if metadata_file.exists():
            try:
                data = json.loads(metadata_file.read_text())
                projects.append(data)
            except Exception:
                pass

    return {"projects": projects, "count": len(projects)}


@router.get("/stats")
async def get_jules_stats():
    """
    Get Jules project stats (accepted/pending/rejected counts).
    Used by JulesPanel stats card.
    """
    from jules.staging import REJECTED_DIR
    from jules.pending_manager import pending_manager

    # Count staged projects
    staged_count = len(staging.list_staged_projects())

    # Count pending (from pending_manager)
    pending_count = len(pending_manager.list_pending())

    # Count rejected projects
    rejected_count = 0
    if REJECTED_DIR.exists():
        rejected_count = len([d for d in REJECTED_DIR.iterdir() if d.is_dir()])

    # Count accepted (merged) - from history file
    accepted_count = 0
    history_file = Path("memories/jules/merge_history.json")
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
            accepted_count = len(history) if isinstance(history, list) else 0
        except Exception:
            pass

    return {
        "accepted": accepted_count,
        "pending": pending_count + staged_count,
        "rejected": rejected_count,
        "staged": staged_count,
    }


@router.get("/council-stats")
async def get_council_stats():
    """
    Get Nightly Council statistics.
    Used by JulesPanel to show Council performance.
    """
    nightly_file = Path("memories/jules/nightly_execution.json")
    history_file = Path("memories/jules/merge_history.json")

    # Default values
    stats = {
        "last_council_date": None,
        "success_rate": 0,
        "avg_score": 0,
        "total_missions": 0,
        "total_prs_created": 0,
        "target_per_night": 3,
    }

    # Read nightly execution report
    if nightly_file.exists():
        try:
            data = json.loads(nightly_file.read_text())
            stats["last_council_date"] = data.get("date")
            stats["total_missions"] = data.get("total_attempted", 0)

            # Calculate success rate
            achieved = data.get("achieved", 0)
            target = data.get("target", 3)
            if target > 0:
                stats["success_rate"] = round((achieved / target) * 100)

            # Calculate average score from results
            results = data.get("results", [])
            scores = [r.get("score", 0) for r in results if r.get("score")]
            if scores:
                stats["avg_score"] = round(sum(scores) / len(scores))

            # Count PRs created (SUCCESS status)
            stats["total_prs_created"] = len(
                [r for r in results if r.get("status") == "SUCCESS"]
            )
        except Exception as e:
            logger.warning(f"⚠️ [JULES-API] Failed to read nightly execution: {e}")

    # Add merged count from history
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
            if isinstance(history, list):
                stats["total_prs_created"] += len(history)
        except Exception:
            pass

    return stats


@router.get("/history")
async def get_jules_history():
    """
    Get Jules history (merged and rejected projects).
    Used by JulesPanel history section.
    """
    from jules.staging import REJECTED_DIR

    merged = []
    rejected = []

    # Read merge history
    history_file = Path("memories/jules/merge_history.json")
    if history_file.exists():
        try:
            data = json.loads(history_file.read_text())
            if isinstance(data, list):
                merged = data[-5:]  # Last 5
        except Exception:
            pass

    # Read rejected projects
    if REJECTED_DIR.exists():
        for project_dir in list(REJECTED_DIR.iterdir())[-5:]:  # Last 5
            if not project_dir.is_dir():
                continue
            metadata_file = project_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    data = json.loads(metadata_file.read_text())
                    rejected.append(
                        {
                            "title": data.get("title", project_dir.name),
                            "rejected_at": data.get("rejected_at"),
                            "reason": data.get("rejection_reason", "Quality gate"),
                        }
                    )
                except Exception:
                    pass

    return {"merged": merged, "rejected": rejected}


@router.get("/notifications")
async def get_notifications_config():
    """Get Jules notification configuration."""
    config_file = Path("jules/config.json")
    default_notifications = {
        "on_pr_created": True,
        "on_pr_merged": True,
        "on_council_complete": True,
        "on_mission_failed": False,
    }

    if config_file.exists():
        try:
            data = json.loads(config_file.read_text())
            return data.get("notifications", default_notifications)
        except Exception:
            pass

    return default_notifications


@router.post("/notifications")
async def save_notifications_config(notifications: dict):
    """Save Jules notification configuration."""
    config_file = Path("jules/config.json")

    try:
        data = {}
        if config_file.exists():
            data = json.loads(config_file.read_text())

        data["notifications"] = notifications
        config_file.write_text(json.dumps(data, indent=4, ensure_ascii=False))

        return {"success": True, "message": "Notifications saved"}
    except Exception as e:
        logger.error(f"💥 [JULES-API] Failed to save notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# COUNCIL CONTROL (Manual Trigger - SOTA 2026)
# ════════════════════════════════════════════════════════════════════════════


async def _run_council_task():
    """Background task wrapper for council execution."""
    global _council_running, _council_started_at
    try:
        from jules.architect import architect

        await architect.convene_council()
    except Exception as e:
        logger.error(f"💥 [JULES-API] Council execution failed: {e}")
    finally:
        _council_running = False
        _council_started_at = None


@router.post("/council/start")
async def start_council():
    """
    Manually trigger the Nightly Council.
    Returns immediately - council runs in background.
    """
    global _council_running, _council_started_at

    if _council_running:
        raise HTTPException(status_code=409, detail="Council already running")

    _council_running = True
    _council_started_at = datetime.now()

    # Launch in background (fire-and-forget)
    asyncio.create_task(_run_council_task())

    logger.info("🏛️ [JULES-API] Manual Council triggered")
    return {
        "success": True,
        "message": "Council started",
        "started_at": _council_started_at.isoformat(),
    }


@router.get("/council/status")
async def get_council_status():
    """Get current council execution status."""
    return {
        "running": _council_running,
        "started_at": _council_started_at.isoformat() if _council_started_at else None,
    }
