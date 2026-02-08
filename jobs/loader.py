"""
JOBS/LOADER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: Generic Job Loader
PURPOSE: Dynamically load jobs based on jobs.json configuration.
ARCH: PRIME DIRECTIVE 1 Compliant — corpus/ never imports from jobs/
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import importlib
from typing import Dict, Any, Optional
from loguru import logger

from corpus.soma.cells import load_json
from corpus.soma.nerves import nerves
from corpus.dna.genome import MEMORIES_DIR, CORPUS_DIR


# Active job instances
active_jobs: Dict[str, Any] = {}

# Jobs config file location
JOBS_CONFIG_FILE = MEMORIES_DIR / "jobs.json"

# Jules config file (SOTA 2026: Persistence like jobs - absolute path)
JULES_CONFIG_FILE = CORPUS_DIR.parent / "jules" / "config.json"


async def load_jobs(app=None) -> None:
    """
    Load and start all enabled jobs from jobs.json.
    Optionally mount job-specific API routes if app is provided.
    """
    global active_jobs

    jobs_config = load_json(JOBS_CONFIG_FILE, default={})

    if not jobs_config:
        logger.info("💤 No jobs")
        return

    # 1. Mount APIs (Always Available for Control Panel)
    if app is not None:
        # Trader
        try:
            from jobs.trader.api import router as trader_router

            app.include_router(trader_router)
        except Exception:
            pass  # Silent fail if module missing

        # Influencer
        try:
            from jobs.influencer.api import router as influencer_router

            app.include_router(influencer_router)
        except Exception:
            pass

        # YouTuber
        try:
            from jobs.youtuber.api import router as youtuber_router

            app.include_router(youtuber_router)
        except Exception:
            pass

        # Jules (SOTA 2026: Staging & Review System)
        try:
            from jules.api import router as jules_router

            app.include_router(jules_router, prefix="/api")
        except Exception:
            pass

        # Evolution Report (SOTA 2026: 8810 Sentinel Button)
        try:
            from corpus.brain.evolution_api import router as evolution_router

            app.include_router(evolution_router)
        except Exception:
            pass
    for job_name, job_cfg in jobs_config.items():
        if not job_cfg.get("enabled", False):
            logger.debug(f"💤 [JOBS] {job_name} off")
            continue

        # Get entry point (default: heart)
        entry_point = job_cfg.get("entry_point", "heart")

        if not entry_point:
            logger.debug(f"💤 [JOBS] {job_name} no entry")
            continue

        try:
            # Dynamic import: jobs.{job_name}.{entry_point}
            module_path = f"jobs.{job_name}.{entry_point}"
            module = importlib.import_module(module_path)

            # Try to get singleton (convention: job_name or entry_point name)
            instance = (
                getattr(module, job_name, None)
                or getattr(module, entry_point, None)
                or getattr(module, "instance", None)
            )

            if not instance:
                logger.warning(f"⚠️ [JOBS] {job_name}: No singleton")
                continue

            if not hasattr(instance, "start"):
                logger.warning(f"⚠️ [JOBS] {job_name}: No start()")
                continue

            # Register job
            active_jobs[job_name] = instance

            # Start job
            asyncio.create_task(instance.start())
            logger.success(f"✅ {job_name}")
            nerves.fire("STATUS", "JOB_ACTIVE", {"job": job_name, "active": True})

        except ImportError as e:
            logger.warning(f"⚠️ [JOBS] {job_name} 404")
            nerves.fire("PAIN", "JOBS", f"{job_name} import failed: {e}")
        except Exception as e:
            import traceback

            tb = traceback.format_exc()  # noqa: F841
            logger.error(f"💥 [JOBS] {job_name} Fail: {e}")
            nerves.fire("PAIN", "JOBS", f"{job_name} error: {e}")

    # ════════════════════════════════════════════════════════════════════════
    # JULES AUTO-START (SOTA 2026: Persistence like jobs)
    # If jules/config.json has "active": true, start the Jules worker
    # ════════════════════════════════════════════════════════════════════════
    try:
        if JULES_CONFIG_FILE.exists():
            jules_cfg = load_json(JULES_CONFIG_FILE, default={})
            if jules_cfg.get("active", False):
                from jules.heart import heart as jules_heart

                if "jules" not in active_jobs:
                    active_jobs["jules"] = jules_heart
                    asyncio.create_task(jules_heart.start())
                    logger.success("✅ jules (auto-start)")
                    nerves.fire(
                        "STATUS", "JOB_ACTIVE", {"job": "jules", "active": True}
                    )
    except Exception as e:
        logger.warning(f"⚠️ [JOBS] Jules auto-start failed: {e}")

    if active_jobs:
        logger.info(f"🏎️ {len(active_jobs)} jobs")
    else:
        logger.info("💤 No jobs active")


async def stop_jobs() -> None:
    """Stop all active jobs gracefully."""
    global active_jobs

    for job_name, instance in active_jobs.items():
        try:
            if hasattr(instance, "stop"):
                await instance.stop()
                logger.info(f"🛑 [JOBS] {job_name}")
        except Exception:
            logger.error(f"💥 [JOBS] {job_name} Stop Fail")

    active_jobs.clear()


def get_job(name: str) -> Optional[Any]:
    """Get a job instance by name."""
    return active_jobs.get(name)


def is_job_active(name: str) -> bool:
    """Check if a job is currently active."""
    return name in active_jobs


async def start_job(name: str) -> bool:
    """
    Dynamically start a single job by name.
    Returns True if started successfully, False otherwise.
    """
    global active_jobs

    if name in active_jobs:
        logger.info(f"⚡ [JOBS] {name} running")
        return True

    jobs_config = load_json(JOBS_CONFIG_FILE, default={})
    job_cfg = jobs_config.get(name, {})

    if not job_cfg:
        logger.warning(f"⚠️ [JOBS] {name} 404")
        return False

    entry_point = job_cfg.get("entry_point", "heart")
    if not entry_point:
        logger.warning(f"⚠️ [JOBS] {name} no entry")
        return False

    try:
        module_path = f"jobs.{name}.{entry_point}"
        module = importlib.import_module(module_path)

        # Reload module to get fresh state
        importlib.reload(module)

        instance = (
            getattr(module, name, None)
            or getattr(module, entry_point, None)
            or getattr(module, "instance", None)
        )

        if not instance:
            logger.warning(f"⚠️ [JOBS] {name}: No singleton")
            return False

        if not hasattr(instance, "start"):
            logger.warning(f"⚠️ [JOBS] {name}: No start()")
            return False

        active_jobs[name] = instance
        asyncio.create_task(instance.start())
        logger.success(f"🚀 [JOBS] {name.upper()}")
        nerves.fire("STATUS", "JOB_ACTIVE", {"job": name, "active": True})
        return True

    except Exception as e:
        logger.error(f"💥 [JOBS] {name} Fail")
        nerves.fire("PAIN", "JOBS", f"{name} start failed: {e}")
        return False


async def stop_job(name: str) -> bool:
    """
    Dynamically stop a single job by name.
    Returns True if stopped successfully, False otherwise.
    """
    global active_jobs

    if name not in active_jobs:
        logger.info(f"⚡ [JOBS] {name} idle")
        return True

    instance = active_jobs[name]

    try:
        if hasattr(instance, "stop"):
            await instance.stop()
        del active_jobs[name]
        logger.success(f"🛑 [JOBS] {name.upper()}")
        nerves.fire("STATUS", "JOB_ACTIVE", {"job": name, "active": False})
        return True
    except Exception:
        logger.error(f"💥 [JOBS] {name} Stop Fail")
        return False
