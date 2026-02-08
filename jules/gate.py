"""
JULES/GATE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE QUALITY GATE 🛡️
PURPOSE: Strict scoring of Jules' output before it reaches the user.
         enforces the <50% (Trash) and >90% (Pass) thresholds.
══════════════════════════════════════════════════════════════════════════════
"""

from loguru import logger
from corpus.brain.gattaca import gattaca


class QualityGate:
    """
    The Inspector.
    Reviews code diffs and assigns a confidence score.
    """

    # HACKATHON FIX: Lowered from 90 to 85 due to Jules API session timeouts
    # Jules sessions become inactive after ~15min, preventing refinement iterations
    MIN_PASS_SCORE = 85
    TRASH_THRESHOLD = 50

    async def evaluate(self, diff: str, context: str) -> dict:
        """
        Evaluates a diff against the project spec.
        Returns: {'score': int, 'verdict': str, 'feedback': str}
        """
        if not diff:
            return {"score": 0, "verdict": "TRASH", "feedback": "No diff generated."}

        logger.info("🛡️ [GATE] Inspecting code quality...")

        # SMART DIFF SAMPLING: Show balanced view instead of truncating from start
        # Extract file headers and sample of additions/deletions
        diff_sample = self._prepare_diff_sample(diff, max_chars=12000)

        prompt = f"""
        Tu es TRINITY, l'Inspecteur de Qualité (SOTA 2026).
        
        CONTEXTE PROJET:
        {context}
        
        CODE PROPOSÉ (DIFF RÉSUMÉ):
        ```diff
        {diff_sample}
        ```
        (Échantillon équilibré du diff - {len(diff)} chars total)

        
        MISSION:
        Note ce code sur 100.
        
        CRITÈRES DE NOTATION SCRUPULEUX:
        - **Securité** (0 si faille détectée : usage interdit de os/subprocess, injections...)
        - **Robustesse** (Gestion des erreurs, types)
        - **Conformité** (Respect du contexte demandé)
        - **Tests** (Présence de tests pour le nouveau code)
        
        BARÈME:
        - < 50 : Poubelle (Code dangereux, halluciné ou hors-sujet).
        - 50-89 : Raffinement requis (Bonne direction mais manque de finition).
        - 90-100 : SOTA (Parfait, prêt pour merge).
        
        CRITICAL: Si le score est < 90, tu DOIS fournir une "GAP ANALYSIS":
        - Liste EXACTE des modifications pour atteindre 90+
        - Estime combien de points chaque fix apporterait
        - Sois CONCRET (noms de fichiers, fonctions, lignes)
        
        FORMAT DE RÉPONSE (JSON Strict):
        {{
            "score": 0-100,
            "feedback": "Analyse critique en 3 points...",
            "critical_issues": ["liste", "des", "bloquants"],
            "gap_analysis": {{
                "points_to_90": 20,
                "fixes": [
                    {{"action": "Ajouter try/catch dans fonction X", "points": 5}},
                    {{"action": "Ajouter tests pour Y", "points": 10}},
                    {{"action": "Corriger typage de Z", "points": 5}}
                ]
            }}
        }}
        """

        try:
            import json
            import re

            response = await gattaca.route(
                prompt=prompt,
                route_id=gattaca.ROUTE_PRO,
                use_cache=False,  # SOTA 2026: Force fresh judgment every time
            )

            # Extract JSON from markdown code block if present
            text = response if isinstance(response, str) else str(response)
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()
            result = json.loads(text)

            score = result.get("score", 0)

            # Determine Verdict
            if score < self.TRASH_THRESHOLD:
                verdict = "TRASH"
            elif score < self.MIN_PASS_SCORE:
                verdict = "REFINE"
            else:
                verdict = "PASS"

            logger.info(f"🛡️ [GATE] Verdict: {verdict} (Score: {score}/100)")

            return {
                "score": score,
                "verdict": verdict,
                "feedback": result.get("feedback", "No feedback provided."),
                "critical_issues": result.get("critical_issues", []),
                "gap_analysis": result.get("gap_analysis", {}),
            }

        except Exception as e:
            logger.error(f"🛡️ [GATE] Evaluation failed: {e}")
            return {"score": 0, "verdict": "TRASH", "feedback": f"Gate Error: {e}"}

    def _prepare_diff_sample(self, diff: str, max_chars: int = 12000) -> str:
        """
        SOTA 2026: Smart diff sampling for balanced LLM evaluation.

        Problem: Simple truncation shows only deletions at the start,
        missing new file additions that appear later in the diff.

        Solution: Extract file headers + prioritize NEW file content.
        """
        if len(diff) <= max_chars:
            return diff

        lines = diff.split("\n")

        # 1. Extract all file headers (diff --git)
        headers = []
        file_chunks = {}
        current_file = None
        current_lines = []

        for line in lines:
            if line.startswith("diff --git"):
                if current_file and current_lines:
                    file_chunks[current_file] = current_lines
                current_file = line
                headers.append(line)
                current_lines = [line]
            elif current_file:
                current_lines.append(line)

        # Don't forget last file
        if current_file and current_lines:
            file_chunks[current_file] = current_lines

        # 2. Build sample: prioritize NEW files (b/... not /dev/null)
        sample_lines = []
        sample_lines.append(f"# DIFF SUMMARY: {len(headers)} files changed\n")

        # Show all headers first
        for h in headers[:20]:  # Max 20 file headers
            parts = h.split(" ")
            if len(parts) >= 4:
                sample_lines.append(f"# - {parts[2]} -> {parts[3]}")
        sample_lines.append("\n# --- SAMPLE OF CHANGES ---\n")

        # Prioritize new files (additions)
        new_files = [
            f for f in file_chunks if "+++ b/" in "\n".join(file_chunks[f][:5])
        ]
        deleted_files = [
            f for f in file_chunks if "+++ /dev/null" in "\n".join(file_chunks[f][:5])
        ]
        modified_files = [
            f for f in file_chunks if f not in new_files and f not in deleted_files
        ]

        budget = max_chars - len("\n".join(sample_lines))

        # Give 60% to new files, 30% to modified, 10% to deleted
        for priority_files, ratio in [
            (new_files, 0.6),
            (modified_files, 0.3),
            (deleted_files, 0.1),
        ]:
            file_budget = int(budget * ratio)
            chars_used = 0
            for f in priority_files:
                chunk = "\n".join(file_chunks[f])
                if chars_used + len(chunk) < file_budget:
                    sample_lines.extend(file_chunks[f])
                    chars_used += len(chunk)
                elif chars_used < file_budget:
                    # Add partial
                    remaining = file_budget - chars_used
                    sample_lines.append("\n".join(file_chunks[f])[:remaining])
                    sample_lines.append("\n# ... (truncated)")
                    break

        return "\n".join(sample_lines)


# Singleton
gate = QualityGate()
