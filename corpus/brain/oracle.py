"""
CORPUS/BRAIN/ORACLE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ORACLE OF ANTITHESIS (L'ORACLE DE L'ANTITHÈSE) 🔮
PURPOSE: Systematic Red Teaming & Cognitive Immunity.
         Simulates failure scenarios and provides radical counter-arguments.
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime
from typing import Dict, Optional, List
from loguru import logger

from corpus.brain.gattaca import gattaca, ROUTE_PRO


class AntithesisOracle:
    """
    The Oracle of Antithesis.
    A module designed to provide cognitive immunity by simulating failure
    scenarios (Red Teaming) and offering radical counter-arguments.
    """

    def __init__(self):
        """Initialize the Oracle."""
        self.history: List[Dict] = []

    async def generate_red_team_report(
        self, project_name: str, description: str, context: Optional[str] = None
    ) -> Dict:
        """
        Generates a comprehensive Red Teaming report for a given project.

        Args:
            project_name: The name of the project.
            description: A detailed description of the project.
            context: Optional technical or strategic context.

        Returns:
            A dictionary containing the parsed report sections.
        """
        logger.info(f"🔮 [ORACLE] Initiating Red Team analysis for: {project_name}")

        full_context = f"""
        PROJECT NAME: {project_name}
        DESCRIPTION: {description}
        CONTEXT: {context or "No additional context provided."}
        """

        prompt = f"""
=== MISSION: THE ORACLE OF ANTITHESIS ===
You are the "Red Teamer" for the Trinity system. Your goal is NOT to be helpful, but to be CRITICAL, RUTHLESS, and ANALYTICAL.
You must simulate why this project will FAIL. You must provide the "Antithesis" to the user's "Thesis".

INPUT DATA:
{full_context}

TASK:
Analyze the project above and generate a Red Team Report with the following strictly formatted sections:

1. FAILURE_MODES: List specific, catastrophic ways this project could fail (Technical, Strategic, or Ethical).
2. DEVIL_ADVOCATE: Provide radical counter-arguments. Why should this project NOT exist?
3. BLIND_SPOTS: What is the user/team ignoring? (Dependencies, edge cases, costs).
4. VERDICT: A harsh but fair conclusion (GO, NO-GO, or PIVOT).

FORMAT REQUIREMENT:
Use the following separators for your response:
---FAILURE_MODES---
(Content)
---DEVIL_ADVOCATE---
(Content)
---BLIND_SPOTS---
(Content)
---VERDICT---
(Content)
"""

        try:
            # Use ROUTE_PRO (Reasoning / Gemini 3 Pro) for maximum critical analysis depth
            response = await gattaca.route(prompt, route_id=ROUTE_PRO)

            report = {
                "timestamp": datetime.now().isoformat(),
                "project_name": project_name,
                "failure_modes": self._parse_section(response, "FAILURE_MODES"),
                "devil_advocate": self._parse_section(response, "DEVIL_ADVOCATE"),
                "blind_spots": self._parse_section(response, "BLIND_SPOTS"),
                "verdict": self._parse_section(response, "VERDICT"),
                "raw_output": response,
            }

            self.history.append(report)
            logger.success(f"🔮 [ORACLE] Report generated for {project_name}")
            return report

        except Exception as e:
            logger.error(f"💥 [ORACLE] Analysis failed: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "project_name": project_name,
            }

    def _parse_section(self, text: str, section_name: str) -> str:
        """
        Robustly extracts a section from the AI response.

        Args:
            text: The full text response.
            section_name: The name of the section (without dashes).

        Returns:
            The content of the section, or empty string if not found.
        """
        try:
            marker = f"---{section_name}---"
            if marker in text:
                start = text.index(marker) + len(marker)
                # Find the next marker or end of string
                next_marker_idx = -1

                # Simple heuristic: look for next "---"
                possible_next = text.find("---", start + 1)
                if possible_next != -1:
                    next_marker_idx = possible_next

                if next_marker_idx > 0:
                    return text[start:next_marker_idx].strip()
                return text[start:].strip()
        except Exception:
            pass
        return ""

# Singleton Instance
oracle = AntithesisOracle()
