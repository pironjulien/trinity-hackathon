"""
CORPUS/SOMA/PLUGINS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ADAPTIVE SOMA (PLUGINS) 🧩
PURPOSE: Chargement dynamique des extensions cognitives (Mini-Plugins).
         Permet à Trinity d'étendre ses capacités sans redéploiement.
══════════════════════════════════════════════════════════════════════════════
"""

import importlib.util
import sys
import asyncio
from pathlib import Path
from loguru import logger
from corpus.dna.genome import MEMORIES_DIR

# Structure des dossiers
PLUGINS_DIR = MEMORIES_DIR / "plugins"
ACTIVE_DIR = PLUGINS_DIR / "active"
STAGING_DIR = PLUGINS_DIR / "staging"
QUARANTINE_DIR = PLUGINS_DIR / "quarantine"


class PluginManager:
    """Gestionnaire d'extensions neuronales dynamiques."""

    def __init__(self):
        self.loaded_plugins = {}
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Crée l'arborescence si nécessaire."""
        for d in [ACTIVE_DIR, STAGING_DIR, QUARANTINE_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    async def load_active_plugins(self) -> int:
        """
        Charge tous les scripts python validés dans active/.
        SOTA: Chargement asynchrone et isolé.
        """
        count = 0
        if not ACTIVE_DIR.exists():
            return 0

        logger.info("🧩 Plugins scan")

        for py_file in ACTIVE_DIR.glob("*.py"):
            try:
                plugin_name = py_file.stem

                # 1. Chargement dynamique du module
                spec = importlib.util.spec_from_file_location(plugin_name, py_file)
                if not spec or not spec.loader:
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin_name] = module
                spec.loader.exec_module(module)

                # 2. Exécution du setup() si présent (Convention)
                if hasattr(module, "setup"):
                    if asyncio.iscoroutinefunction(module.setup):
                        await module.setup(self)
                    else:
                        module.setup(self)

                self.loaded_plugins[plugin_name] = module
                count += 1
                logger.success(f"🧩 [PLUGINS] + {plugin_name}")

            except Exception as e:
                logger.error(f"💥 [PLUGINS] Load Fail: {py_file.name}")
                # Auto-Quarantine immédiate : Le corps rejette la greffe
                self._quarantine(py_file, reason=str(e))

        return count

    def _quarantine(self, file_path: Path, reason: str):
        """Isole un plugin toxique pour protéger le système."""
        try:
            dest = QUARANTINE_DIR / file_path.name
            # Si destination existe, on écrase ou rename
            if dest.exists():
                dest.unlink()

            file_path.rename(dest)
            logger.warning(f"☣️ [PLUGINS] Quarantine: {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to quarantine plugin: {e}")


# Singleton
plugins = PluginManager()
