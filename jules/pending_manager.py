"""
JULES/PENDING_MANAGER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: PENDING PROJECT MANAGER 📁
PURPOSE: Manages projects in "waiting" state for user review.
         Projects can be analyzed by Antigravity before merge decision.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from corpus.dna import genome

# Storage directories
PENDING_DIR = genome.ROOT_DIR / "memories" / "jules" / "pending"
REJECTED_DIR = genome.ROOT_DIR / "memories" / "jules" / "rejected"


class PendingManager:
    """
    Manages projects awaiting user decision.
    Each project gets its own folder with metadata and PR details.
    """

    def __init__(self):
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    def move_to_pending(
        self,
        project_id: str,
        project_data: dict,
        pr_url: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> Path:
        """
        Move a project to pending state.

        Args:
            project_id: Unique identifier (slug format)
            project_data: Full project data from morning brief
            pr_url: GitHub PR URL if available
            branch: Branch name if available

        Returns:
            Path to the created pending folder
        """
        # Sanitize ID for filesystem
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_id)
        project_dir = PENDING_DIR / safe_id

        # Clean previous if exists
        if project_dir.exists():
            shutil.rmtree(project_dir)

        project_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = {
            "id": project_id,
            "created_at": datetime.now().isoformat(),
            "status": "PENDING_REVIEW",
            "project": project_data,
            "pr_url": pr_url,
            "branch": branch,
        }

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

        logger.success(
            f"📁 [PENDING] Project '{project_id}' moved to pending: {project_dir}"
        )
        return project_dir

    def list_pending(self) -> list[dict]:
        """
        List all pending projects.

        Returns:
            List of project metadata dicts
        """
        projects = []

        if not PENDING_DIR.exists():
            return projects

        for folder in PENDING_DIR.iterdir():
            if folder.is_dir():
                metadata_file = folder / "metadata.json"
                if metadata_file.exists():
                    try:
                        data = json.loads(metadata_file.read_text(encoding="utf-8"))
                        data["folder"] = str(folder)
                        projects.append(data)
                    except Exception as e:
                        logger.warning(f"📁 [PENDING] Failed to read {folder}: {e}")

        # Sort by creation date (newest first)
        projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return projects

    def get_pending(self, project_id: str) -> Optional[dict]:
        """
        Get a specific pending project.

        Args:
            project_id: Project identifier

        Returns:
            Project metadata or None if not found
        """
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_id)
        project_dir = PENDING_DIR / safe_id
        metadata_file = project_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            data["folder"] = str(project_dir)
            return data
        except Exception as e:
            logger.error(f"📁 [PENDING] Failed to read {project_id}: {e}")
            return None

    def delete_pending(self, project_id: str) -> bool:
        """
        Delete a pending project (after merge or rejection).

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_id)
        project_dir = PENDING_DIR / safe_id

        if not project_dir.exists():
            return False

        try:
            shutil.rmtree(project_dir)
            logger.info(f"📁 [PENDING] Deleted project '{project_id}'")
            return True
        except Exception as e:
            logger.error(f"📁 [PENDING] Failed to delete {project_id}: {e}")
            return False

    def update_status(self, project_id: str, status: str, notes: str = "") -> bool:
        """
        Update the status of a pending project.

        Args:
            project_id: Project identifier
            status: New status (e.g., "REVIEWED", "READY_TO_MERGE")
            notes: Optional notes from review

        Returns:
            True if updated, False if not found
        """
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_id)
        project_dir = PENDING_DIR / safe_id
        metadata_file = project_dir / "metadata.json"

        if not metadata_file.exists():
            return False

        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            data["status"] = status
            data["updated_at"] = datetime.now().isoformat()
            if notes:
                data["review_notes"] = notes
            metadata_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f"📁 [PENDING] Updated '{project_id}' status to {status}")
            return True
        except Exception as e:
            logger.error(f"📁 [PENDING] Failed to update {project_id}: {e}")
            return False

    def count_pending(self) -> int:
        """Get the number of pending projects."""
        if not PENDING_DIR.exists():
            return 0
        return sum(1 for f in PENDING_DIR.iterdir() if f.is_dir())

    def move_to_rejected(
        self,
        project_id: str,
        project_data: dict,
        reason: str = "User rejected",
        pr_url: Optional[str] = None,
    ) -> Path:
        """
        Archive a rejected project so it won't be proposed again.

        Args:
            project_id: Unique identifier
            project_data: Full project data (title, description, etc.)
            reason: Why it was rejected
            pr_url: GitHub PR URL if available

        Returns:
            Path to the created rejected folder
        """
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Include timestamp to keep history if same idea proposed multiple times
        project_dir = REJECTED_DIR / f"{safe_id}_{timestamp}"

        project_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = {
            "id": project_id,
            "rejected_at": datetime.now().isoformat(),
            "reason": reason,
            "project": project_data,
            "pr_url": pr_url,
            # Extract key fields for easy searching
            "title": project_data.get("title", project_data.get("name", project_id)),
            "description": project_data.get("description", ""),
        }

        metadata_file = project_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

        logger.warning(f"📁 [REJECTED] Project '{project_id}' archived: {project_dir}")
        return project_dir

    def list_rejected(self) -> list[dict]:
        """
        List all rejected projects.

        Returns:
            List of rejected project metadata dicts
        """
        projects = []

        if not REJECTED_DIR.exists():
            return projects

        for folder in REJECTED_DIR.iterdir():
            if folder.is_dir():
                metadata_file = folder / "metadata.json"
                if metadata_file.exists():
                    try:
                        data = json.loads(metadata_file.read_text(encoding="utf-8"))
                        data["folder"] = str(folder)
                        projects.append(data)
                    except Exception as e:
                        logger.warning(f"📁 [REJECTED] Failed to read {folder}: {e}")

        # Sort by rejection date (newest first)
        projects.sort(key=lambda x: x.get("rejected_at", ""), reverse=True)
        return projects

    def is_rejected(self, title: str) -> bool:
        """
        Check if a project with similar title was already rejected.

        Args:
            title: Project title to check

        Returns:
            True if a similar project was rejected
        """
        title_lower = title.lower().strip()
        for project in self.list_rejected():
            rejected_title = project.get("title", "").lower().strip()
            # Fuzzy match: same title or one contains the other
            if (
                title_lower == rejected_title
                or title_lower in rejected_title
                or rejected_title in title_lower
            ):
                return True
        return False


# Singleton
pending_manager = PendingManager()
