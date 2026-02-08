"""
PARTNERS/JULES/NIGHTWATCH.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE NIGHTWATCH (ANGEL GUARDIAN) 🦉
PURPOSE: Autonomous Log Monitoring & Active Failsafe.
         Uses a 'Dead Man's Switch' (Probation Lock) to revert critical failures.
══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
import asyncio
from loguru import logger

# Initialisation de l'environnement pour importer les modules Trinity
sys.path.append(os.getcwd())

try:
    from corpus.dna.genome import genome, LOGS_DIR
    from jules.git_controller import GitController
except ImportError:
    print("❌ ERREUR: Lance ce script depuis la racine du dossier Trinity !")
    sys.exit(1)


async def analyze_logs():
    """
    Active Failsafe:
    Checks for CRITICAL errors only if the System is in Probation (Locked).
    Uses Strike system: 1st failure = quarantine (retry), 2nd = blacklist.
    """
    try:
        LOCK_FILE = genome.ROOT_DIR / ".probation_lock"

        # SYSTEM NOT IN PROBATION -> SLEEP (Pass)
        if not LOCK_FILE.exists():
            return

        # LOGIC: LOCK EXISTS -> WE ARE IN DANGER ZONE
        log_files = [LOGS_DIR / "system.jsonl", LOGS_DIR / "alerts.jsonl"]

        for log_file in log_files:
            if not log_file.exists():
                continue

            # Read last 20 lines to catch immediate crash
            try:
                logs = log_file.read_text("utf-8").splitlines()[-20:]
            except Exception:
                continue

            for line in logs:
                if any(
                    k in line
                    for k in [
                        "CRITICAL",
                        "Traceback",
                        "ModuleNotFoundError",
                        "SyntaxError",
                    ]
                ):
                    logger.critical(
                        "🚨 [NIGHTWATCH] CRITICAL FAILURE DETECTED DURING PROBATION!"
                    )
                    logger.critical(f"🚨 Source: {line[:100]}...")

                    # TRIGGER REVERT
                    git = GitController(genome.ROOT_DIR)
                    if git.revert_last_commit():
                        logger.success("🚑 [NIGHTWATCH] AUTO-REVERT SUCCESSFUL.")

                        # CORTEX SYSTEM: Record failure in semantic memory
                        current_attempt_file = (
                            genome.ROOT_DIR / "memories/jules/.current_attempt"
                        )
                        if current_attempt_file.exists():
                            signature = current_attempt_file.read_text().strip()
                            logger.warning(
                                f"💀 [NIGHTWATCH] Recording failure for: {signature}"
                            )

                            # Record failure in Cortex
                            from jules.cortex import cortex

                            error_msg = line.strip()[:200]
                            cortex.record_outcome(signature, "FAILED", reason=error_msg)

                            # Check if now blocked
                            if not cortex.check_task(signature):
                                logger.critical(
                                    f"☠️ [NIGHTWATCH] BLACKLISTED/COOLDOWN: {signature}"
                                )
                                # Notify via Phone Widget
                                try:
                                    from social.messaging.notification_client import (
                                        notify,
                                    )
                                    import asyncio

                                    asyncio.get_event_loop().create_task(
                                        notify.jules(
                                            f"☠️ Task blocked by Cortex: {signature}"
                                        )
                                    )
                                except Exception:
                                    pass
                            else:
                                logger.warning(
                                    f"⚠️ [NIGHTWATCH] QUARANTINE: {signature} (will retry with post-mortem)"
                                )

                            current_attempt_file.unlink()  # Clear attempt

                    else:
                        logger.critical("☠️ [NIGHTWATCH] AUTO-REVERT FAILED.")

                    # DELETE LOCK TO STOP LOOP
                    LOCK_FILE.unlink(missing_ok=True)
                    return

    except Exception as e:
        logger.error(f"Nightwatch scan failed: {e}")


async def main_loop():
    logger.debug("🦉 [NIGHTWATCH] Angel Guardian Activated.")
    while True:
        await analyze_logs()
        # Fast check during probation (probation is ~3min, check every 10s is fine)
        # But to be truly "Active", checking every 5s is safer.
        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.warning("🦉 [NIGHTWATCH] Sleeping.")
