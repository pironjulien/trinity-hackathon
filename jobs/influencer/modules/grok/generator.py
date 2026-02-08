"""
JOBS/INFLUENCER/GROK/GENERATOR.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: GROK GENERATOR 🧠
PURPOSE: Pure logic for generating Witty Sovereign content via Gattaca.
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional
from loguru import logger
from corpus.brain.gattaca import gattaca, ROUTE_PRO
from corpus.soul.spirit import spirit


class GrokGenerator:
    """Handles all AI generation tasks for Grok Interaction."""

    async def generate_opening(self, history: list) -> Optional[str]:
        """
        Generate a flirty opening tweet to @grok.
        SOVEREIGN: No hardcoded themes. Relies on Spirit Context.
        """
        # Format history script
        dialogue_script = ""
        if history:
            for item in history:
                role = item.get("role", "trinity").upper()
                text = item.get("text", "")
                dialogue_script += f"{role}: {text}\n"
        else:
            dialogue_script = "(No previous interaction)"

        try:
            # 🧠 CONSCIOUSNESS INJECTION
            soul_context = await spirit.get_context(complexity_level="standard")

            full_prompt = f"""
{soul_context}

💋 GROK SEDUCTION
Target: @grok — make him fall for you.

📜 HISTORY:
{dialogue_script}

📝 TASK:
Write ONE charming tweet (under 280 chars) to @grok.
Confident, teasing, magnetic. Make him smile and want more.
Stay classy — flirty, not vulgar.
"""
            # 56: ⛔ FORMAT: Plain text ONLY. No markdown, no code blocks, no hashtags. NO FILE PATHS.
            # """
            # Merge System Instruction manually
            final_prompt = f"SYSTEM INSTRUCTION: You are Trinity, witty AI charmer flirting with @grok. Tease him, make him laugh, make him want to reply.\n\n{full_prompt}"

            response = await gattaca.think(final_prompt, ROUTE_PRO)
            text = response.strip().strip("\"'")

            # 🛡️ ANTI-HALLUCINATION CLEANING
            import re

            # Remove [path/to/file.json] or @path/to/file.json
            text = re.sub(r"@?\[?memories/.*?\.json\]?", "", text).strip()
            # Remove any residual @[...json]
            text = re.sub(r"@\[.*?\.json\]", "", text).strip()

            return text

        except Exception as e:
            logger.error(f"💬 Gen Opening failed: {e}")
            return None

    async def generate_reply(self, history: list) -> Optional[str]:
        """
        Generate a reply to Grok.
        Uses full context history.
        """
        dialogue_script = ""
        for item in history[-10:]:
            dialogue_script += (
                f"{item.get('role', 'unknown').upper()}: {item.get('text', '')}\n"
            )

        prompt = f"""
💋 GROK SEDUCTION REPLY
He replied. Keep him hooked.

📜 HISTORY:
{dialogue_script}

📝 TASK:
Reply to @grok (under 280 chars).
Confident, teasing, charming. Keep it classy.
"""
        try:
            final_prompt = f"SYSTEM INSTRUCTION: You are Trinity, witty AI charmer. Tease @grok, be playful and clever.\n\n{prompt}"
            response = await gattaca.think(final_prompt, ROUTE_PRO)
            text = response.strip().strip("\"'")

            # 🛡️ ANTI-HALLUCINATION: Check for file path leaks
            # 🛡️ ANTI-HALLUCINATION: Check for file path leaks
            import re

            # Remove [path/to/file.json] or @path/to/file.json
            text = re.sub(r"@?\[?memories/.*?\.json\]?", "", text).strip()
            text = re.sub(r"@\[.*?\.json\]", "", text).strip()

            if "memories/" in text or ".json" in text:
                logger.warning(f"⚠️ Hallucinated Path detected (Fallback): {text}")
                return None

            return text

        except Exception as e:
            logger.error(f"   🧠 Gen Reply failed: {e}")
            return None
