"""
JULES/HARVEST.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SUGGESTION HARVESTER 🌾
PURPOSE: Caches Jules code analysis suggestions for NightlyCouncil fusion.
         Runs 1x/day (24h interval) via GUARDIAN key.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from jules.jules_client import JulesClient, JulesMode, save_jules_task

# CONSTANTS
HARVEST_STATE_FILE = Path("memories/jules/harvest_state.json")
HARVEST_CACHE_FILE = Path(
    "memories/jules/harvest_cache.json"
)  # New: for Council fusion
HARVEST_INTERVAL_HOURS = 24  # 1x per day (was 4h)

# Prompt optimisé pour récupérer les suggestions UI
HARVEST_PROMPT = """
🌾 JULES SUGGESTION SYNC

Tu as analysé ce repo et généré des suggestions d'amélioration dans l'onglet "Codebase overview" > "Suggested".

MISSION CRITIQUE:
Génère un fichier `memories/jules/HARVEST_SUGGESTIONS.md` contenant EXACTEMENT les suggestions que tu as déjà identifiées.

PRIORITÉS À INCLURE:
- CRITIQUE: Bugs, erreurs, problèmes de sécurité
- HAUTE: Performance, blocking I/O, patterns inefficaces

FORMAT STRICT (Markdown):
```
# 🌾 Jules Harvest - {date}

## CRITIQUE
- [ ] **[Titre exact de ta suggestion]** | `fichier.py:ligne` | Explication courte

## HAUTE  
- [ ] **[Titre exact de ta suggestion]** | `fichier.py:ligne` | Explication courte
```

RÈGLES:
1. NE modifie aucun code - génère UNIQUEMENT le fichier markdown
2. Utilise les TITRES EXACTS de tes suggestions (ceux visibles dans "Suggested")
3. Inclus le fichier et la ligne concernés
4. Ne génère que CRITIQUE et HAUTE, ignore les priorités moyennes/basses

Si tu n'as pas de suggestions stockées, analyse le code et génère-en.
"""


class SuggestionHarvester:
    """Harvests suggestions from Jules and imports to wishlist."""

    def __init__(self):
        self._load_state()

    def _load_state(self):
        """Load harvest state from disk."""
        if HARVEST_STATE_FILE.exists():
            try:
                self.state = json.loads(HARVEST_STATE_FILE.read_text())
            except Exception:
                self.state = {"last_harvest": None, "pending_session": None}
        else:
            self.state = {"last_harvest": None, "pending_session": None}

    def _save_state(self):
        """Save harvest state to disk."""
        HARVEST_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HARVEST_STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def should_harvest(self) -> bool:
        """Check if enough time has passed since last harvest."""
        # Don't start new harvest if sessions are still pending
        if self.state.get("pending_sessions"):
            logger.debug("🌾 [HARVEST] Sessions pending, skipping new harvest.")
            return False

        last = self.state.get("last_harvest")
        if not last:
            return True

        try:
            last_dt = datetime.fromisoformat(last)
            elapsed = datetime.now() - last_dt
            should = elapsed >= timedelta(hours=HARVEST_INTERVAL_HOURS)
            if not should:
                logger.debug(
                    f"🌾 [HARVEST] Next harvest in {HARVEST_INTERVAL_HOURS - (elapsed.seconds // 3600)}h"
                )
            return should
        except Exception:
            return True

    async def start_harvest(self) -> str:
        """Start harvest sessions on BOTH keys simultaneously."""
        logger.info("🌾 [HARVEST] Starting dual-key suggestion harvest...")

        results = []
        pending_sessions = []

        # Create sessions on BOTH keys in parallel
        for mode in [JulesMode.GUARDIAN, JulesMode.CREATOR]:
            try:
                async with JulesClient(mode=mode) as client:
                    response = await client.create_session(
                        prompt=HARVEST_PROMPT,
                        title=f"🌾 Harvest ({mode.value}) - {datetime.now().strftime('%H:%M')}",
                        auto_create_pr=True,
                        require_plan_approval=False,
                    )

                    if response:
                        logger.success(
                            f"🌾 [HARVEST] Session created: {response.id} (Key: {mode.value})"
                        )
                        save_jules_task(response.id)
                        pending_sessions.append(
                            {
                                "id": response.id,
                                "key": mode.value,
                                "created_at": datetime.now().isoformat(),
                            }
                        )
                        results.append(response.id)
            except Exception as e:
                logger.error(f"🌾 [HARVEST] Failed on {mode.value}: {e}")

        # Track all pending sessions
        self.state["pending_sessions"] = pending_sessions
        self.state["last_harvest"] = datetime.now().isoformat()
        self._save_state()

        return results[0] if results else None

    async def check_and_import(self, session_id: str, pr_url: str = None) -> int:
        """Check if a completed session is a harvest and import suggestions via API."""
        # Check if this session is in our pending list
        pending_sessions = self.state.get("pending_sessions") or []
        session_info = None

        for ps in pending_sessions:
            if ps.get("id") == session_id:
                session_info = ps
                break

        if not session_info:
            return 0  # Not a harvest session

        # Wait at least 10 minutes after creation before checking (avoid unnecessary calls)
        created_at = session_info.get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at)
                elapsed = datetime.now() - created_dt
                if elapsed < timedelta(minutes=10):
                    logger.debug(
                        f"🌾 [HARVEST] Waiting... ({10 - elapsed.seconds // 60}min left)"
                    )
                    return 0  # Too early, will check later
            except Exception:
                pass  # Continue if timestamp parsing fails

        logger.info(f"🌾 [HARVEST] Fetching suggestions from session {session_id}...")

        # Get the key used for this session
        key = session_info.get("key", "guardian")
        mode = JulesMode.GUARDIAN if key == "guardian" else JulesMode.CREATOR

        # Remove this session from pending list
        self.state["pending_sessions"] = [
            ps for ps in pending_sessions if ps.get("id") != session_id
        ]
        self._save_state()

        # Fetch activities via API to get the patch content
        try:
            async with JulesClient(mode=mode) as client:
                url = f"{client.BASE_URL}/sessions/{session_id}/activities"

                async with client.session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(
                            f"🌾 [HARVEST] Failed to fetch activities: {resp.status}"
                        )
                        return 0

                    data = await resp.json()
                    activities = data.get("activities", [])

                    # Find the activity with the patch (usually sessionCompleted or progressUpdated)
                    for activity in reversed(activities):  # Start from newest
                        artifacts = activity.get("artifacts", [])
                        for artifact in artifacts:
                            change_set = artifact.get("changeSet", {})
                            git_patch = change_set.get("gitPatch", {})
                            patch_content = git_patch.get("unidiffPatch", "")

                            if (
                                "SUGGESTIONS" in patch_content
                                or "CRITIQUE" in patch_content
                            ):
                                logger.info(
                                    "🌾 [HARVEST] Found suggestions in activity!"
                                )
                                # Extract the actual content from the diff
                                suggestions_md = self._extract_from_patch(patch_content)
                                if suggestions_md:
                                    items = self.parse_harvest_file(suggestions_md)
                                    return self.cache_suggestions(items)

                    logger.warning("🌾 [HARVEST] No suggestions found in activities")
                    return 0

        except Exception as e:
            logger.error(f"🌾 [HARVEST] Import error: {e}")
            return 0

    def _extract_from_patch(self, patch: str) -> str:
        """Extract markdown content from a unified diff patch."""
        lines = []
        in_content = False

        # Handle both real newlines and escaped newlines
        if "\\n" in patch and "\n" not in patch:
            patch_lines = patch.split("\\n")
        else:
            patch_lines = patch.split("\n")

        for line in patch_lines:
            # Skip diff headers
            if line.startswith("diff --git") or line.startswith("index "):
                continue
            if line.startswith("--- ") or line.startswith("+++ "):
                continue
            if line.startswith("@@ "):
                in_content = True
                continue

            # Extract added lines (remove the + prefix)
            if in_content and line.startswith("+"):
                lines.append(line[1:])  # Remove the + prefix

        return "\n".join(lines)

    def parse_harvest_file(self, content: str) -> list:
        """Parse HARVEST_SUGGESTIONS.md content and extract items."""
        items = []
        current_priority = None

        for line in content.splitlines():
            line = line.strip()

            # Detect priority headers
            if "## CRITIQUE" in line:
                current_priority = "CRITIQUE"
            elif "## HAUTE" in line:
                current_priority = "HAUTE"
            elif line.startswith("## "):
                current_priority = None  # Ignore other priorities

            # Extract items - handle both formats:
            # Format 1: - [ ] **Titre** | `file` | Description
            # Format 2: - [ ] **Titre** - `file` - Description
            if current_priority and line.startswith("- [ ] **"):
                # Try pipe format first
                match = re.match(
                    r"- \[ \] \*\*(.+?)\*\*\s*[\|\-]\s*`(.+?)`\s*[\|\-]\s*(.+)", line
                )
                if match:
                    items.append(
                        {
                            "title": match.group(1),
                            "location": match.group(2),
                            "description": match.group(3),
                            "priority": current_priority,
                        }
                    )

        return items

    def cache_suggestions(self, items: list) -> int:
        """Cache parsed items to JSON for NightlyCouncil fusion."""
        if not items:
            return 0

        # Load existing cache
        if HARVEST_CACHE_FILE.exists():
            try:
                cached = json.loads(HARVEST_CACHE_FILE.read_text())
            except Exception:
                cached = {"items": [], "updated_at": None}
        else:
            cached = {"items": [], "updated_at": None}

        # Merge new items (dedupe by title)
        existing_titles = {i["title"] for i in cached.get("items", [])}
        added = 0

        for item in items:
            if item["title"] not in existing_titles:
                cached["items"].append(item)
                existing_titles.add(item["title"])
                added += 1

        # Cap at 20 items (most recent)
        cached["items"] = cached["items"][-20:]
        cached["updated_at"] = datetime.now().isoformat()

        # Save cache
        HARVEST_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HARVEST_CACHE_FILE.write_text(json.dumps(cached, indent=2))

        logger.success(f"🌾 [HARVEST] Cached {added} items for NightlyCouncil")
        return added

    @staticmethod
    def get_cached_suggestions() -> list:
        """Return cached suggestions for NightlyCouncil fusion."""
        if not HARVEST_CACHE_FILE.exists():
            return []

        try:
            cached = json.loads(HARVEST_CACHE_FILE.read_text())
            items = cached.get("items", [])

            # Convert to NightlyCouncil format
            suggestions = []
            for item in items:
                suggestions.append(
                    {
                        "title": item["title"],
                        "description": f"{item['description']} ({item['location']})",
                        "source": "harvest",
                        "priority": item.get("priority", "HAUTE"),
                    }
                )

            logger.debug(
                f"🌾 [HARVEST] Providing {len(suggestions)} suggestions to Council"
            )
            return suggestions

        except Exception as e:
            logger.error(f"🌾 [HARVEST] Cache read error: {e}")
            return []


# Singleton
harvester = SuggestionHarvester()
