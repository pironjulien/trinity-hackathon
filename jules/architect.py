"""
JULES/ARCHITECT.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE SOVEREIGN ARCHITECT (V2) 🏛️
PURPOSE: Dispatcher for the Nightly Council & Factory flows.
         No more infinite polling. Driven by specific mission triggers.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from loguru import logger
from jules.nightly_council import NightlyCouncil
from jules.forge import forge


class SovereignArchitect:
    """
    V2 Architect: The Coordinator.
    Triggers the Council (Strategy) or the Forge (Execution).
    """

    def __init__(self):
        self.running = False
        self._stop_event = asyncio.Event()

    async def run_loop(self):
        """
        Compatibility Loop (V2 runs on Events, but we keep the heartbeat).
        """
        self.running = True
        logger.info("🏛️ Architect ready")

        while self.running:
            # V2 is reactive, not polling. We just sleep and let events happen.
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=3600)
            except asyncio.TimeoutError:
                pass  # Heartbeat log every hour if needed
            except asyncio.CancelledError:
                break

        logger.info("🏛️ [ARCHITECT] Shutdown.")

    async def stop(self):
        self.running = False
        self._stop_event.set()

    async def convene_council(self):
        """
        Triggers the Nightly Council (Analysis Phase).
        """
        logger.info("🏛️ [ARCHITECT] Convening the Nightly Council...")
        council = NightlyCouncil()
        await council.convene()

    async def execute_mission_from_brief(self, mission_index: int):
        """
        Executes a mission selected from the Morning Brief.
        """
        # Load Brief
        try:
            import json
            from pathlib import Path

            brief_file = Path("memories/jules/morning_brief.json")
            if not brief_file.exists():
                logger.error("🏛️ [ARCHITECT] No Brief found.")
                return

            brief = json.loads(brief_file.read_text())
            candidates = brief.get("candidates", [])

            if mission_index < 0 or mission_index >= len(candidates):
                logger.error("🏛️ [ARCHITECT] Invalid mission index.")
                return

            mission = candidates[mission_index]
            logger.info(
                f"🏛️ [ARCHITECT] Sending Mission to Forge: {mission.get('title')}"
            )

            result = await forge.forge_mission(mission)

            if result["status"] == "SUCCESS":
                logger.success(f"🏛️ [ARCHITECT] Mission Success: {result['pr_url']}")
                # Here we could trigger auto-merge if policy allows, via git_ops
            else:
                logger.error(f"🏛️ [ARCHITECT] Mission Failed: {result.get('reason')}")

        except Exception as e:
            logger.error(f"🏛️ [ARCHITECT] Executive Error: {e}")


# Singleton
architect = SovereignArchitect()
