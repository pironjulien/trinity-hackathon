"""
JULES/NIGHTLY_COUNCIL.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE NIGHTLY COUNCIL 🌙
PURPOSE: Orchestrates the dual-analysis (Jules vs Trinity).
         Cross-validates ideas and prepares autonomous execution.
NOTE: Migrated from corpus/brain/council.py to respect Corpus Sanctity.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from loguru import logger

from corpus.brain.prefrontal import TrinityStrategist
from corpus.brain.gattaca import gattaca
from social.messaging.i18n import get_language

# Load .env BEFORE any Jules imports (for API keys)
load_dotenv(Path(__file__).parent.parent / ".env")

# ════════════════════════════════════════════════════════════════════════════════
# LOGGING: Import nerves to activate the jules.jsonl sink
# This ensures logs are routed to jules.jsonl even when running standalone
# ════════════════════════════════════════════════════════════════════════════════
import corpus.soma.nerves  # noqa: F401 - activates JSONL sink for jules.*


# JULES: Optional peripheral (not part of corpus vital core)
try:
    from jules.jules_client import JulesClient, JulesMode

    JULES_AVAILABLE = True
except ImportError:
    JULES_AVAILABLE = False
    JulesClient = None
    JulesMode = None

# Store suggestions here
MORNING_BRIEF_FILE = Path("memories/jules/morning_brief.json")

# SOTA 2026: Quota-based execution (target successes, not attempts)
TARGET_SUCCESS = 3  # PRs per night
MAX_ATTEMPTS = 10  # Prevent infinite loops


def _extract_json(response: str) -> Any:
    """Extract JSON from a response that may be wrapped in markdown code blocks."""

    if not response:
        return None

    # Try to find JSON in markdown code block (```json ... ```)
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if match:
        response = match.group(1).strip()

    return json.loads(response)


class NightlyCouncil:
    """
    The Committee that sleeps not.
    """

    def __init__(self):
        self.strategist = TrinityStrategist()

    async def convene(self):
        """
        Main execution flow of the Council (AUTONOMOUS NIGHTLY PIPELINE).

        1. Fetch Jules Ideas (Outsider) + Trinity Ideas (Insider)
        2. Fetch Harvest Cache + Evolution Proposals
        3. Cross-Validate all sources (Trinity 3 Pro)
        4. AUTO-EXECUTE: Send top 3 to The Forge (no human validation)
        5. Morning: User finds staged projects ready for review
        """
        logger.info("🌙 [COUNCIL] Convening the Nightly Council...")

        # 1. PARALLEL BRAINSTORM
        # Jules (Creator Key) + Trinity (Local)
        jules_task = self._fetch_jules_ideas()
        trinity_task = self.strategist.analyze_and_propose(limit=3)

        results = await asyncio.gather(jules_task, trinity_task, return_exceptions=True)

        jules_ideas = results[0] if isinstance(results[0], list) else []
        trinity_ideas = results[1] if isinstance(results[1], list) else []

        # 2. HARVEST CACHE (Code Analysis from previous harvest)
        harvest_ideas = self._fetch_harvest_cache()

        # 3. EVOLUTION PROPOSALS (SOTA 2026: Routed through Council)
        evolution_ideas = self._fetch_evolution_proposals()

        logger.info(
            f"🌙 [COUNCIL] Table is set: {len(jules_ideas)} Jules, {len(trinity_ideas)} Trinity, {len(harvest_ideas)} Harvest, {len(evolution_ideas)} Evolution."
        )

        all_ideas = jules_ideas + trinity_ideas + harvest_ideas + evolution_ideas
        if not all_ideas:
            logger.warning("🌙 [COUNCIL] Silence in the chamber (No ideas generated).")
            return

        # 3. THE DEBATE (Cross-Validation by Gattaca / Trinity 3 Pro)
        vetted_ideas = await self._cross_validate(all_ideas)

        # 4. SEMANTIC DEDUPLICATION (SOTA 2026: Prevents near-duplicate projects)
        vetted_ideas = await self._deduplicate_ideas(vetted_ideas)

        # 5. AUTONOMOUS EXECUTION (Quota-Based → Forge)
        # SOTA 2026: Continue until TARGET_SUCCESS is reached (not just 3 attempts)
        # This ensures we get 3 PRs per night even if some missions fail.
        await self._execute_missions(vetted_ideas)

        # 5. WEEKLY SELF-EVOLUTION (Sundays only)
        # Jules analyzes its own code and proposes improvements
        from datetime import datetime

        if datetime.now().weekday() == 6:  # Sunday
            await self._trigger_self_evolution()

    async def _fetch_jules_ideas(self):
        """Generate creative project ideas using Gattaca (simulating Jules' creative style)."""
        if not JULES_AVAILABLE:
            logger.debug("🌙 [COUNCIL] Jules not available (corpus standalone mode)")
            return []

        try:
            # Use Gattaca with a creative prompt (Jules style)
            # SOTA 2026: Language-aware prompts (Standard 362.18)
            lang = get_language()
            if lang == "fr":
                prompt = """
                Tu es JULES, l'Assistant Créatif de Trinity (External Perspective).
                
                Génère 3 idées de projets CRÉATIFS pour améliorer ou étendre le système.
                Pense "outside the box" - au-delà du code technique:
                
                1. **Features UX** - Nouvelles interfaces ou améliorations d'expérience
                2. **Content** - Génération de contenu, documentation, tutoriels
                3. **Automation** - Scripts d'automatisation, outils CLI
                4. **Research** - Analyses, rapports, prototypes
                5. **Integration** - Connexions avec d'autres services ou APIs
                
                FORMAT JSON (Liste):
                [
                    {
                        "title": "Nom du projet",
                        "description": "Description en 2-3 phrases",
                        "source": "JULES_CREATIVE",
                        "confidence": 70-95
                    }
                ]
                """
            else:
                prompt = """
                You are JULES, Trinity's Creative Assistant (External Perspective).
                
                Generate 3 CREATIVE project ideas to improve or extend the system.
                Think outside the box - beyond technical code:
                
                1. **UX Features** - New interfaces or experience improvements
                2. **Content** - Content generation, documentation, tutorials
                3. **Automation** - Automation scripts, CLI tools
                4. **Research** - Analyses, reports, prototypes
                5. **Integration** - Connections with other services or APIs
                
                FORMAT JSON (List):
                [
                    {
                        "title": "Project name",
                        "description": "Description in 2-3 sentences",
                        "source": "JULES_CREATIVE",
                        "confidence": 70-95
                    }
                ]
                """
            response = await gattaca.route(prompt=prompt, route_id=gattaca.ROUTE_FLASH)
            ideas = _extract_json(response) if isinstance(response, str) else response

            if isinstance(ideas, list):
                logger.info(f"🌙 [COUNCIL] Jules generated {len(ideas)} creative ideas")
                return ideas[:3]
            return []
        except Exception as e:
            logger.error(f"🌙 [COUNCIL] Jules failed to attend: {e}")
            return []

    def _fetch_harvest_cache(self) -> list:
        """Fetch cached suggestions from Harvest (code analysis)."""
        if not JULES_AVAILABLE:
            return []

        try:
            from jules.harvest import SuggestionHarvester

            return SuggestionHarvester.get_cached_suggestions()
        except Exception as e:
            logger.debug(f"🌙 [COUNCIL] Harvest cache unavailable: {e}")
            return []

    def _fetch_evolution_proposals(self) -> list:
        """
        SOTA 2026: Fetch proposals from Evolution module.
        Evolution writes expansion opportunities here instead of direct Jules delegation.
        Proposals are consumed (cleared) after reading.
        """
        try:
            proposals_file = Path("memories/trinity/evolution_proposals.json")
            if not proposals_file.exists():
                return []

            proposals = json.loads(proposals_file.read_text())

            if proposals:
                # Clear after reading (consumed by Council)
                proposals_file.write_text("[]")
                logger.info(
                    f"🌙 [COUNCIL] Fetched {len(proposals)} Evolution proposals"
                )

            return proposals if isinstance(proposals, list) else []
        except Exception as e:
            logger.debug(f"🌙 [COUNCIL] Evolution proposals unavailable: {e}")
            return []

    async def _cross_validate(self, ideas: list) -> list:
        """
        Uses Gattaca to critique execution feasibility and alignment.
        """
        # SOTA 2026: Language-aware prompts (Standard 362.18)
        lang = get_language()
        if lang == "fr":
            prompt = f"""
            Tu présides le COMITÉ DE SÉLECTION PROJET (2026).
            
            CANDIDATS:
            {json.dumps(ideas, indent=2)}
            
            MISSION:
            Classe TOUS les projets valides par ordre de pertinence.
            Ne te limite pas à 3 projets, garde tous ceux qui sont bons.
            
            CRITÈRES DE SÉLECTION:
            1. **Valeur Ajoutée**: Est-ce utile maintenant ?
            2. **Faisabilité**: Réalisable en < 1 journée par l'agent ?
            3. **Equilibre**: Mélange de Technique (Trinity) et Créatif (Jules).
            4. **Classification**: Pour chaque projet, détermine "requires_repo":
               - true → modifie le codebase Trinity (feature, bugfix, refactoring)
               - false → script standalone, analyse, rapport, génération (sandbox Repoless)
            
            FORMAT DE SORTIE (JSON List):
            Renvoie la liste filtrée et triée, avec les clés ajoutées/conservées:
            - "confidence": score de confiance 0-100 (préserve le score source)
            - "verdict": pourquoi retenu
            - "requires_repo": true ou false selon la classification
            """
        else:
            prompt = f"""
            You preside over the PROJECT SELECTION COMMITTEE (2026).
            
            CANDIDATES:
            {json.dumps(ideas, indent=2)}
            
            MISSION:
            Rank ALL valid projects by relevance.
            Do not limit to 3 projects, keep all good ones.
            
            SELECTION CRITERIA:
            1. **Added Value**: Is it useful now?
            2. **Feasibility**: Achievable in < 1 day by the agent?
            3. **Balance**: Mix of Technical (Trinity) and Creative (Jules).
            4. **Classification**: For each project, determine "requires_repo":
               - true → modifies Trinity codebase (feature, bugfix, refactoring)
               - false → standalone script, analysis, report, generation (Repoless sandbox)
            
            OUTPUT FORMAT (JSON List):
            Return the filtered and sorted list, with keys added/preserved:
            - "confidence": confidence score 0-100 (preserve source score)
            - "verdict": why selected
            - "requires_repo": true or false based on classification
            """

        try:
            response = await gattaca.route(prompt=prompt, route_id=gattaca.ROUTE_PRO)
            # Parse JSON response
            vetted = _extract_json(response) if isinstance(response, str) else response
            return vetted if isinstance(vetted, list) else ideas
        except Exception as e:
            logger.error(f"🌙 [COUNCIL] Debate error: {e}")
            return ideas  # Fallback to raw list

    async def _deduplicate_ideas(self, ideas: list) -> list:
        """
        SOTA 2026: Semantic deduplication to prevent near-duplicate projects.
        Uses Gattaca to identify projects that are conceptually identical.
        """
        if len(ideas) <= 1:
            return ideas

        # Also check against current staging projects
        staging_titles = []
        staging_dir = Path("memories/jules/staging")
        if staging_dir.exists():
            for project_dir in staging_dir.iterdir():
                if project_dir.is_dir():
                    meta_file = project_dir / "metadata.json"
                    if meta_file.exists():
                        try:
                            meta = json.loads(meta_file.read_text())
                            staging_titles.append(meta.get("title", ""))
                        except Exception:
                            pass

        # SOTA 2026: Language-aware prompt
        lang = get_language()
        if lang == "fr":
            prompt = f"""
TÂCHE DE DÉDUPLICATION: Identifie les projets DUPLIQUÉS ou QUASI-IDENTIQUES.

NOUVELLES IDÉES:
{json.dumps([{"title": i.get("title"), "description": i.get("description", "")[:100]} for i in ideas], indent=2)}

DÉJÀ EN STAGING:
{json.dumps(staging_titles, indent=2)}

RÈGLES:
1. Deux projets sont DUPLIQUÉS s'ils résolvent le même problème (même avec des mots différents)
2. "Auth Unification" et "Auth Consolidation" = DUPLIQUÉS
3. Garde la PREMIÈRE occurrence, marque les autres comme doublons
4. Compare aussi avec les projets déjà en staging

FORMAT DE SORTIE (JSON):
{{"keep_indices": [0, 2], "duplicates": [{{"index": 1, "duplicate_of": "titre"}}]}}
"""
        else:
            prompt = f"""
DEDUPLICATION TASK: Identify DUPLICATE or NEAR-DUPLICATE projects.

NEW IDEAS:
{json.dumps([{"title": i.get("title"), "description": i.get("description", "")[:100]} for i in ideas], indent=2)}

ALREADY IN STAGING:
{json.dumps(staging_titles, indent=2)}

RULES:
1. Two projects are DUPLICATES if they solve the same problem (even with different wording)
2. "Auth Unification" and "Auth Consolidation" = DUPLICATES
3. Keep the FIRST occurrence, mark others as duplicates
4. Also compare against projects already in staging

OUTPUT FORMAT (JSON):
{{"keep_indices": [0, 2], "duplicates": [{{"index": 1, "duplicate_of": "title"}}]}}
"""

        try:
            response = await gattaca.route(prompt=prompt, route_id=gattaca.ROUTE_FLASH)
            result = _extract_json(response) if isinstance(response, str) else response

            if result and "keep_indices" in result:
                kept = [ideas[i] for i in result["keep_indices"] if i < len(ideas)]
                if result.get("duplicates"):
                    for dup in result["duplicates"]:
                        if dup.get("index") is not None and dup["index"] < len(ideas):
                            logger.info(
                                f"🌙 [COUNCIL] Filtered duplicate: "
                                f"{ideas[dup['index']].get('title')} ≈ {dup.get('duplicate_of')}"
                            )
                logger.info(
                    f"🌙 [COUNCIL] Deduplication: {len(ideas)} → {len(kept)} unique ideas"
                )
                return kept
        except Exception as e:
            logger.error(f"🌙 [COUNCIL] Dedup error: {e}")

        return ideas  # Fallback

    async def _execute_missions(self, missions: list):
        """
        AUTONOMOUS EXECUTION: Send missions to The Forge.
        SOTA 2026: Quota-based execution - continue until TARGET_SUCCESS is reached.

        Logic (prevents infinite loops):
        - Batch 1: Launch TARGET_SUCCESS missions
        - If K succeed, need (TARGET_SUCCESS - K) more
        - Batch 2: Launch (TARGET_SUCCESS - K) from remaining pool
        - Repeat until quota met OR pool exhausted
        """
        if not JULES_AVAILABLE:
            logger.warning("🌙 [COUNCIL] Jules not available - cannot execute missions")
            return

        try:
            from jules.forge import forge
        except ImportError:
            logger.error("🌙 [COUNCIL] Forge not available")
            return

        # Import pending_manager for rejection check
        pending_manager = None
        try:
            from jules.pending_manager import pending_manager

            can_check_rejected = True
        except ImportError:
            can_check_rejected = False

        # Filter out rejected missions upfront
        available_missions = []
        for mission in missions:
            title = mission.get("title", "Unknown")
            if (
                can_check_rejected
                and pending_manager
                and pending_manager.is_rejected(title)
            ):
                logger.info(f"🌙 [COUNCIL] Skipping rejected project: {title}")
                continue
            available_missions.append(mission)

        results = []
        total_success = 0
        batch_num = 0
        mission_index = 0  # Track position in available_missions pool

        # SOTA 2026: Count existing projects in staging to avoid redundant forging
        staging_dir = Path("memories/jules/staging")
        existing_staged = 0
        if staging_dir.exists():
            existing_staged = len([d for d in staging_dir.iterdir() if d.is_dir()])
            if existing_staged > 0:
                logger.info(
                    f"🌙 [COUNCIL] {existing_staged} project(s) already in staging - "
                    f"targeting {TARGET_SUCCESS - existing_staged} new success(es)"
                )

        adjusted_target = max(0, TARGET_SUCCESS - existing_staged)
        if adjusted_target == 0:
            logger.info("🌙 [COUNCIL] Staging full - no new missions needed")
            return

        # Continue until we hit adjusted target or exhaust the pool
        while total_success < adjusted_target and mission_index < len(
            available_missions
        ):
            batch_num += 1
            needed = adjusted_target - total_success
            batch_size = min(needed, len(available_missions) - mission_index)

            if batch_size <= 0:
                break

            logger.info(
                f"🌙 [COUNCIL] Batch {batch_num}: Launching {batch_size} missions "
                f"(need {needed} more successes)"
            )

            batch_success = 0
            for i in range(batch_size):
                mission = available_missions[mission_index]
                mission_index += 1
                title = mission.get("title", f"Project {mission_index}")

                logger.info(
                    f"🌙 [COUNCIL] ⚒️ Forging mission {mission_index}/{len(available_missions)}: {title}"
                )

                try:
                    result = await forge.forge_mission(
                        {
                            "title": title,
                            "description": mission.get("description", ""),
                            "rationale": mission.get("verdict", ""),
                            "requires_repo": mission.get("requires_repo", True),
                            "confidence": mission.get("confidence", 75),
                            "source": mission.get("source", "COUNCIL"),
                        }
                    )

                    results.append(
                        {
                            "title": title,
                            "status": result.get("status"),
                            "pr_url": result.get("pr_url"),
                            "score": result.get("score"),
                            "session_id": result.get("session_id"),
                        }
                    )

                    if result.get("status") == "SUCCESS":
                        batch_success += 1
                        total_success += 1
                        logger.success(
                            f"🌙 [COUNCIL] ✅ Mission SUCCESS: {title} → {result.get('pr_url')}"
                        )
                    else:
                        # SOTA 2026: Failures are normal - Critic doing its job
                        logger.info(
                            f"🌙 [COUNCIL] ❌ Mission FAILED: {title} → {result.get('reason')}"
                        )

                except Exception as e:
                    logger.error(f"🌙 [COUNCIL] Mission error for {title}: {e}")
                    results.append(
                        {
                            "title": title,
                            "status": "ERROR",
                            "error": str(e),
                        }
                    )

            logger.info(
                f"🌙 [COUNCIL] Batch {batch_num} complete: {batch_success}/{batch_size} succeeded "
                f"(total: {total_success}/{TARGET_SUCCESS})"
            )

        # Save execution report
        report = {
            "date": datetime.now().isoformat(),
            "target": TARGET_SUCCESS,
            "achieved": total_success,
            "batches": batch_num,
            "total_attempted": mission_index,
            "pool_size": len(available_missions),
            "results": results,
        }

        report_file = Path("memories/jules/nightly_execution.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))

        if total_success >= adjusted_target:
            logger.success(
                f"☀️ [COUNCIL] Quota reached! {total_success + existing_staged} PRs in staging for morning review."
            )
        else:
            logger.warning(
                f"☀️ [COUNCIL] Pool exhausted: {total_success}/{adjusted_target} new PRs staged "
                f"(tried {mission_index} missions, {existing_staged} already in staging)."
            )

    def _prepare_morning_brief(self, finalists: list):
        """Writes the final selection to memory for the User Interface."""
        # Import pending_manager for rejection check (optional peripheral)
        pending_manager = None
        try:
            from jules.pending_manager import pending_manager

            can_check_rejected = True
        except ImportError:
            can_check_rejected = False

        # Enrichir chaque projet avec un ID unique
        enriched = []
        skipped_rejected = 0

        for i, idea in enumerate(finalists):
            title = idea.get("title", f"Project {i + 1}")

            # IMPROVEMENT 1: Skip if already rejected
            if (
                can_check_rejected
                and pending_manager
                and pending_manager.is_rejected(title)
            ):
                logger.info(f"🌙 [COUNCIL] Skipping rejected project: {title}")
                skipped_rejected += 1
                continue

            project_id = f"project_{datetime.now().strftime('%Y%m%d')}_{i}"
            enriched.append(
                {
                    "id": project_id,
                    "index": i,
                    "title": title,
                    "description": idea.get("description", ""),
                    "source": idea.get("source", "UNKNOWN"),
                    "verdict": idea.get("verdict", ""),
                    "confidence": idea.get(
                        "confidence", 75
                    ),  # Default 75% if not provided
                    "status": "WAITING_DECISION",  # WAITING_DECISION | MERGED | PENDING | REJECTED
                }
            )

        if skipped_rejected > 0:
            logger.info(
                f"🌙 [COUNCIL] Filtered {skipped_rejected} previously rejected projects"
            )

        brief = {
            "date": datetime.now().isoformat(),
            "candidates": enriched,
            "status": "WAITING_USER_DECISION",
            "total": len(enriched),
        }

        MORNING_BRIEF_FILE.parent.mkdir(parents=True, exist_ok=True)
        MORNING_BRIEF_FILE.write_text(json.dumps(brief, indent=2, ensure_ascii=False))

        logger.success(
            f"☀️ [COUNCIL] Morning Brief prepared with {len(enriched)} candidates."
        )

        # SOTA 2026: Language-aware notification text (Standard 362.18)
        lang = get_language()
        if lang == "fr":
            text = f"☀️ **Morning Brief** ({len(enriched)} Projets)\n\n"
        else:
            text = f"☀️ **Morning Brief** ({len(enriched)} Projects)\n\n"

        for project in enriched:
            icon = "🤖" if "JULES" in project.get("source", "").upper() else "🧠"
            text += f"{project['index'] + 1}. {icon} **{project['title']}**\n"
            if project.get("description"):
                text += f"   _{project['description'][:100]}..._\n"

        if lang == "fr":
            text += "\n**Choisis une action pour chaque projet:**"
            text += "\n✅ MERGE | ⏳ ATTENTE | ❌ REFUS"
        else:
            text += "\n**Choose an action for each project:**"
            text += "\n✅ MERGE | ⏳ HOLD | ❌ REJECT"

        # Buttons structure: 3 per project (inline row)
        buttons = []
        for project in enriched:
            pid = project["id"]
            buttons.append(
                [
                    {
                        "text": f"✅ {project['index'] + 1}",
                        "data": f"JULES_MERGE_{pid}",
                    },
                    {
                        "text": f"⏳ {project['index'] + 1}",
                        "data": f"JULES_PENDING_{pid}",
                    },
                    {
                        "text": f"❌ {project['index'] + 1}",
                        "data": f"JULES_REJECT_{pid}",
                    },
                ]
            )

        logger.info(f"🔔 [NERVE] MORNING_BRIEF: {len(enriched)} projects ready")

    async def _trigger_self_evolution(self):
        """
        Weekly Self-Evolution: Jules analyzes its own code and proposes improvements.
        Proposals are saved to memories/jules/evolution_proposals.json for morning review.
        """
        logger.info("🧬 [COUNCIL] Triggering weekly self-evolution analysis...")
        try:
            from jules.self_review import JulesSelfEvolution

            result = await JulesSelfEvolution.analyze_self()
            if result and result.get("session_id"):
                logger.success(
                    f"🧬 [COUNCIL] Self-evolution session started: {result['session_id']}"
                )
            else:
                logger.warning("🧬 [COUNCIL] Self-evolution returned no session")
        except Exception as e:
            logger.error(f"🧬 [COUNCIL] Self-evolution error: {e}")


# CLI Entrypoint
if __name__ == "__main__":
    asyncio.run(NightlyCouncil().convene())
