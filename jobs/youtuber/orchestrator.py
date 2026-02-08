"""
JOBS/YOUTUBER/ORCHESTRATOR.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ORCHESTRATOR (SHOWRUNNER) 🎩
PURPOSE: Chef de projet. Coordonne production BILINGUE (FR + EN).
PIPELINE: Script (FR+EN) → Audio (FR+EN) → Vidéo → Montage (FR+EN) → Upload
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger as _root_logger

from corpus.dna.genome import MEMORIES_DIR
from corpus.soma.cells import load_json, save_json
from jobs.youtuber.editor import editor
from jobs.youtuber.producer import producer
from jobs.youtuber.scheduler import scheduler
from jobs.youtuber.syncer import YouTubeSyncer
from jobs.youtuber.uploader import uploader
from jobs.youtuber.visuals import visuals

# SOTA 2026: Bind logger with job name for proper source identification
logger = _root_logger.bind(name="youtuber")

# SOTA 2026: Script Generation Scheduler Constants
SCRIPT_GENERATION_CYCLE_HOURS = 24  # Generate new script every 24h
PENDING_SCRIPTS_DIR = MEMORIES_DIR / "youtuber" / "output" / "pending_scripts"
READY_SCRIPTS_DIR = MEMORIES_DIR / "youtuber" / "output" / "scripts"  # Scripts validés


class Showrunner:
    """
    Le Showrunner BILINGUE.

    Produit automatiquement:
    - 1 vidéo EN pour la chaîne EN
    - 1 vidéo FR pour la chaîne FR

    Même contenu VEO, audio et bannière adaptés.
    """

    def __init__(self) -> None:
        self.state_file = MEMORIES_DIR / "youtuber" / "state.json"
        self.output_dir = MEMORIES_DIR / "youtuber"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.syncer = YouTubeSyncer()
        self._is_running = False
        self._run_task = None

    def _has_pending_scripts(self) -> bool:
        """
        Check if there are scripts awaiting human validation.
        SOTA 2026: Block new script generation if pending scripts exist.
        """
        if not PENDING_SCRIPTS_DIR.exists():
            return False
        pending_files = list(PENDING_SCRIPTS_DIR.glob("*.json"))
        return len(pending_files) > 0

    def _get_next_ready_script(self) -> tuple[dict | None, Path | None]:
        """
        SOTA 2026: Get next validated script pair (FR/EN) from ready queue.
        Returns: (script_data, script_path) or (None, None) if empty.
        """
        if not READY_SCRIPTS_DIR.exists():
            return None, None

        # Get FR scripts (primary), sorted by filename for consistent ordering
        fr_scripts = sorted(READY_SCRIPTS_DIR.glob("*_fr.json"))
        if not fr_scripts:
            return None, None

        # Take oldest script (first in sorted order)
        script_path = fr_scripts[0]
        try:
            script_data = load_json(script_path)
            return script_data, script_path
        except Exception as e:
            logger.error(f"❌ [SHOWRUNNER] Failed to load script {script_path}: {e}")
            return None, None

    def _consume_script(self, script_path: Path) -> None:
        """
        Remove a script after successful production.
        Removes both FR and EN versions.
        """
        base_name = script_path.stem.replace("_fr", "").replace("_en", "")
        for suffix in ["_fr.json", "_en.json"]:
            target = READY_SCRIPTS_DIR / f"{base_name}{suffix}"
            if target.exists():
                try:
                    target.unlink()
                    logger.info(f"🗑️ [SHOWRUNNER] Consumed: {target.name}")
                except Exception as e:
                    logger.error(f"❌ [SHOWRUNNER] Failed to remove {target}: {e}")

    def _is_script_generation_due(self) -> tuple[bool, float]:
        """
        Check if script generation cycle (24h) has elapsed.
        Returns: (is_due, hours_remaining)
        """
        state = load_json(self.state_file, default={})
        last_gen = state.get("last_script_generation")

        if not last_gen:
            # Never generated -> due immediately
            return True, 0.0

        try:
            last_dt = datetime.fromisoformat(last_gen)
            # Strip timezone if present to avoid naive vs aware comparison
            if last_dt.tzinfo is not None:
                last_dt = last_dt.replace(tzinfo=None)
            now = datetime.now()
            next_gen = last_dt + timedelta(hours=SCRIPT_GENERATION_CYCLE_HOURS)

            if now >= next_gen:
                return True, 0.0

            remaining = (next_gen - now).total_seconds() / 3600
            return False, remaining
        except Exception:
            return True, 0.0

    async def _check_and_generate_script(self) -> dict:
        """
        SOTA 2026: Automatic 24h Script Generation Cycle.

        Logic:
        1. If pending script exists -> skip (waiting validation)
        2. If 24h not passed -> skip (cycle not due)
        3. Otherwise -> generate new script via brainstorm

        Returns: {"status": "generated"|"pending"|"waiting", ...}
        """
        # 1. Check pending scripts
        if self._has_pending_scripts():
            logger.info(
                "⏸️ [SCRIPT SCHEDULER] Script pending validation - skipping generation"
            )
            return {"status": "pending", "reason": "script_pending_validation"}

        # 2. Check 24h cycle
        is_due, remaining = self._is_script_generation_due()
        if not is_due:
            logger.debug(f"⏰ [SCRIPT SCHEDULER] Next script in {remaining:.1f}h")
            return {"status": "waiting", "hours_remaining": remaining}

        # 3. Generate new script
        logger.info("🧠 [SCRIPT SCHEDULER] 24h cycle due - generating new script...")
        try:
            # Brainstorm a new topic
            topic = await producer.brainstorm_topic()
            if not topic:
                logger.warning("❌ [SCRIPT SCHEDULER] Brainstorm failed")
                return {"status": "error", "reason": "brainstorm_failed"}

            # Generate bilingual script
            logger.info(f"📝 [SCRIPT SCHEDULER] Generating script for: {topic}")
            script_paths = await producer.generate_bilingual(topic)

            # Update last generation timestamp
            state = load_json(self.state_file, default={})
            state["last_script_generation"] = datetime.now().isoformat()
            save_json(self.state_file, state)

            logger.success(f"✅ [SCRIPT SCHEDULER] Script generated: {topic}")

            # SOTA 2026: Pipeline Notification (Standard 362)
            if state.get("notify_pipeline", True):
                try:
                    from social.messaging.notification_client import notify

                    await notify.youtuber(
                        f"📝 Script Généré\n{topic}", dedup_key="YOUTUBER_SCRIPT"
                    )
                except Exception:
                    pass

            return {
                "status": "generated",
                "topic": topic,
                "scripts": {lang: str(path) for lang, path in script_paths.items()},
            }
        except Exception as e:
            logger.error(f"❌ [SCRIPT SCHEDULER] Generation failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def run_daily_show(self) -> dict:
        """
        Pipeline complète de production BILINGUE.

        SOTA 2026: Consomme les scripts validés depuis /scripts/.

        Logic:
        1. Check 48h Upload Window.
        2. If CLOSED -> Sleep.
        3. If OPEN -> Check Pending Uploads.
        4. If PENDING -> Upload.
        5. If NOTHING -> Produce from VALIDATED scripts.
        6. If NO SCRIPTS -> Auto-pause.
        """
        start_time = datetime.now()
        results = {"status": "started", "en": {}, "fr": {}}

        logger.info("🎬 Showrunner awake")

        # 0. PRÉPARATION
        state = load_json(self.state_file, default={"status": "ACTIVE", "topics": []})

        # 0.1 SYNC DATA (Video Catalog & Analytics)
        try:
            await (
                self.syncer._run_sync_async()
            )  # Direct async call (already in event loop)
        except Exception as e:
            logger.error(f"❌ [SHOWRUNNER] Sync failed: {e}")

        if state.get("status") != "ACTIVE":
            logger.info("💤 [SHOWRUNNER] PAUSED")
            return {"status": "paused"}

        # 1. GATEKEEPER: CHECK DATE
        is_open, remaining = scheduler.is_upload_window_open()
        if not is_open:
            logger.info(
                f"⏳ [GATEKEEPER] 48h limit active. Next slot in {remaining:.1f}h"
            )
            return {"status": "waiting", "remaining_hours": remaining}

        logger.info("🟢 [GATEKEEPER] Upload window OPEN")

        # 2. CHECK PENDING UPLOADS first
        next_video = scheduler.get_next_due()
        if next_video:
            logger.info(
                f"📡 [SHOWRUNNER] Video ready for upload: {next_video.get('metadata', {}).get('title')}"
            )
            # Skip production, go straight to upload logic (Phase 5)
            # We can refactor Phase 5 to be standalone or just jump there.
            # Ideally, we follow flow. Topic will be None.
            pass
        else:
            # 3. IF NOTHING PENDING -> PRODUCE FROM VALIDATED SCRIPTS
            # SOTA 2026: Direct consumption of validated scripts from /scripts/
            script_data, script_path = self._get_next_ready_script()

            if not script_data or not script_path:
                # No validated scripts available -> AUTO-PAUSE
                logger.warning("📭 [SHOWRUNNER] No validated scripts available")
                logger.info("⏸️ [SHOWRUNNER] Auto-pausing pipeline...")
                state["status"] = "PAUSED"
                save_json(self.state_file, state)
                return {"status": "auto_paused", "reason": "no_ready_scripts"}

            # Get both FR and EN script paths
            base_name = script_path.stem.replace("_fr", "").replace("_en", "")
            script_paths = {
                "fr": READY_SCRIPTS_DIR / f"{base_name}_fr.json",
                "en": READY_SCRIPTS_DIR / f"{base_name}_en.json",
            }

            # Filter to only existing scripts
            script_paths = {
                lang: path for lang, path in script_paths.items() if path.exists()
            }

            if not script_paths:
                logger.error("❌ [SHOWRUNNER] Script paths invalid")
                return {"status": "error", "reason": "script_paths_invalid"}

            title = script_data.get("title", base_name)
            logger.info(f"📌 [PRODUCTION] Starting production for: {title}")

            # PRODUCTION (Phases 2-4) - Scripts already exist, skip Phase 1
            # 2. VISUELS
            logger.info("\n👁️ [PHASE 2] Visual Generation...")
            audio_dir = MEMORIES_DIR / "youtuber" / "audio"
            visual_plans = {}
            for lang, sp in script_paths.items():
                if sp.exists():
                    try:
                        plan = await visuals.create_visual_plan(sp, audio_dir)
                        if plan:
                            visual_plans[lang] = plan
                    except Exception as e:
                        logger.error(f"   ❌ Visuals failed: {e}")

            # 3. MONTAGE
            logger.info("\n✂️ [PHASE 3] Bilingual Editing...")
            final_videos = {}
            for lang, plan_path in visual_plans.items():
                try:
                    video_path = editor.assemble_video(plan_path, lang=lang)
                    if video_path:
                        final_videos[lang] = video_path
                except Exception as e:
                    logger.error(f"   ❌ Edit failed: {e}")

            # 4. SCHEDULING
            logger.info("\n📅 [PHASE 4] Scheduling...")
            for lang, video_path in final_videos.items():
                lang_script_data = load_json(script_paths.get(lang))
                metadata = {
                    "title": lang_script_data.get("title", title),
                    "lang": lang,
                    "description": f"Trinity AI - {lang.upper()}",
                    "tags": ["AI", "Trinity", "Shorts"],
                }
                scheduler.add_to_queue(video_path, metadata)

            # Consume script after successful scheduling
            if final_videos:
                self._consume_script(script_path)
                logger.success(f"✅ [SHOWRUNNER] Production complete: {title}")

        # 5. UPLOAD PHASE (Always run if we reached here)
        logger.info("\n📡 [PHASE 5] Publication Check...")
        upload_state = load_json(self.state_file, default={})

        if upload_state.get("upload_enabled", False):
            # Try to upload pending videos
            for lang in ["en", "fr"]:
                next_vid = scheduler.get_next_due()  # This checks scheduled time vs now
                # If we just produced, scheduled time might be optimal_hour (future/now).
                # If scheduler says it's due, we upload.
                if next_vid and next_vid.get("metadata", {}).get("lang") == lang:
                    try:
                        video_id = await uploader.upload_video(
                            Path(next_vid["path"]),
                            next_vid["metadata"],  # type: ignore[call-arg]
                        )
                        if video_id:
                            scheduler.mark_published(next_vid["id"], video_id)
                            results[lang]["youtube_id"] = video_id
                            logger.success(f"   ✅ {lang.upper()} uploaded: {video_id}")

                            # SOTA 2026: Upload Notification (Standard 362)
                            if upload_state.get("notify_uploads", True):
                                try:
                                    from social.messaging.notification_client import (
                                        notify,
                                    )

                                    title = next_vid.get("metadata", {}).get(
                                        "title", "Video"
                                    )
                                    await notify.youtuber(
                                        f"📡 Upload YouTube\n{title} ({lang.upper()})",
                                        dedup_key="YOUTUBER_UPLOAD",
                                    )
                                except Exception:
                                    pass

                    except Exception as e:
                        logger.error(f"   ❌ Upload failed: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"🎬 [SHOWRUNNER] Cycle Complete in {elapsed:.1f}s")
        return results

    async def quick_test(self) -> dict:
        """Test rapide bilingue - utilise le prochain script validé."""
        logger.info("🧪 [SHOWRUNNER] Quick Test - Using next validated script")
        return await self.run_daily_show()

    async def run_forever(self):
        """
        Independent Loop (Loader Protocol).
        SOTA 2026: Now includes automatic 24h script generation cycle.
        """
        logger.info("🎩 [YOUTUBER] Starting autonomous loop (Showrunner)...")
        while self._is_running:
            # SOTA 2026: Golden Interval (Fibonacci 377s ~ 6.2 min)
            sleep_time = 377
            try:
                # CRITICAL: ALWAYS respect PAUSE state (Standard 362.50.20)
                state = load_json(self.state_file, default={"status": "ACTIVE"})
                if state.get("status") != "ACTIVE":
                    logger.debug("💤 [YOUTUBER] Paused - sleeping...")
                    sleep_time = 55 * 60  # Fibonacci 55 minutes
                else:
                    # SOTA 2026: Script Generation Scheduler (24h Cycle)
                    script_result = await self._check_and_generate_script()
                    if script_result.get("status") == "generated":
                        logger.success(
                            "🧠 [SCRIPT SCHEDULER] New script ready for validation"
                        )

                    # Run daily show logic
                    results = await self.run_daily_show()

                    # Dynamic Sleep Optimization
                    if results.get("status") == "waiting":
                        remaining = results.get("remaining_hours", 0)
                        if remaining > 0:
                            sleep_time = int(remaining * 3600) + 60
                            logger.info(
                                f"🛌 [YOUTUBER] Smart Sleep: Waking up in {sleep_time / 3600:.1f}h"
                            )

            except Exception as e:
                logger.error(f"🎩 [YOUTUBER] Loop error: {e}")

            # Interruptible Sleep
            if self._is_running:
                # Chunk sleep to allow stop
                chunks = sleep_time // 1
                for _ in range(int(chunks)):
                    if not self._is_running:
                        break
                    await asyncio.sleep(1)

    async def start(self):
        """Loader Protocol Start."""
        logger.info("🎩 [YOUTUBER] Starting via Loader Protocol...")
        self._is_running = True
        self._run_task = asyncio.create_task(self.run_forever())

    async def stop(self):
        """Loader Protocol Stop."""
        logger.info("🎩 [YOUTUBER] Stopping...")
        self._is_running = False
        # No need to cancel task, loop will exit on next tick
        logger.success("🎩 [YOUTUBER] Stopped")


# Singleton
showrunner = Showrunner()
# Loader expects 'youtuber' (job name) or 'orchestrator' (entry point)
youtuber = showrunner

if __name__ == "__main__":
    asyncio.run(showrunner.quick_test())
