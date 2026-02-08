"""
JULES/STAGING.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: PROJECT STAGING MANAGER
PURPOSE: Manages local storage of Jules project outputs for human review.
         Supports staging (review), acceptance (merge), and rejection.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger
from pydantic import BaseModel


# ════════════════════════════════════════════════════════════════════════════
# PATHS
# ════════════════════════════════════════════════════════════════════════════

JULES_MEMORY_DIR = Path("memories/jules")
STAGING_DIR = JULES_MEMORY_DIR / "staging"
# Use same path as pending_manager for unified rejection storage (SOTA 2026)
REJECTED_DIR = JULES_MEMORY_DIR / "rejected"


# ════════════════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════════════════


class StagedProject(BaseModel):
    """Represents a project staged for human review."""

    id: str
    title: str
    description: Optional[str] = None
    session_id: str
    pr_url: Optional[str] = None
    staged_at: str
    status: str = "STAGED"  # STAGED, PENDING, MERGED, REJECTED
    files_count: int = 0
    additions: int = 0
    deletions: int = 0


# ════════════════════════════════════════════════════════════════════════════
# STAGING MANAGER
# ════════════════════════════════════════════════════════════════════════════


class StagingManager:
    """
    Manages the lifecycle of Jules projects from staging to decision.

    Flow:
    1. stage_project() - Save outputs locally after Forge execution
    2. list_staged_projects() - Show available for review
    3. get_project_diff() - Get the patch content
    4. accept_project() - Merge PR and cleanup
    5. reject_project() - Move to rejected folder
    """

    def __init__(self):
        # Ensure directories exist
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    def stage_project(
        self,
        project_id: str,
        title: str,
        session_id: str,
        outputs: dict,
        pr_url: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Stage a project for human review.

        Args:
            project_id: Unique project identifier
            title: Human-readable title
            session_id: Jules session ID
            outputs: Output from JulesClient.get_session_outputs()
            pr_url: GitHub PR URL if available
            description: Project description

        Returns:
            True if staging succeeded
        """
        try:
            project_dir = STAGING_DIR / project_id
            project_dir.mkdir(parents=True, exist_ok=True)

            # Extract stats from outputs
            files = outputs.get("files", [])
            patch = outputs.get("patch", "")

            additions = sum(f.get("additions", 0) for f in files)
            deletions = sum(f.get("deletions", 0) for f in files)

            # Save metadata
            metadata = StagedProject(
                id=project_id,
                title=title,
                description=description,
                session_id=session_id,
                pr_url=pr_url,
                staged_at=datetime.now().isoformat(),
                status="STAGED",
                files_count=len(files),
                additions=additions,
                deletions=deletions,
            )

            (project_dir / "metadata.json").write_text(
                metadata.model_dump_json(indent=2), encoding="utf-8"
            )

            # Save the full patch
            if patch:
                (project_dir / "diff.patch").write_text(patch, encoding="utf-8")

            # Save files list for quick reference
            if files:
                (project_dir / "files.json").write_text(
                    json.dumps(files, indent=2, ensure_ascii=False), encoding="utf-8"
                )

            logger.success(
                f"📦 [STAGING] Project staged: {project_id} ({len(files)} files)"
            )
            return True

        except Exception as e:
            logger.error(f"💥 [STAGING] Failed to stage project: {e}")
            return False

    def list_staged_projects(self) -> list[StagedProject]:
        """List all projects currently in staging."""
        projects = []

        if not STAGING_DIR.exists():
            return projects

        for project_dir in STAGING_DIR.iterdir():
            if not project_dir.is_dir():
                continue

            metadata_file = project_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
                projects.append(StagedProject(**data))
            except Exception as e:
                logger.warning(f"⚠️ [STAGING] Failed to load {project_dir.name}: {e}")

        # Sort by staged_at descending (newest first)
        projects.sort(key=lambda p: p.staged_at, reverse=True)
        return projects

    def get_project(self, project_id: str) -> Optional[StagedProject]:
        """Get a specific staged project by ID."""
        project_dir = STAGING_DIR / project_id
        metadata_file = project_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            return StagedProject(**data)
        except Exception:
            return None

    def get_project_diff(self, project_id: str) -> Optional[str]:
        """Get the diff patch for a project."""
        patch_file = STAGING_DIR / project_id / "diff.patch"

        if not patch_file.exists():
            return None

        try:
            return patch_file.read_text(encoding="utf-8")
        except Exception:
            return None

    def get_project_files(self, project_id: str) -> list[dict]:
        """Get the list of modified files for a project."""
        files_file = STAGING_DIR / project_id / "files.json"

        if not files_file.exists():
            return []

        try:
            return json.loads(files_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def update_status(self, project_id: str, status: str) -> bool:
        """Update the status of a staged project."""
        project_dir = STAGING_DIR / project_id
        metadata_file = project_dir / "metadata.json"

        if not metadata_file.exists():
            return False

        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            data["status"] = status
            metadata_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return True
        except Exception:
            return False

    async def accept_project(self, project_id: str) -> dict:
        """
        Accept a project: merge the PR and clean up staging.

        Returns:
            {"success": bool, "message": str}
        """
        project = self.get_project(project_id)
        if not project:
            return {"success": False, "message": "Project not found"}

        # Merge PR if available
        if project.pr_url:
            try:
                from jules.git_ops import merge_pr

                merged = await merge_pr(project.pr_url)
                if not merged:
                    return {"success": False, "message": "Failed to merge PR"}
            except Exception as e:
                logger.error(f"💥 [STAGING] Merge failed: {e}")
                return {"success": False, "message": f"Merge error: {e}"}

        # Update status and clean up
        self.update_status(project_id, "MERGED")

        # Remove from staging (keep in logs via metadata update)
        project_dir = STAGING_DIR / project_id
        try:
            shutil.rmtree(project_dir)
        except Exception:
            pass

        logger.success(f"✅ [STAGING] Project accepted: {project_id}")
        return {"success": True, "message": "Project merged successfully"}

    async def reject_project(
        self, project_id: str, reason: Optional[str] = None
    ) -> dict:
        """
        Reject a project: close PR, delete branch, save metadata only.

        SOTA 2026 Lifecycle:
        - Close the PR without merging
        - Delete the feature branch
        - Save only metadata to rejected folder (for memory, to not repeat)
        - Delete the staging folder (no need to keep files)

        Returns:
            {"success": bool, "message": str}
        """
        project_dir = STAGING_DIR / project_id
        if not project_dir.exists():
            return {"success": False, "message": "Project not found"}

        try:
            # 1. Load metadata
            metadata_file = project_dir / "metadata.json"
            if not metadata_file.exists():
                return {"success": False, "message": "Metadata not found"}

            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            pr_url = data.get("pr_url")

            # 2. Close PR and delete branch (GitHub cleanup)
            if pr_url:
                try:
                    from jules.git_ops import cleanup_pr

                    await cleanup_pr(pr_url, merge=False)
                    logger.info(
                        f"🧹 [STAGING] Cleaned up PR and branch for {project_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ [STAGING] GitHub cleanup failed (continuing): {e}"
                    )

            # 3. Update metadata with rejection info
            data["status"] = "REJECTED"
            data["rejected_at"] = datetime.now().isoformat()
            if reason:
                data["rejection_reason"] = reason

            # 4. Save metadata ONLY to rejected folder (no files, just for memory)
            rejected_dest = REJECTED_DIR / project_id
            rejected_dest.mkdir(parents=True, exist_ok=True)
            (rejected_dest / "metadata.json").write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            # 5. Delete staging folder completely (files not needed)
            shutil.rmtree(project_dir)

            logger.info(
                f"⚰️ [STAGING] Project rejected: {project_id} (metadata saved, files cleaned)"
            )
            return {"success": True, "message": "Project rejected and cleaned up"}

        except Exception as e:
            logger.error(f"💥 [STAGING] Reject failed: {e}")
            return {"success": False, "message": str(e)}

    def set_pending(self, project_id: str) -> dict:
        """Mark a project as pending (keep for later review)."""
        if self.update_status(project_id, "PENDING"):
            logger.info(f"⏳ [STAGING] Project set to pending: {project_id}")
            return {"success": True, "message": "Project marked as pending"}
        return {"success": False, "message": "Project not found"}


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

staging = StagingManager()
