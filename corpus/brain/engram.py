"""
CORPUS/BRAIN/ENGRAM.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ENGRAM (SYNAPSE) 🕸️
PURPOSE: Stockage Vectoriel (ChromaDB).
USAGE: Souvenirs sémantiques, apprentissage, patterns.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import chromadb
from pathlib import Path
from loguru import logger
from typing import List, Dict, Any

from corpus.dna.genome import BRAIN_MEMORY_VECTOR_DIR


class LongTermMemory:
    """
    La Synapse V3 (ChromaDB).
    Gère le stockage vectoriel pour la recherche sémantique.
    """

    def __init__(self, persistence_path: str = str(BRAIN_MEMORY_VECTOR_DIR)):
        self.path = persistence_path
        self.client = None
        self.collection = None

    async def initialize(self):
        """Initialise ChromaDB."""
        try:
            # Ensure directory exists
            if not Path(self.path).exists():
                Path(self.path).mkdir(parents=True, exist_ok=True)

            # Check Permissions BEFORE Init
            if Path(self.path).exists():
                import os

                if not os.access(self.path, os.W_OK):
                    logger.warning(f"🕸️ [LTM] Read-Only: {self.path}")
                    try:
                        # Try to fix ownership/permissions if we own it
                        os.chmod(self.path, 0o755)
                    except Exception:
                        pass  # Fail silently, let the detailed error handler catch it

            self.client = chromadb.PersistentClient(path=self.path)
            self.collection = self.client.get_or_create_collection(
                name="trinity_memories", metadata={"hnsw:space": "cosine"}
            )
            logger.info("🕸️ LTM ready")
        except Exception as e:
            err_str = str(e).lower()
            if "readonly" in err_str or "permission" in err_str:
                cmd_fix = f"sudo chown -R $USER:$USER {Path(self.path).parent.parent}"  # Target memories/trinity
                logger.critical(f"🕸️ [LTM] FATAL: Read-Only\n👉 {cmd_fix}")
                # Don't silence the error, but make the fix obvious
            logger.error(f"🕸️ [LTM] Init Fail: {e}")

    async def memorize(
        self, text: str, metadata: Dict[str, Any], memory_id: str
    ) -> bool:
        """Ajoute un souvenir vectoriel."""
        if not self.collection:
            return False
        try:
            await asyncio.to_thread(
                self.collection.add,
                documents=[text],
                metadatas=[metadata],
                ids=[memory_id],
            )
            return True
        except Exception as e:
            logger.error(f"🕸️ [LTM] Save Fail: {e}")
            return False

    async def recall(self, query: str, n_results: int = 3) -> List[Dict]:
        """
        Recherche sémantique avec Recency Weighting.
        Score = (Similarity * 0.7) + (Recency * 0.3)
        """
        if not self.collection:
            return []
        try:
            # 1. Fetch more candidates (Recency needs a candidate pool)
            candidates_count = max(10, n_results * 2)

            results = self.collection.query(
                query_texts=[query], n_results=candidates_count
            )

            if not results["documents"]:
                return []

            # 2. Score Candidates
            import time
            import math

            current_time = time.time()
            candidates = []

            # Unpack ChromaDB structure (arrays of arrays)
            if not results["ids"] or not results["ids"][0]:
                return []
            
            ids = results["ids"][0]
            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][
                0
            ] if results["distances"] else []

            for i, doc_id in enumerate(ids):
                # A. Similarity Score (Normalize distance 0-2 -> 1-0)
                # We want 1.0 for close, 0.0 for far.
                dist = distances[i]
                sim_score = max(
                    0.0, 1.0 - (dist / 2.0)
                )  # Rough approximation for Cosine Distance

                # B. Recency Score
                meta = metas[i]
                timestamp = meta.get("timestamp")

                recency_score = 0.5  # Neutral fallback
                if timestamp:
                    try:
                        elapsed_seconds = current_time - float(str(timestamp))
                        elapsed_days = elapsed_seconds / 86400.0
                        # Decay Formula: 1 / (1 + decay * days)
                        # Start at 1.0.
                        # At 30 days => 0.5? -> decay ~ 0.03
                        # Let's be closer to "Bitcoin 90k" vs "20k in 2022"
                        # 2022 is 1000+ days ago. 1000 days => score ~ 0.0.
                        # Yesterday (1 day) => score ~ 0.99.
                        # Use Exponential Decay for sharper falloff?
                        # recency = exp(-0.01 * days) -> 100 days = 0.36. 365 days = 0.02.
                        recency_score = math.exp(-0.01 * max(0, elapsed_days))
                    except (ValueError, TypeError):
                        pass

                # C. Combined Score
                # Weighted: 70% Semantic, 30% Recency
                final_score = (sim_score * 0.7) + (recency_score * 0.3)

                candidates.append(
                    {
                        "text": docs[i],
                        "meta": meta,
                        "score": final_score,
                        "debug": f"Sim:{sim_score:.2f} Rec:{recency_score:.2f}",
                    }
                )

            # 3. Sort by Final Score Descending
            candidates.sort(key=lambda x: x["score"], reverse=True)

            # 4. Return top N
            final_memories = candidates[:n_results]

            # Log for debug
            if final_memories:
                logger.debug(f"🕸️ [LTM] Recall Top 1: {final_memories[0]['debug']}")

            return final_memories

        except Exception as e:
            logger.error(f"🕸️ [LTM] Recall Fail: {e}")
            return []


# Singleton
ltm = LongTermMemory()
