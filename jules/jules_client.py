"""
JULES/JULES_CLIENT.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: JULES INTERFACE V2 (CORTEX) 🧠
PURPOSE: Interface de communication avec Google Jules API v1alpha.
         Gère les sessions, l'envoi de tâches, et le suivi des PRs.
         Supporte le mode dual-key (Guardian/Creator).
══════════════════════════════════════════════════════════════════════════════
"""

import aiohttp
import os
from typing import Optional, List
from pathlib import Path
from enum import Enum
import json
from loguru import logger
from pydantic import BaseModel


# ════════════════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════════════════


class JulesMode(str, Enum):
    """Dual-key strategy modes."""

    GUARDIAN = "guardian"  # Fast healing, auto-approve
    CREATOR = "creator"  # Feature creation, human review


class JulesSession(BaseModel):
    """Represents a Jules session (v1alpha)."""

    id: str
    name: str
    title: str
    status: str = "PENDING"
    pr_url: Optional[str] = None
    pr_title: Optional[str] = None
    pr_description: Optional[str] = None


class JulesSource(BaseModel):
    """Represents a connected GitHub source."""

    name: str
    id: str
    owner: str
    repo: str


# ════════════════════════════════════════════════════════════════════════════
# CLIENT
# ════════════════════════════════════════════════════════════════════════════


class JulesClient:
    """
    Client for Google Jules API v1alpha.

    Supports dual-key strategy:
    - GUARDIAN mode: Uses KEY_1, auto-approves plans, for healing.
    - CREATOR mode: Uses KEY_2, requires plan approval, for expansion.
    """

    BASE_URL = "https://jules.googleapis.com/v1alpha"

    def __init__(self, mode: JulesMode = JulesMode.GUARDIAN):
        self.mode = mode
        self.api_key = os.getenv("GOOGLE_JULES_API_KEY")

        if not self.api_key:
            logger.warning("⚠️ [JULES] No API Key found (GOOGLE_JULES_API_KEY)")

        self.session: Optional[aiohttp.ClientSession] = None
        self._source_cache: Optional[str] = None  # Cache default source

    async def start(self):
        """Initialize HTTP session."""
        if not self.api_key:
            raise ValueError("API Key missing (GOOGLE_JULES_API_KEY)")

        headers = {"X-Goog-Api-Key": self.api_key, "Content-Type": "application/json"}
        self.session = aiohttp.ClientSession(headers=headers)

        key_hint = self.api_key[-4:] if self.api_key else "None"
        logger.debug(
            f"🤖 [JULES] Client initialized (Mode: {self.mode.value}, Key: ...{key_hint})"
        )

    async def close(self):
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ════════════════════════════════════════════════════════════════════════
    # SOURCES
    # ════════════════════════════════════════════════════════════════════════

    async def list_sources(self) -> List[JulesSource]:
        """List all connected GitHub repositories."""
        if not self.session:
            return []

        url = f"{self.BASE_URL}/sources"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ [JULES] list_sources failed: {text}")
                    return []

                data = await resp.json()
                sources = []
                for src in data.get("sources", []):
                    gh = src.get("githubRepo", {})
                    sources.append(
                        JulesSource(
                            name=src.get("name", ""),
                            id=src.get("id", ""),
                            owner=gh.get("owner", ""),
                            repo=gh.get("repo", ""),
                        )
                    )
                return sources
        except Exception as e:
            logger.error(f"💥 [JULES] list_sources error: {e}")
            return []

    async def get_default_source(self) -> Optional[str]:
        """Get the default source (Trinity repo) or first available."""
        if self._source_cache:
            return self._source_cache

        sources = await self.list_sources()
        if not sources:
            return None

        # Prefer Trinity repo
        for src in sources:
            if "trinity" in src.repo.lower():
                self._source_cache = src.name
                return src.name

        # Fallback to first
        self._source_cache = sources[0].name
        return self._source_cache

    # ════════════════════════════════════════════════════════════════════════
    # SESSIONS
    # ════════════════════════════════════════════════════════════════════════

    async def create_session(
        self,
        prompt: str,
        title: str,
        source: Optional[str] = None,
        starting_branch: str = "main",
        auto_create_pr: bool = True,
        require_plan_approval: bool = False,
    ) -> Optional[JulesSession]:
        """
        Create a new coding session.

        Args:
            prompt: The task instruction.
            title: Human-readable title.
            source: Source name (e.g., "sources/github/owner/repo").
            starting_branch: Branch to start from.
            auto_create_pr: Whether to auto-create PR on completion.
            require_plan_approval: Whether to block for manual plan approval (Default: False).
        """
        if not self.session:
            logger.error("❌ [JULES] Client not ready.")
            return None

        # Resolve source
        if not source:
            source = await self.get_default_source()
            if not source:
                logger.error("❌ [JULES] No source available.")
                return None

        # Build payload
        payload = {
            "prompt": prompt,
            "title": title,
            "sourceContext": {
                "source": source,
                "githubRepoContext": {"startingBranch": starting_branch},
            },
        }

        # Mode-specific settings
        if auto_create_pr:
            payload["automationMode"] = "AUTO_CREATE_PR"

        # Explicitly set plan approval requirement
        if require_plan_approval:
            payload["requirePlanApproval"] = True

        url = f"{self.BASE_URL}/sessions"
        try:
            logger.info(f"📤 [JULES] Creating session: {title}")
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(
                        f"❌ [JULES] create_session failed {resp.status}: {text}"
                    )
                    return None

                data = await resp.json()
                return JulesSession(
                    id=data.get("id", ""),
                    name=data.get("name", ""),
                    title=data.get("title", title),
                    status="PENDING",
                )
        except Exception as e:
            logger.error(f"💥 [JULES] create_session error: {e}")
            return None
        finally:
            logger.debug("📊 [JULES] Session created")

    async def get_session(self, session_id: str) -> Optional[JulesSession]:
        """Get session details including PR status."""
        if not self.session:
            return None

        # Handle both formats: "sessions/123" and "123"
        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"

        url = f"{self.BASE_URL}/{session_id}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()

                # Extract PR info from outputs
                pr_url = None
                pr_title = None
                pr_desc = None
                for output in data.get("outputs", []):
                    pr = output.get("pullRequest")
                    if pr:
                        pr_url = pr.get("url")
                        pr_title = pr.get("title")
                        pr_desc = pr.get("description")
                        break

                # Determine status from API state field
                api_state = data.get("state", "")
                if pr_url:
                    status = "PR_OPEN"
                elif api_state == "AWAITING_PLAN_APPROVAL":
                    status = "AWAITING_PLAN_APPROVAL"
                elif api_state == "EXECUTING":
                    status = "EXECUTING"
                elif api_state == "PLANNING":
                    status = "PLANNING"
                elif api_state == "FAILED":
                    status = "FAILED"
                elif api_state == "COMPLETED":
                    status = "COMPLETED"
                else:
                    status = api_state if api_state else "PENDING"

                return JulesSession(
                    id=data.get("id", ""),
                    name=data.get("name", ""),
                    title=data.get("title", ""),
                    status=status,
                    pr_url=pr_url,
                    pr_title=pr_title,
                    pr_description=pr_desc,
                )
        except Exception as e:
            logger.error(f"⚠️ [JULES] get_session error: {e}")
            return None

    async def send_message(self, session_id: str, prompt: str) -> bool:
        """Send a follow-up message to an existing session."""
        if not self.session:
            return False

        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"

        url = f"{self.BASE_URL}/{session_id}:sendMessage"
        payload = {"prompt": prompt}

        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ [JULES] send_message failed: {text}")
                    return False
                return True
        except Exception:
            return False

    async def approve_plan(self, session_id: str) -> bool:
        """Approve the plan for a session (required in CREATOR mode)."""
        if not self.session:
            return False

        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"

        url = f"{self.BASE_URL}/{session_id}:approvePlan"

        try:
            async with self.session.post(url, json={}) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ [JULES] approve_plan failed: {text}")
                    return False
                logger.success(f"✅ [JULES] Plan approved for {session_id}")
                return True
        except Exception as e:
            logger.error(f"💥 [JULES] approve_plan error: {e}")
            return False

    async def list_sessions(self, page_size: int = 10) -> List[JulesSession]:
        """List recent sessions."""
        if not self.session:
            return []

        url = f"{self.BASE_URL}/sessions?pageSize={page_size}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                sessions = []
                for s in data.get("sessions", []):
                    sessions.append(
                        JulesSession(
                            id=s.get("id", ""),
                            name=s.get("name", ""),
                            title=s.get("title", ""),
                            status="PENDING",
                        )
                    )
                return sessions
        except Exception as e:
            logger.error(f"⚠️ [JULES] list_sessions error: {e}")
            return []

    # ════════════════════════════════════════════════════════════════════════
    # NEW API FEATURES (2026-01-26)
    # ════════════════════════════════════════════════════════════════════════

    async def get_activities(
        self,
        session_id: str,
        since_timestamp: Optional[str] = None,
        page_size: int = 30,
    ) -> List[dict]:
        """
        Get activities for a session with optional timestamp filter.

        Args:
            session_id: Session ID.
            since_timestamp: ISO timestamp to filter activities after (createTime filter).
                             Format: ISO timestamp
            page_size: Number of activities to fetch.

        Returns:
            List of activity objects (plan, progress, messages, etc.)
        """
        if not self.session:
            return []

        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"

        url = f"{self.BASE_URL}/{session_id}/activities?pageSize={page_size}"
        if since_timestamp:
            url += f"&createTime={since_timestamp}"

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"❌ [JULES] get_activities failed: {text}")
                    return []

                data = await resp.json()
                return data.get("activities", [])
        except Exception as e:
            logger.error(f"⚠️ [JULES] get_activities error: {e}")
            return []

    async def get_session_outputs(self, session_id: str) -> Optional[dict]:
        """
        Get file outputs from a completed session (git patch format).

        EXTENDED API: Returns the entire changeset in git patch format.
        This is more reliable than using gh CLI to get PR diffs.

        Returns:
            Dict with file changes, or None if not available.
            Example: {"patch": "...", "files": [{"path": "...", "additions": N, "deletions": N}]}
        """
        if not self.session:
            return None

        if not session_id.startswith("sessions/"):
            session_id = f"sessions/{session_id}"

        url = f"{self.BASE_URL}/{session_id}/outputs"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    # May not be available for incomplete sessions
                    return None

                data = await resp.json()
                return data
        except Exception as e:
            logger.error(f"⚠️ [JULES] get_session_outputs error: {e}")
            return None

    async def get_git_patch(self, session_id: str) -> Optional[str]:
        """
        Get the actual unidiff patch from session activities.

        SOTA 2026: This is the ONLY reliable way to get the diff.
        session.outputs only returns PR url/title/description.
        The actual patch is in activities[].artifacts[].changeSet.gitPatch.unidiffPatch.

        CRITICAL: Must return the MOST RECENT patch (after Jules pushes new commits).
        Activities are ordered by createTime, so we reverse to get latest first.

        Returns:
            The unidiff patch string, or None if not available.
        """
        activities = await self.get_activities(session_id, page_size=50)
        # CRITICAL: Reverse to get most recent activity first
        # After Jules refines code, new activities are appended at the end
        for activity in reversed(activities):
            artifacts = activity.get("artifacts", [])
            for artifact in artifacts:
                change_set = artifact.get("changeSet")
                if change_set:
                    git_patch = change_set.get("gitPatch", {})
                    patch = git_patch.get("unidiffPatch")
                    if patch:
                        create_time = activity.get("createTime", "unknown")
                        logger.debug(
                            f"🔍 [JULES] Found GitPatch ({len(patch)} chars) "
                            f"from activity at {create_time}"
                        )
                        return patch
        return None

    async def get_plan(self, session_id: str) -> Optional[dict]:
        """
        Get the generated plan from session activities.

        SOTA 2026: Use this to intercept and critique plans BEFORE execution.
        The plan is in activities[].planGenerated.plan.

        Returns:
            Dict with plan structure: {"id": str, "steps": [{"title": str, "description": str}]}
            or None if no plan was generated (e.g., auto-approve mode).
        """
        activities = await self.get_activities(session_id, page_size=20)
        for activity in activities:
            plan_generated = activity.get("planGenerated")
            if plan_generated:
                plan = plan_generated.get("plan")
                if plan:
                    logger.debug(
                        f"📋 [JULES] Found Plan with {len(plan.get('steps', []))} steps"
                    )
                    return plan
        return None

    async def create_repoless_session(
        self,
        prompt: str,
        title: str,
    ) -> Optional[JulesSession]:
        """
        Create a repoless session (serverless sandbox).

        EXTENDED API: Creates an ephemeral cloud dev environment with
        Node, Python, Rust, Bun preloaded. No GitHub repo required.

        Use cases:
        - Running isolated tests
        - Generating standalone code/scripts
        - Sandbox experiments without affecting the main repo

        Args:
            prompt: Task instruction.
            title: Human-readable title.

        Returns:
            JulesSession or None on failure.
        """
        if not self.session:
            logger.error("❌ [JULES] Client not ready.")
            return None

        # Repoless = No sourceContext
        payload = {
            "prompt": prompt,
            "title": title,
        }

        url = f"{self.BASE_URL}/sessions"
        try:
            logger.info(f"📤 [JULES] Creating repoless session: {title}")
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(
                        f"❌ [JULES] create_repoless_session failed {resp.status}: {text}"
                    )
                    return None

                data = await resp.json()
                return JulesSession(
                    id=data.get("id", ""),
                    name=data.get("name", ""),
                    title=data.get("title", title),
                    status="PENDING",
                )
        except Exception as e:
            logger.error(f"💥 [JULES] create_repoless_session error: {e}")
            return None
        finally:
            logger.debug("📊 [JULES] Repoless session created")


# ════════════════════════════════════════════════════════════════════════════
# PERSISTENCE HELPERS
# ════════════════════════════════════════════════════════════════════════════

JULES_MEMORY_FILE = Path("memories/jules/active_sessions.json")


def save_jules_task(session_id: str):
    """Saves a session ID to persistence."""
    try:
        tasks = load_jules_tasks()
        if session_id not in tasks:
            tasks.append(session_id)
            JULES_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            JULES_MEMORY_FILE.write_text(json.dumps(tasks))
    except Exception as e:
        logger.error(f"Failed to save Jules session: {e}")


def load_jules_tasks() -> List[str]:
    """Loads active session IDs."""
    if not JULES_MEMORY_FILE.exists():
        return []
    try:
        return json.loads(JULES_MEMORY_FILE.read_text())
    except Exception:
        return []


def remove_jules_task(session_id: str):
    """Removes a completed session."""
    try:
        tasks = load_jules_tasks()
        if session_id in tasks:
            tasks.remove(session_id)
            JULES_MEMORY_FILE.write_text(json.dumps(tasks))
    except Exception as e:
        logger.error(f"Failed to remove Jules session: {e}")
