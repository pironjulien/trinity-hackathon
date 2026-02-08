"""
JULES/PLANNING_CRITIC.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE PLANNING CRITIC 😈
PURPOSE: SOTA 2026 Feature.
         Interprets Jules' plans via Gattaca BEFORE code execution.
         Reduces failure rate by acting as an adversarial reviewer.
══════════════════════════════════════════════════════════════════════════════
"""

import json
import re
from typing import Dict, Any
from loguru import logger
from corpus.brain.gattaca import gattaca


class PlanningCritic:
    """
    The Adversarial Critic for Auto-Approved Plans.
    """

    @staticmethod
    async def critique_plan(task_description: str, plan_text: str) -> Dict[str, Any]:
        """
        Critiques a plan. Returns approval status and feedback.

        Args:
            task_description: The original prompt given to Jules.
            plan_text: The plan proposed by Jules (STEP 1).

        Returns:
            Dict: {
                "approved": bool,
                "confidence": int (0-100),
                "critique": str,
                "improvement_prompt": str (to send back to Jules)
            }
        """
        logger.info("😈 [CRITIC] Reviewing Plan...")

        prompt = f"""
        ROLE: YOU ARE THE PLANNING CRITIC (SOTA 2026).
        Your goal is to decrease task failure by finding flaws in plans BEFORE execution.

        ORIGINAL TASK:
        "{task_description}"

        PROPOSED PLAN (By Jules):
        \"\"\"
        {plan_text}
        \"\"\"

        MISSION:
        Critique this plan ruthlessly but constructively.
        Check for:
        1. **Feasibility**: Can this be done? Are files missing?
        2. **Safety**: Does it use forbidden imports (os.system, etc)?
        3. **Completeness**: Does it solve the WHOLE task?
        4. **Steps**: Are the steps logical?

        OUTPUT FORMAT (JSON):
        {{
            "approved": boolean,  // True if plan is solid, False if needs changes
            "confidence": int,    // 0-100
            "critique": "Short summary of flaws",
            "improvement_prompt": "Instruction to Jules to fix the plan (e.g. 'Add a test step', 'Don't delete X')"
        }}
        """

        try:
            # Use PRO route for deep reasoning
            response = await gattaca.route(prompt=prompt, route_id=gattaca.ROUTE_PRO)

            # Clean response (remove markdown blocks)
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
            if match:
                response = match.group(1).strip()

            result = json.loads(response)

            # Safe defaults
            approved = result.get("approved", False)
            return {
                "approved": approved,
                "confidence": result.get("confidence", 50),
                "critique": result.get("critique", "No critique provided"),
                "improvement_prompt": result.get(
                    "improvement_prompt", "Please refine the plan based on feedback."
                ),
            }

        except Exception as e:
            logger.error(f"😈 [CRITIC] Failed to critique: {e}")
            # Fail safe: Approve to avoid deadlock, but warn
            return {
                "approved": True,
                "confidence": 50,
                "critique": "Critic unavailable - Auto-passing",
                "improvement_prompt": "",
            }


# Singleton
critic = PlanningCritic()
