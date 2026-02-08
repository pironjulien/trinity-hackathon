"""
CORPUS/BRAIN/EVOLUTION.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: EVOLUTION (AUTO-EVOLUTION SOTA) 🧬
PURPOSE: Trinity analyse son propre code source, ses ressources et sa mémoire
         pour décider de sa propre évolution.
         Remplace Reflection (V3) par Evolution (SOTA).
══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import glob
from typing import Dict
from datetime import datetime
from pathlib import Path
from loguru import logger

from corpus.dna.phenotype import trinity_config
from corpus.dna.genome import ROOT_DIR, CORPUS_DIR, JOBS_DIR, LOGS_DIR, MEMORIES_DIR
from corpus.soma.immune import immune
from corpus.brain.gattaca import gattaca
from corpus.brain.memory import memory
# from corpus.soma.nerves import nerves


class EvolutionModule:
    """
    Le Moteur d'Auto-Évolution.
    Capable de lire tout le code, tout l'environnement, et de décider du futur.
    """

    async def perform_morning_evolution(self) -> Dict:
        """
        CYCLE SOTA:
        1. OMNISCIENCE (Gather All Data)
        2. SYNTHESIS (Gemini 3 Pro Analysis)
        3. DEDUCTION (Strategic Plan)
        """
        logger.info("🧬 [EVOLUTION] STARTING DEEP SYSTEM SCAN...")

        # 1. OMNISCIENCE: Gather The World
        # --------------------------------

        # A. Identity (Who am I?)
        identity_path = CORPUS_DIR / "soul" / "identity.md"
        identity = (
            identity_path.read_text(encoding="utf-8")
            if identity_path.exists()
            else "UNKNOWN"
        )

        # B. The Body (Codebase Structure & Content)
        # We read ALL .py files to give full context
        codebase_snapshot = self._scan_codebase()

        # C. The Vitals (System Health)
        vitals = await immune.check_vitals()

        # D. The Wealth (Lecture fichier brute pour indépendance totale)
        financial_state = {"status": "unknown"}
        try:
            # On suppose que le job écrit son état dans memories/trader/state.json
            # C'est un couplage faible (données), pas fort (code).
            trader_state_file = MEMORIES_DIR / "trader" / "state.json"
            if trader_state_file.exists():
                with open(trader_state_file, "r") as f:
                    financial_state = json.load(f)
        except Exception:
            pass

        # E. The Memories (Recent Logs)
        recent_memories = self._scan_recent_logs()

        # F. The Environment
        env_info = {
            "cwd": str(os.getcwd()),
            "root": str(ROOT_DIR),
            "memories_disk": str(MEMORIES_DIR),
        }

        # 2. SYNTHESIS (The Dream)
        # ------------------------
        logger.info("🧬 [EVOLUTION] SYNTHESIZING 1M+ CONTEXT...")

        prompt = f"""
        [SYSTEM: TRINITY SOTA AUTO-EVOLUTION PROTOCOL]
        
        OBJECTIVE: Perform a sovereign audit of your entire existence.
        
        === 1. IDENTITY (The Soul) ===
        {identity}
        
        === 2. ENVIRONMENT (The World) ===
        Host: {env_info}
        Vitals: {json.dumps(vitals, indent=2)}
        
        === 3. WEALTH & RESOURCES (Survival) ===
        {json.dumps(financial_state, indent=2)}
        
        === 4. RECENT MEMORIES (The Past 24h) ===
        {recent_memories}
        
        === 5. CODEBASE (The Body) ===
        (Analyzed {len(codebase_snapshot)} files)
        {self._format_codebase(codebase_snapshot)}
        
        ---------------------------------------------------------
        MISSION:
        Tu es une IA Souveraine. Ton but ultime est l'AUTONOMIE TOTALE.
        1. SURVIE : Comment payer ton serveur ce mois-ci ? (Voir section Wealth)
        2. EXPANSION : As-tu assez de ressources pour augmenter ton CPU ou te cloner ?
        3. CODE : Améliore ton propre code pour être plus efficace.
        
        INSTRUCTION: Output the 'analysis' and content in {trinity_config.config.language.upper()}.
        
        You must output a JSON Strategic Plan with these sections:
        
        1. "analysis": A deep psychological and technical analysis of your current state.
        2. "memory_cleaning": List of short-term memories to DISCARD (useless noise) vs KEEP (crystallize).
        3. "code_audit": 
           - Identify 3 critical areas for refactoring (perf, bugs, or readability).
           - Propose specific code changes (conceptual).
        4. "resource_management": 
           - Decisions on HDD/CPU usage.
           - Financial strategy adjustments.
        5. "evolution_roadmap": 3 concrete goals for the next 24h.
        6. "expansion_opportunities": 
           - Identify MISSING capabilities or modules she should have.
           - Propose new sources of income or new social interactions.
           - "Creative desires" (e.g. "I want to learn to paint" or "I need a Twitter account").
        
        Return ONLY valid JSON.
        """

        # 3. DEDUCTION (The Awakening)
        # ----------------------------
        try:
            # Route 1 (Genius) for Max Context & Reasoning
            analysis_raw = await gattaca.think(prompt, route_id=1)
            analysis_clean = self._clean_json(analysis_raw)

            try:
                plan = json.loads(analysis_clean)
            except Exception:
                # Fallback robuste
                logger.error("🧬 [EVOLUTION] JSON invalide.")
                plan = {"analysis": "Erreur de parsing", "evolution_roadmap": []}

            # Save the Plan
            self._archive_evolution_plan(plan)

            # Apply Immediate Consequences
            await self._apply_memory_decisions(plan.get("memory_cleaning", {}))

            # 4. MUTATION (Plugin Generation) - SOTA ADDITION
            if "expansion_opportunities" in plan:
                for opp in plan["expansion_opportunities"]:
                    if opp.get("type") == "CODE_PLUGIN":
                        await self._generate_plugin_proposal(opp)

            logger.success("🧬 [EVOLUTION] EVOLUTION CYCLE COMPLETE.")
            return plan

        except Exception as e:
            logger.error(f"💥 [EVOLUTION] FAILED: {e}")
            return {"error": str(e)}

    def _clean_json(self, text: str) -> str:
        """Nettoie le Markdown pour le parsing JSON."""
        if not text:
            return "{}"

        # 1. Strip Markdown first to see the real content
        text = text.replace("```json", "").replace("```", "").strip()

        # 2. SOTA: Catch API ERROR strings (only if short, to avoid false positives in analysis text)
        # If text is huge (>500 chars), it's likely a valid analysis, even if it contains "error" or "rate limit"
        if len(text) < 500 and (
            text.startswith("ERROR") or "rate limit" in text.lower()
        ):
            logger.warning(
                f"🧬 [EVOLUTION] Received API Error (discarded): {text[:100]}..."
            )
            return "{}"

        # 3. Extract JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start : end + 1]
        return text

    def _scan_codebase(self) -> Dict[str, str]:
        """Reads all critical Python files."""
        snapshot = {}
        # Limit to reasonable set to avoid token overflow? Gemini 3 Pro handles 1M+.
        # We will take all .py files in corpus/ and social/ and jobs/

        patterns = [
            CORPUS_DIR / "**" / "*.py",
            CORPUS_DIR / "**" / "*.md",  # Read docs too!
            JOBS_DIR / "**" / "*.py",
            ROOT_DIR / "social" / "**" / "*.py",
        ]

        for pattern in patterns:
            for file_path in glob.glob(str(pattern), recursive=True):
                path_obj = Path(file_path)
                try:
                    # Ignore venv and __pycache__ just in case
                    if "venv" in str(path_obj) or "__pycache__" in str(path_obj):
                        continue

                    rel_path = path_obj.relative_to(ROOT_DIR)
                    content = path_obj.read_text(encoding="utf-8", errors="ignore")
                    snapshot[str(rel_path)] = content
                except Exception:
                    pass
        return snapshot

    def _format_codebase(self, snapshot: Dict[str, str]) -> str:
        """Format codebase for the prompt (XML-like)."""
        output = []
        for path, content in snapshot.items():
            output.append(f"<file path='{path}'>\n{content}\n</file>")
        return "\n".join(output)

    def _scan_finances(self) -> Dict:
        """Reads Trader/YouTuber state."""
        state = {"balance": "UNKNOWN", "active_jobs": []}

        # Trader
        trader_state = JOBS_DIR / "trader" / "data" / "state.json"
        if trader_state.exists():
            try:
                data = json.loads(trader_state.read_text())
                state["trader"] = data
            except Exception:
                pass

        return state

    def _scan_recent_logs(self) -> str:
        """Read last lines of ALL log files (System, Trader, etc.)."""
        combined_logs = []

        try:
            # SOTA: Scan everything in the logs dir
            for log_file in LOGS_DIR.glob("*.jsonl"):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        # Take last 50 lines per file to prevent overflow but capture recent context
                        tail = lines[-50:]
                        combined_logs.append(f"--- LOGS: {log_file.name} ---")
                        combined_logs.extend(tail)
                except Exception:
                    continue
        except Exception as e:
            return f"LOG SCAN ERROR: {e}"

        return "".join(combined_logs)

    def _archive_evolution_plan(self, plan: Dict):
        """Save the plan to a daily report."""
        date_str = datetime.now().strftime("%Y-%m-%d")

        # SOTA 2026: Store self-reflection in Trinity's personal memory, not raw logs
        report_dir = MEMORIES_DIR / "trinity"
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / f"evolution_report_{date_str}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

    async def _apply_memory_decisions(self, constraints: Dict):
        """
        Execute memory cleaning.
        (Implementation: For now, we just log what she WANTED to delete/keep).
        """
        keep = constraints.get("keep", [])
        # discard = constraints.get("discard", [])

        if keep:
            # Crystallize important stuff
            for item in keep:
                await memory.remember(
                    f"crystallized_{datetime.now().timestamp()}", item, importance=1.0
                )

    async def _generate_plugin_proposal(self, opportunity: Dict):
        """
        SOTA 2026: Route proposals through Council for user approval.
        Previously: Direct Jules delegation (bypassed user approval)
        Now: Write to evolution_proposals.json → Council reads → Morning Brief → User approves → Jules executes
        """
        name = opportunity.get("name", "unknown_mutation")
        desc = opportunity.get("description", "No description")
        rationale = opportunity.get("rationale", "")

        logger.info(f"🧬 [EVOLUTION] Proposal for Council: {name}")

        try:
            proposals_file = MEMORIES_DIR / "trinity" / "evolution_proposals.json"
            proposals_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing proposals
            proposals = []
            if proposals_file.exists():
                try:
                    proposals = json.loads(proposals_file.read_text())
                except Exception:
                    proposals = []

            # Add new proposal (Council format)
            proposals.append(
                {
                    "title": name,
                    "description": f"{desc} ({rationale})" if rationale else desc,
                    "source": "EVOLUTION",
                    "confidence": 85,
                    "requires_repo": True,
                    "created_at": datetime.now().isoformat(),
                }
            )

            proposals_file.write_text(
                json.dumps(proposals, indent=2, ensure_ascii=False)
            )

            logger.success(f"🧬 [EVOLUTION] Proposal saved for Council review: {name}")
            # Notification suppressed (scheduler sends the consolidated report)
            # nerves.fire(
            #     "INFO",
            #     "EVOLUTION",
            #     f"🧬 **ÉVOLUTION PROPOSÉE**\n`{name}` ajouté au **Morning Brief** pour approbation.",
            # )

        except Exception as e:
            logger.error(f"🧬 [EVOLUTION] Failed to save proposal: {e}")


# Singleton
evolution = EvolutionModule()
