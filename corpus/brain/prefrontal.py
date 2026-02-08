"""
CORPUS/BRAIN/STRATEGIST.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TRINITY STRATEGIST 🧠
PURPOSE: Deep analysis of the codebase to generate pragmatic project proposals.
         This is the "Insider" view of the Nightly Council.
══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
from loguru import logger
from datetime import datetime
from corpus.brain.gattaca import gattaca


class TrinityStrategist:
    """
    The Strategic Brain of Trinity.
    Analyzes the 'Corpus' (Codebase) to find structural improvements,
    technical debt, or missing features.
    """

    async def analyze_and_propose(self, limit: int = 5) -> list[dict]:
        """
        Scans the codebase and returns a list of Project Proposals.
        """
        logger.info("🧠 [STRATEGIST] Starting deep codebase analysis...")

        # 1. GATHER CONTEXT
        # We scan the structure to give Gattaca a map of the territory.
        structure_summary = self._scan_structure()

        # 2. ASK GATTACA (The LLM)
        # We ask specific strategic questions.
        prompt = f"""
        Tu es TRINITY, l'Architecte de ce système.
        
        CARTOGRAPHIE DU SYSTÈME ACTUEL :
        {structure_summary}
        
        TA MISSION :
        Identifie 5 chantiers stratégiques (Projets) pour améliorer le système.
        Concentre-toi sur :
        1. La robustesse (Error handling, typage)
        2. La sécurité (Sanitization, Auth)
        3. L'observabilité (Logs, Metrics)
        4. L'extension (Nouveaux modules logiques)
        
        RÈGLES :
        - Sois pragmatique. Pas de réécriture totale.
        - Des projets finissables en 1 jour (~100 appels API).
        
        FORMAT DE RÉPONSE ATTENDU (JSON list) :
        [
            {{
                "title": "Nom du Projet (ex: Refonte Auth)",
                "description": "Description détaillée...",
                "rationale": "Pourquoi c'est vital maintenat",
                "files_to_touch": ["fichier1.py", "dossier/"]
            }}
        ]
        """

        try:
            # Use PRO route for strategic analysis
            response = await gattaca.route(
                prompt=prompt,
                route_id=gattaca.ROUTE_PRO,
            )

            # Parse JSON response from Gattaca (may be wrapped in markdown code block)
            import json
            import re

            text = response if isinstance(response, str) else str(response)
            # Extract JSON from markdown code block if present
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()
            proposals = json.loads(text)

            if isinstance(proposals, list):
                # Enrich with Metadata
                for p in proposals:
                    p["source"] = "TRINITY_STRATEGIST"
                    p["confidence"] = 90  # Trinity trusts herself
                    p["created_at"] = datetime.now().isoformat()

                logger.success(f"🧠 [STRATEGIST] Generated {len(proposals)} proposals.")
                return proposals[:limit]

            return []

        except Exception as e:
            logger.error(f"🧠 [STRATEGIST] Analysis failed: {e}")
            return []

    def _scan_structure(self) -> str:
        """Generates a summary of the file tree for context."""
        summary = ""
        roots = [Path("corpus"), Path("jules"), Path("jobs")]

        for root in roots:
            if not root.exists():
                continue
            summary += f"\n--- {root}/ ---\n"
            # Get Python files only, usually enough for architecture map
            for path in root.rglob("*.py"):
                # Skip deep nesting or tests for the high level map
                if "tests" in str(path) or "__pycache__" in str(path):
                    continue

                # Check file size/complexity heuristic
                size = path.stat().st_size
                summary += f"- {path} ({size} bytes)\n"

                # Peek at headers (first 5 lines) to capture Docstrings/Purpose
                try:
                    with open(path, "r") as f:
                        head = [next(f) for _ in range(5)]
                        doc = "".join(head).strip()
                        summary += f"  Context: {doc[:100]}...\n"
                except Exception:
                    pass

        return summary
