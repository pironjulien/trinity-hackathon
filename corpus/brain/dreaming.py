"""
CORPUS/BRAIN/DREAMING.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: DREAMING V2 (AUTO-GUÉRISON) 🌙
PURPOSE: Analyse les cauchemars (logs d'erreurs) et génère des patchs.
══════════════════════════════════════════════════════════════════════════════
"""

import json
from loguru import logger
from corpus.brain.hippocampus import stm
from corpus.dna.genome import LOGS_DIR
from corpus.soma.nerves import nerves


class Dreamer:
    """Manager du Sommeil Paradoxal & Auto-Guérison."""

    def __init__(self):
        self.is_dreaming = False

    async def start_rem_cycle(self) -> int:
        """Lance le cycle : Consolidation + Guérison."""
        logger.info("🌙 [DREAMING] Entering REM Cycle...")
        self.is_dreaming = True

        # 1. Consolidation Mémoire (Classique)
        await self._consolidate_memories()

        # 2. AUTO-GUÉRISON (Nouveau)
        # On ne lance ça que si on a détecté des erreurs critiques la veille
        await self._heal_nightmares()

        self.is_dreaming = False
        return 1

    async def _consolidate_memories(self):
        """Transforme la STM en LTM (Version simplifiée)."""
        recent = await stm.retrieve_recent(limit=50)
        # Logique simplifiée pour économie de tokens
        if recent:
            logger.info(f"💎 [DREAMING] Consolidated {len(recent)} memories.")

    async def _heal_nightmares(self):
        """
        Analyse les logs d'erreurs et propose des correctifs (Patches).
        """
        logger.info("🩺 [DREAMING] Scanning for nightmares (errors)...")

        # 1. Lire les logs d'erreurs récents
        error_logs = self._scan_error_logs(limit=20)

        if not error_logs:
            logger.info("🌙 [DREAMING] Sleep is peaceful. No errors found.")
            return

        # 2. Grouper par type d'erreur pour éviter les doublons
        unique_errors = {}
        for log in error_logs:
            # Clé simple : Message d'erreur
            msg = log.get("message", "")[:100]
            if msg not in unique_errors:
                unique_errors[msg] = log

        logger.warning(f"🩺 [DREAMING] Found {len(unique_errors)} unique nightmares.")

        # 3. Pour chaque cauchemar majeur, déléguer à Jules (SOTA)

        for msg, log in unique_errors.items():
            source_module = log.get("extra", {}).get("source", "unknown")
            logger.info(f"💊 [DREAMING] Delegating nightmare to Jules: {msg[:50]}...")

            error_desc = f"""
            RUNTIME ERROR: {msg}
            SOURCE: {source_module}
            FULL LOG: {json.dumps(log)}
            
            TASK: validFix this bug. 
            Search for the file '{source_module.split(".")[-1]}.py' or similar.
            Create a PR with a fix.
            """

            try:
                # OPTIONAL: DÉLÉGATION À JULES (peripheral, not vital)
                try:
                    from jules.jules_client import (
                        JulesClient,
                        JulesMode,
                        save_jules_task,
                    )
                except ImportError:
                    logger.debug(
                        "💊 [DREAMING] Jules not available - skipping delegation"
                    )
                    continue

                async with JulesClient(mode=JulesMode.GUARDIAN) as jules:
                    session = await jules.create_session(
                        prompt=error_desc,
                        title=f"Fix: {msg[:30]}",
                        auto_create_pr=True
                    )

                    if session:
                        save_jules_task(session.id)
                        logger.success(
                            f"💊 [DREAMING] Nightmare delegated to Jules: {session.title}"
                        )
                        nerves.fire(
                            "DREAM",
                            "INFO",
                            f"🌙 <b>RÊVE LUCIDE</b>\nErreur : <i>{msg[:50]}</i>.\nJules répare ça : `{session.title}`.",
                        )
                    else:
                        logger.error("💊 [DREAMING] Jules refused the nightmare.")

            except Exception as e:
                logger.error(f"💥 [DREAMING] Failed to heal nightmare: {e}")

    def _scan_error_logs(self, limit=20):
        """Lit les fichiers logs pour trouver des entrées de niveau ERROR."""
        errors = []
        # On suppose que les logs systèmes sont dans system.jsonl
        log_file = LOGS_DIR / "system.jsonl"
        if not log_file.exists():
            return []

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                # Lire les dernières lignes (méthode simple)
                lines = f.readlines()[-200:]  # Check last 200 lines
                for line in lines:
                    if '"level": "ERROR"' in line or '"level": "CRITICAL"' in line:
                        try:
                            errors.append(json.loads(line))
                        except Exception:
                            pass
        except Exception:
            pass
        return errors[-limit:]


# Singleton
dreamer = Dreamer()
