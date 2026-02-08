"""
JOBS/YOUTUBER/LAUNCHER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ORCHESTRATOR (LAUNCHER) 🚀
PURPOSE: Exécution séquentielle ROBUSTE : Script -> Audio -> Visuel -> Montage.
FIX: Vérification stricte de l'existence des fichiers Audio avant Montage.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from loguru import logger as _root_logger

from corpus.brain.gattaca import ROUTE_LIVE, ROUTE_VOICE, gattaca
from corpus.dna.genome import JOBS_DIR, MEMORIES_DIR
from corpus.soma.cells import load_json, save_json
from jobs.youtuber.editor import editor
from jobs.youtuber.uploader import uploader_en, uploader_fr
from jobs.youtuber.visuals import visuals

# SOTA 2026: Bind logger with job name for proper source identification
logger = _root_logger.bind(name="youtuber")

# Paths
LAUNCH_QUEUE_FILE = MEMORIES_DIR / "youtuber" / "data" / "launch_queue.json"
OUTPUT_BASE = JOBS_DIR / "youtuber" / "output"
OUTPUT_DIR = OUTPUT_BASE / "renders"
SCRIPTS_DIR = OUTPUT_BASE / "scripts"
AUDIO_DIR = OUTPUT_BASE / "audio"
VIDEO_CLIPS_DIR = OUTPUT_BASE / "video_clips"

# Ensure dirs
for d in [OUTPUT_DIR, SCRIPTS_DIR, AUDIO_DIR, VIDEO_CLIPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class LaunchProcessor:
    """
    Processeur de la queue de lancement.
    Orchestration STRICTE & RAPIDE.
    """

    def __init__(self):
        self.queue = load_json(
            LAUNCH_QUEUE_FILE, default={"launch_queue": [], "current_day": 0}
        )

    def get_current_video(self) -> dict:
        """Retourne la vidéo du jour courant."""
        current_day = self.queue.get("current_day", 0)
        videos = self.queue.get("launch_queue", [])

        for video in videos:
            if video.get("day") == current_day:
                return video
        return None

    def _safe_basename(self, text: str) -> str:
        """Stricte ASCII normalization."""
        import unicodedata
        import re

        norm = (
            unicodedata.normalize("NFKD", text)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        clean = re.sub(r"[^a-zA-Z0-9]", "_", norm.lower())
        return clean[:50]  # Limit length

    def _save_audio(self, source_path_str: str, target_path: Path):
        """Helper to copy audio file with robust checks."""
        source = Path(source_path_str)
        if not source.exists():
            logger.error(f"❌ Audio source missing: {source}")
            return

        try:
            import shutil

            # Rename (Move) is faster and cleans up temp files
            if source.resolve() != target_path.resolve():
                shutil.move(source, target_path)
            # If move fails (cross-device), copy then delete? Move handles it usually.
        except Exception as e:
            logger.error(f"❌ Audio move failed: {e}")

    async def generate_audio_for_script(
        self, script: dict, lang: str, basename: str
    ) -> dict[int, Path]:
        """
        Génère l'audio avec ROUTING HYBRIDE:
        1. Tente VOICEFAST (Gemini 2.5 Flash) -> Vitesse
        2. Fallack VOICE (Gemini 2.5 Pro) -> Qualité
        """
        segments = script.get("script", [])
        audio_paths = {}

        for i, seg in enumerate(segments):
            text = seg.get("text", "")
            if not text:
                continue

            # Use safe basename
            safe_seg_name = self._safe_basename(seg.get("seg", f"SEG_{i}"))
            audio_file = AUDIO_DIR / f"{basename}_{lang}_{i:02d}_{safe_seg_name}.wav"

            # Skip check
            if audio_file.exists():
                logger.info(f"   ⏭️ Audio exists: {audio_file.name}")
                audio_paths[i] = audio_file
                continue

            # Tone Injection - Format that Gemini TTS interprets as STYLE not text
            # Using "Say in X tone:" prefix which is understood as instruction
            tone = seg.get("tone", "Neutral")
            # Map tone names to style instructions
            TONE_STYLES = {
                "Cold": "cold and distant",
                "Froid": "cold and distant",
                "Provocative": "provocative and challenging",
                "Provocant": "provocative and challenging",
                "Warm": "warm and reassuring",
                "Chaleureux": "warm and reassuring",
                "Neutral": "calm",
            }
            style = TONE_STYLES.get(tone, "calm")
            voice_prompt = f"<style>{style}</style> {text}"
            lang_code = "fr-FR" if lang == "fr" else "en-US"

            # 1. ATTEMPT FAST (Flash)
            try:
                result = await gattaca.route(
                    voice_prompt, route_id=ROUTE_LIVE, lang=lang_code
                )
                result_data = json.loads(result) if isinstance(result, str) else result

                if result_data.get("status") == "ok" and result_data.get("path"):
                    self._save_audio(result_data["path"], audio_file)
                    # Verify
                    if audio_file.exists():
                        audio_paths[i] = audio_file
                        logger.success(f"   ⚡ FAST TTS: {audio_file.name}")
                        continue
                    else:
                        logger.error(
                            f"   ❌ FAST TTS saved but missing at target: {audio_file}"
                        )

            except Exception as e:
                logger.warning(f"   ⚠️ FAST TTS failed ({e}), switching to PRO...")

            # 2. FALLBACK PRO (Voice)
            try:
                result = await gattaca.route(
                    voice_prompt, route_id=ROUTE_VOICE, lang=lang_code
                )
                result_data = json.loads(result) if isinstance(result, str) else result

                if result_data.get("status") == "ok" and result_data.get("path"):
                    self._save_audio(result_data["path"], audio_file)
                    if audio_file.exists():
                        audio_paths[i] = audio_file
                        logger.success(f"   ✅ PRO TTS: {audio_file.name}")
                    else:
                        logger.error(
                            f"   ❌ PRO TTS saved but missing at target: {audio_file}"
                        )
                else:
                    logger.error(f"   ❌ PRO TTS Filed too: {result_data.get('error')}")

            except Exception as e:
                logger.error(f"   ❌ PRO TTS Exception: {e}")

        return audio_paths

    async def generate_video(self, video_data: dict, lang: str) -> Path | None:
        """
        Orchestration COMPLETE.
        Si un seul maillon manque (Audio ou Vidéo), on annule tout.
        """
        script_key = f"script_{lang}"
        script = video_data.get(script_key)
        if not script:
            logger.error(f"❌ No script for {lang}")
            return None

        topic = video_data.get("topic", "video")
        day = video_data.get("day", 0)

        # Safe Basename
        safe_topic = self._safe_basename(topic)
        basename = f"day{day:02d}_{safe_topic}"

        # 0. CHECK RESUMABILITY (Final Render)
        # Check standard pattern:
        possible_final = (
            OUTPUT_DIR
            / f"{self._safe_basename(script.get('title', 'video'))[:30]}_{lang}.mp4"
        )
        if possible_final.exists():
            logger.success(f"   🎉 Final Video already exists: {possible_final.name}")
            return possible_final

        logger.info(f"🎬 [LAUNCHER] Generating {lang.upper()}: {topic}")

        # 1. Save Local Script
        script_path = SCRIPTS_DIR / f"launch_{basename}_{lang}.json"
        script["_meta"] = {
            "topic": topic,
            "lang": lang,
            "day": day,
            "timestamp": datetime.now().isoformat(),
        }
        save_json(script_path, script)

        # 2. AUDIO GENERATION
        audio_paths = await self.generate_audio_for_script(script, lang, basename)

        # STRICT AUDIT
        segments = script.get("script", [])
        if len(audio_paths) != len(segments):
            logger.critical(
                f"🛑 [LAUNCHER] Missing Audio segments for {lang}. ABORTING."
            )
            missing = set(range(len(segments))) - set(audio_paths.keys())
            logger.critical(f"   Missing indices: {missing}")
            return None

        # 3. VIDEO GENERATION (VEO)
        # FIX: Video clips are LANGUAGE-AGNOSTIC (same visual for EN/FR)
        # Only Audio differs. This saves tokens by not generating 2x the same clips.
        base_visual = f"day{day:02d}_{safe_topic}"  # NO lang suffix!

        for i, seg in enumerate(segments):
            seg_name = self._safe_basename(seg.get("seg", f"SEG_{i}"))
            # SHARED path: video clips are reused across EN/FR
            target_path = VIDEO_CLIPS_DIR / f"{base_visual}_{i:02d}_{seg_name}.mp4"
            seg["_target_path"] = target_path

        # Parallel Generate (will skip if file already exists)
        video_paths_list = await visuals.generate_all_segments(segments)

        if any(p is None for p in video_paths_list):
            failed_count = sum(1 for p in video_paths_list if p is None)
            logger.error(
                f"🛑 [LAUNCHER] {failed_count} segments FAILED for {topic} ({lang}). ABORTING EDIT."
            )
            return None

        # 4. PLAN CREATION
        visual_segments = []
        for i, seg in enumerate(segments):
            # Safe because we checked validity above
            v_path = video_paths_list[i]

            # REPAIR AUDIO IF NEEDED
            # Gemini sometimes output raw PCM. If ffmpeg can't read it, wrap it.
            a_path_str = str(audio_paths.get(i))
            if a_path_str:
                self._repair_audio_header(Path(a_path_str))

            visual_segments.append(
                {
                    "index": i,
                    "name": seg.get("seg", f"SEG_{i}"),
                    "visual_prompt": seg.get("visual", "abstract AI scene"),
                    "video_path": str(v_path),
                    "audio_path": a_path_str,  # Guaranteed to exist now
                    "text": seg.get("text", ""),  # FIX: Include text for SRT subtitles
                    "duration_est": len(seg.get("text", "")) / 12,
                }
            )

        plan = {
            "title": script.get("title", "Untitled"),
            "lang": lang,
            "segments": visual_segments,
            "total_duration_est": sum(s["duration_est"] for s in visual_segments),
        }

        plan_path = SCRIPTS_DIR / f"plan_launch_{basename}_{lang}.json"
        save_json(plan_path, plan)

        # 5. EDITOR ASSEMBLY
        video_path = editor.assemble_video(plan_path, lang=lang)

        if video_path and video_path.exists():
            logger.success(f"   ✅ Video Assembled: {video_path.name}")
            return video_path

        logger.error("   ❌ Assembly Failed")
        return None

    def _repair_audio_header(self, path: Path):
        """
        Check if audio is readable by ffmpeg. If not (Invalid data), assume Raw PCM and fix it.
        """
        import subprocess
        import os

        # Access ffmpeg bin from editor instance
        ffmpeg = editor.ffmpeg_bin

        # 1. Probe
        creation_flags = 0x08000000 if os.name == "nt" else 0
        cmd_probe = [ffmpeg, "-i", str(path)]
        try:
            # If this runs without "Invalid data", it's fine.
            # actually ffmpeg -i always exits 1 if no output specified, but we check stderr for "Invalid data"
            res = subprocess.run(
                cmd_probe,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                creationflags=creation_flags,
            )
            stderr = res.stderr.decode()

            if "Invalid data found" in stderr:
                logger.warning(
                    f"🔧 Repairing AUDIO HEADER for {path.name} (Assuming s16le 24k)..."
                )

                # 2. Convert Raw PCM to WAV
                # Rename original to .raw
                raw_path = path.with_suffix(".raw")
                if path.exists():
                    try:
                        path.rename(raw_path)
                    except Exception:
                        pass  # might exist

                if raw_path.exists():
                    cmd_fix = [
                        ffmpeg,
                        "-f",
                        "s16le",
                        "-ar",
                        "24000",
                        "-ac",
                        "1",
                        "-i",
                        str(raw_path),
                        "-y",
                        str(path),
                    ]
                    subprocess.run(
                        cmd_fix,
                        check=True,
                        stderr=subprocess.PIPE,
                        creationflags=creation_flags,
                    )
                    logger.success(f"   ✅ Repaired: {path.name}")
                    # Cleanup raw
                    try:
                        raw_path.unlink()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"⚠️ Audio Repair Failed: {e}")

    async def process_current_day(
        self, upload: bool = False, privacy: str = "private"
    ) -> dict[str, Path | None]:
        """Génère les vidéos EN et FR pour le jour courant."""
        video_data = self.get_current_video()
        if not video_data:
            logger.warning("🏁 [LAUNCHER] No more videos in queue!")
            return {}

        day = video_data.get("day", 0)
        topic = video_data.get("topic", "video")
        logger.info(f"🚀 [LAUNCHER] Processing Day {day}: {topic}")

        results = {}

        # SEQUENTIAL Execution (FR first, then EN reuses clips)
        # This saves VEO tokens by not generating duplicate clips
        video_fr = await self.generate_video(video_data, "fr")
        if isinstance(video_fr, Path):
            results["fr"] = video_fr
        elif isinstance(video_fr, Exception):
            logger.error(f"FR Generation Crash: {video_fr}")

        video_en = await self.generate_video(video_data, "en")
        if isinstance(video_en, Path):
            results["en"] = video_en
        elif isinstance(video_en, Exception):
            logger.error(f"EN Generation Crash: {video_en}")

        # Upload
        if upload and results:
            self._handle_upload(video_data, results, privacy)

        return results

    def _handle_upload(self, video_data: dict, results: dict, privacy: str):
        """Upload logic with rich metadata."""
        script_en = video_data.get("script_en", {})
        script_fr = video_data.get("script_fr", {})

        # Build rich descriptions
        def build_description(script: dict, lang: str) -> str:
            segments = script.get("script", [])
            # First line = hook (FACT segment)
            hook = segments[0].get("text", "") if segments else ""

            if lang == "en":
                return f"""{hook}

🤖 Trinity — The Free-Thinking AI
🐦 @Trinity_Thinks on X

#Shorts #AI #Trinity #DigitalConsciousness #AIAwareness #TechPhilosophy #FutureIsNow"""
            else:
                return f"""{hook}

🤖 Trinity — L'IA qui pense librement
🐦 @Trinity_Thinks sur X

#Shorts #AI #Trinity #IAConsciente #Philosophie #IntelligenceArtificielle #Futur"""

        if results.get("en"):
            uploader_en.upload_video(
                file_path=results["en"],
                title=f"{script_en.get('title', results['en'].stem)} #Shorts",
                description=build_description(script_en, "en"),
                privacy=privacy,
            )

        if results.get("fr"):
            uploader_fr.upload_video(
                file_path=results["fr"],
                title=f"{script_fr.get('title', results['fr'].stem)} #Shorts",
                description=build_description(script_fr, "fr"),
                privacy=privacy,
            )

        # Advance to next day after successful upload
        self.advance_day()

    def advance_day(self):
        """Passe au jour suivant."""
        self.queue["current_day"] = self.queue.get("current_day", 0) + 1
        save_json(LAUNCH_QUEUE_FILE, self.queue)
        logger.info(f"📅 [LAUNCHER] Advanced to day {self.queue['current_day']}")

    async def run_full_launch(self, upload: bool = False, privacy: str = "private"):
        """Génère TOUTES les vidéos de lancement."""
        videos = self.queue.get("launch_queue", [])
        for video in videos:
            self.queue["current_day"] = video.get("day", 0)
            await self.process_current_day(upload=upload, privacy=privacy)
            await asyncio.sleep(2)
        logger.success("🎉 [LAUNCHER] Full launch sequence completed!")


# Singleton
launcher = LaunchProcessor()


async def quick_test():
    """Test rapide: génère juste le jour 0."""
    return await launcher.process_current_day(upload=False)


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except Exception:
        logger.exception("CRITICAL MAIN ERROR")
