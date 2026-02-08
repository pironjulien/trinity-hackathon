"""
CORPUS/SOMA/HYGIENE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: HYGIENE (IMMUNE CLEANING) 🧹
PURPOSE: Nettoyage automatique des déchets (Logs, Tmp).
FREQ: Appelé au démarrage et par cycle (via Immune).
══════════════════════════════════════════════════════════════════════════════
"""

import shutil
import time
from pathlib import Path
from loguru import logger
from corpus.dna.genome import LOGS_DIR

MAX_LOG_AGE_DAYS = 7


class HygieneSystem:
    """
    Le Système Lymphatique.
    Évacue les déchets pour éviter l'intoxication numérique.
    """

    def __init__(self):
        self.logs_dir = LOGS_DIR

        # Ensure dirs exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def clean_cycle(self):
        """Lance un cycle de nettoyage complet."""
        logger.info("🧹 [HYGIENE] Cleaning Cycle Started...")

        deleted_count = 0

        # 1. Rotate Logs (Keep 7 days)
        logger.debug(f"🧹 [HYGIENE] Cleaning Logs: {self.logs_dir}")
        deleted_count += self._clean_dir(self.logs_dir, MAX_LOG_AGE_DAYS * 86400)

        if deleted_count > 0:
            logger.success(f"🧹 [HYGIENE] Removed {deleted_count} items.")
        else:
            logger.debug("🧹 [HYGIENE] System is clean.")

    def _clean_dir(self, directory: Path, max_age_seconds: int) -> int:
        now = time.time()
        count = 0

        if not directory.exists():
            return 0

        # 🛡️ SAFETY CHECK (CRITICAL)
        abs_path = str(directory.resolve()).lower()
        if "memories" not in abs_path and "logs" not in abs_path:
            logger.critical(
                f"🛑 [HYGIENE] SAFETY KICK: Tentative de suppression hors zone sûre: {abs_path}"
            )
            raise ValueError(f"CRITICAL: Suppression interdite dans {abs_path}")

        for item in directory.iterdir():
            try:
                # Check age
                if (now - item.stat().st_mtime) > max_age_seconds:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                    count += 1
            except Exception as e:
                logger.warning(f"⚠️ [HYGIENE] Failed to delete {item.name}: {e}")

        return count


# Singleton
hygiene = HygieneSystem()


def purify_environment():
    """Wrapper pour l'appel depuis main.py"""
    hygiene.clean_cycle()
