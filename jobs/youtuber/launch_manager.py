"""
JOBS/YOUTUBER/LAUNCH_MANAGER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: LAUNCH MANAGER 🚀
PURPOSE: Read/Write interface for launch_queue.json.
         Serves the "Next Scenario" to the Orchestrator.
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional, Dict
from loguru import logger
from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

LAUNCH_FILE = MEMORIES_DIR / "youtuber" / "data" / "launch_queue.json"


class LaunchManager:
    def __init__(self):
        self.file_path = LAUNCH_FILE

    def get_next_scenario(self) -> Optional[Dict]:
        """
        Retrieves the next scenario based on 'current_day'.
        Returns None if queue is finished or empty.
        """
        data = load_json(self.file_path)
        if not data:
            logger.error(f"❌ [LAUNCH] Could not load {self.file_path}")
            return None

        queue = data.get("launch_queue", [])
        current_day = data.get("current_day", 0)

        # Find the scenario for the current day
        scenario = next((item for item in queue if item["day"] == current_day), None)

        if scenario:
            logger.info(
                f"🚀 [LAUNCH] Found scenario Day {current_day}: {scenario.get('topic')}"
            )
            return scenario
        else:
            logger.info(
                f"✨ [LAUNCH] No scenario found for Day {current_day} (End of Queue?)"
            )
            return None

    def advance_day(self):
        """
        Increments current_day in launch_queue.json.
        Should be called AFTER successful production/scheduling.
        """
        data = load_json(self.file_path)
        if data:
            data["current_day"] = data.get("current_day", 0) + 1
            save_json(self.file_path, data)
            logger.success(f"📅 [LAUNCH] Advanced to Day {data['current_day']}")


# Singleton
launch_manager = LaunchManager()
