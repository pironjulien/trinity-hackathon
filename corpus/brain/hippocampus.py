"""
CORPUS/BRAIN/HIPPOCAMPUS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SHORT-TERM MEMORY (HIPPOCAMPUS) ⚡
PURPOSE: Stockage Rapide & Persistant (SQLite Async).
USAGE: État du système, contexte immédiat, files d'attente.
══════════════════════════════════════════════════════════════════════════════
"""

import aiosqlite
import json
from typing import Any
from loguru import logger
from corpus.dna.genome import BRAIN_MEMORY_DB_FILE


class ShortTermMemory:
    """
    Le Hippocampe V3 (Async).
    Gère le stockage KV rapide pour l'état courant de l'entité.
    """

    def __init__(self, db_path: str = str(BRAIN_MEMORY_DB_FILE)):
        self.db_path = db_path

    async def initialize(self):
        """Prépare les synapses (Tables)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()
            logger.info("⚡ STM ready")

    async def remember(self, key: str, value: Any) -> bool:
        """Encode un souvenir rapide."""
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO kv_store (key, value, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET 
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP;
                """,
                    (key, json_str),
                )
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"⚡ [STM] Write Fail: {e}")
            return False

    async def recall(self, key: str, default: Any = None) -> Any:
        """Rappel immédiat."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT value FROM kv_store WHERE key = ?", (key,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return json.loads(row[0])
            return default
        except Exception as e:
            logger.error(f"⚡ [STM] Read Fail: {e}")
            return default

    async def forget(self, key: str) -> bool:
        """Oubli volontaire."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM kv_store WHERE key = ?", (key,))
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"⚡ [STM] Delete Fail: {e}")
            return False

    async def retrieve_recent(self, limit: int = 50) -> list:
        """Retrieve most recent memories for dream consolidation."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT key, value FROM kv_store ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "key": row[0],
                            "content": json.loads(row[1]),
                            "metadata": {"tags": []},
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"⚡ [STM] Retrieve Fail: {e}")
            return []


# Singleton
stm = ShortTermMemory()
