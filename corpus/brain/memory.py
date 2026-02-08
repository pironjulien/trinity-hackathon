"""
CORPUS/BRAIN/MEMORY.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: UNIFIED MEMORY (LA MÉMOIRE) 💾
PURPOSE: Façade unique pour Hippocampus (STM) et Synapse (LTM).
══════════════════════════════════════════════════════════════════════════════
"""

import uuid
from typing import Any, List, Dict, Optional
from loguru import logger

from corpus.brain.hippocampus import stm
from corpus.brain.engram import ltm


class UnifiedMemory:
    """
    Façade de Mémoire SOTA.
    Abstrait la complexité SQL vs Vectoriel.
    """

    def __init__(self):
        self.is_ready = False

    async def initialize(self):
        """Boot sequence for memories."""
        await stm.initialize()
        await ltm.initialize()
        self.is_ready = True

    async def remember(
        self,
        key: str,
        value: Any,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ):
        """
        Stocke une information.
        - STM (Always): Stockage rapide/exact state.
        - LTM (If Important): Vectorisation pour le contexte futur.
        """
        # Always STM (Exact Recall)
        await stm.remember(key, value)

        # LTM (Semantic Recall)
        if importance > 0.7 and isinstance(value, str):
            mem_id = f"{key}_{uuid.uuid4().hex[:8]}"
            import time

            metadata = {
                "source": "memory",
                "importance": importance,
                "tags": ",".join(tags or []),
                "original_key": key,
                "timestamp": time.time(),
            }
            logger.debug(f"💾 [MEMORY] Crystallizing to LTM: {key}")
            await ltm.memorize(value, metadata, mem_id)

    async def recall(self, query: str, mode: str = "hybrid") -> Dict[str, Any]:
        """
        Retrieves une information contextuelle.
        Modes:
        - "exact": STM only (Key lookup)
        - "semantic": LTM only (Search)
        - "hybrid": Both
        """
        result = {"exact": None, "related": []}

        # 1. STM Lookup (Exact Key)
        if mode in ["exact", "hybrid"]:
            stm_res = await stm.recall(query)
            if stm_res:
                result["exact"] = stm_res

        # 2. LTM Search (Semantic)
        if mode in ["semantic", "hybrid"]:
            ltm_res = await ltm.recall(query)
            result["related"] = ltm_res

        return result

    async def close(self):
        """Shutdown memory subsystems."""
        # STM (SQLite) manages connections per-query
        # LTM (Chroma) client handles its own lifecycle
        self.is_ready = False
        logger.info("💾 [MEMORY] Shutdown complete.")


# Singleton
memory = UnifiedMemory()
