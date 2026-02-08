"""
JOBS/YOUTUBER/EDITOR.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: EDITOR (BARE METAL + SUBS + OUTRO) ✂️
FIX: Ajout Outro + Incrustation Sous-titres (Hardsub).
══════════════════════════════════════════════════════════════════════════════
"""

import os
import subprocess
import random
import shutil
import re
from pathlib import Path
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from corpus.dna.genome import PROFESSIONS_DIR, MEMORIES_DIR
from jobs.youtuber.constants import BANNERS
from corpus.soma.cells import load_json

ASSETS_DIR = PROFESSIONS_DIR / "youtuber" / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
OUTRO_DIR = ASSETS_DIR / "outro"
OUTPUT_BASE = MEMORIES_DIR / "youtuber" / "output"
OUTPUT_DIR = OUTPUT_BASE / "renders"
TEMP_DIR = OUTPUT_BASE / "temp"
FONT_DIR = PROFESSIONS_DIR / "youtuber" / "fonts"
GOOGLE_SANS_BOLD = FONT_DIR / "GoogleSans-Bold.ttf"

for d in [OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class VideoEditor:
    def __init__(self):
        self.ffmpeg_bin = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        try:
            import imageio_ffmpeg

            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.exists(exe):
                return exe
        except Exception:
            pass
        return "ffmpeg"

    def assemble_video(self, plan_path: Path, lang: str = "en") -> Path:
        """
        Assemble final video from visual plan.

        VEO 3.1 MODE: If plan has native_audio=True, videos already contain audio.
        LEGACY MODE: Separate video + audio files overlayed.
        """
        plan = load_json(plan_path)
        if not plan:
            return None

        import re

        raw_title = plan.get("title", "video")
        # SANITIZE: Remove apostrophes, accents, and special chars that break FFmpeg
        title_safe = re.sub(
            r"[^a-zA-Z0-9_]",
            "",
            raw_title.replace("'", "").replace("'", "").replace(" ", "_"),
        )[:30]
        if not title_safe:
            title_safe = "video"
        # Temp file for clean video (before subs)
        temp_video = TEMP_DIR / f"clean_{title_safe}_{lang}.mp4"
        final_output = OUTPUT_DIR / f"{title_safe}_{lang}.mp4"

        segments = plan.get("segments", [])
        native_audio_mode = plan.get("native_audio", False)

        # VEO 3.1 NATIVE AUDIO MODE
        if native_audio_mode:
            logger.info("🔊 [EDITOR] VEO 3.1 Native Audio Mode - Videos contain audio")
            valid_segs = [s for s in segments if s.get("video_path")]
        else:
            # Legacy mode: require both video and audio
            valid_segs = [
                s for s in segments if s.get("video_path") and s.get("audio_path")
            ]

        if not valid_segs:
            logger.error("❌ [EDITOR] No valid segments found")
            return None

        # VALIDATION: Ensure ALL segments have video_path (not just some)
        missing_segments = [
            i for i, s in enumerate(segments) if not s.get("video_path")
        ]
        if missing_segments:
            logger.error(f"❌ [EDITOR] Missing video for segments: {missing_segments}")
            logger.error("   ⚠️ Aborting assembly - all segments must have valid videos")
            return None

        # PRE-CALCULATE segment durations (needed for SRT timing)
        for seg in valid_segs:
            video_dur = self._get_duration(seg["video_path"])
            if native_audio_mode:
                # In native mode, video duration = audio duration (they're together)
                seg["_seg_dur"] = video_dur + 0.5  # +0.5s pause between segments
            else:
                audio_dur = self._get_duration(seg["audio_path"])
                # Use max to ensure ALL audio plays (video loops if needed)
                seg["_seg_dur"] = max(
                    video_dur, audio_dur + 1.0
                )  # +1s pause after speech

        # 1. GENERATE SRT & BANNER (now with correct seg durations)
        full_srt_path = TEMP_DIR / f"{title_safe}_{lang}.srt"
        self._generate_full_srt(valid_segs, full_srt_path, native_audio_mode)
        banner_path = self._generate_banner(lang)

        # 2. ASSEMBLE (PASS 1)
        inputs = []
        filter_complex = []
        concat_v = []
        concat_a = []
        idx = 0

        for i, seg in enumerate(valid_segs):
            seg_dur = seg["_seg_dur"]
            v_lbl = f"v{i}"
            a_lbl = f"a{i}"

            if native_audio_mode:
                # VEO 3.1: Video contains audio - NO stream_loop (videos are exact duration)
                inputs.extend(["-i", str(seg["video_path"])])
                v_idx = idx
                idx += 1

                # Video: scale and trim (with setsar=1 to fix VEO SAR issues)
                filter_complex.append(
                    f"[{v_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,trim=duration={seg_dur},setpts=PTS-STARTPTS[{v_lbl}]"
                )

                # Audio: from same video file, pad with silence if needed
                video_dur = self._get_duration(seg["video_path"])
                if seg_dur > video_dur:
                    filter_complex.append(
                        f"[{v_idx}:a]apad=pad_dur={seg_dur - video_dur}[{a_lbl}]"
                    )
                else:
                    filter_complex.append(
                        f"[{v_idx}:a]atrim=duration={seg_dur}[{a_lbl}]"
                    )
            else:
                # LEGACY: Separate video and audio files
                inputs.extend(["-stream_loop", "-1", "-i", str(seg["video_path"])])
                v_idx = idx
                idx += 1
                inputs.extend(["-i", str(seg["audio_path"])])
                a_idx = idx
                idx += 1

                audio_dur = self._get_duration(seg["audio_path"])

                # Video: use calculated segment duration (with setsar=1 for SAR consistency)
                filter_complex.append(
                    f"[{v_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,trim=duration={seg_dur},setpts=PTS-STARTPTS[{v_lbl}]"
                )

                # Audio: pad with silence to match segment duration
                if seg_dur > audio_dur:
                    filter_complex.append(
                        f"[{a_idx}:a]apad=pad_dur={seg_dur - audio_dur}[{a_lbl}]"
                    )
                else:
                    filter_complex.append(
                        f"[{a_idx}:a]atrim=duration={seg_dur}[{a_lbl}]"
                    )

            concat_v.append(f"[{v_lbl}]")
            concat_a.append(f"[{a_lbl}]")

            # SOTA 2026: Flash Transitions between segments
            # Clean white/black flash (more professional than RGB glitch)
            FLASH_DURATION = 0.15
            is_last_segment = i == len(valid_segs) - 1

            if not is_last_segment:
                flash_v_lbl = f"flash{i}"
                flash_a_lbl = f"flashA{i}"

                # White flash: color source with quick fade
                filter_complex.append(
                    f"color=c=white:s=1080x1920:d={FLASH_DURATION},"
                    f"format=yuv420p,setsar=1[{flash_v_lbl}]"
                )
                concat_v.append(f"[{flash_v_lbl}]")

                # Flash audio: short silence (cleaner than buzz)
                filter_complex.append(
                    f"anullsrc=r=48000:cl=stereo,atrim=0:{FLASH_DURATION}[{flash_a_lbl}]"
                )
                concat_a.append(f"[{flash_a_lbl}]")

        # Final Flash before Outro (longer, with fade)
        FINAL_FLASH_DURATION = 0.25
        if valid_segs:
            # White flash then black fade before outro
            filter_complex.append(
                f"color=c=white:s=1080x1920:d={FINAL_FLASH_DURATION},"
                f"format=yuv420p,setsar=1,fade=t=out:st=0.1:d=0.15[v_flash_final]"
            )
            concat_v.append("[v_flash_final]")

            filter_complex.append(
                f"anullsrc=r=48000:cl=stereo,atrim=0:{FINAL_FLASH_DURATION}[a_flash_final]"
            )
            concat_a.append("[a_flash_final]")

            logger.info("⚡ [EDITOR] Flash transitions added (inter-segment + final)")

        # Outro Logic
        outro_path = OUTRO_DIR / "outro.mp4"

        if outro_path.exists():
            inputs.extend(["-i", str(outro_path)])
            out_v_idx = idx
            idx += 1

            # Check for audio stream in outro
            outro_dur = self._get_duration(outro_path)
            has_audio = self._has_audio(outro_path)

            # Visuals (with setsar=1 for SAR consistency)
            filter_complex.append(
                f"[{out_v_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,setpts=PTS-STARTPTS[v_outro]"
            )
            concat_v.append("[v_outro]")

            # Audio (Use embedded audio if present, else generate silence)
            if has_audio:
                # Use audio from same input file as video (no need for second input)
                concat_a.append(f"[{out_v_idx}:a]")
            else:
                # Generate silent audio matching outro duration
                filter_complex.append(
                    f"anullsrc=r=44100:cl=stereo:d={outro_dur}[a_outro_silence]"
                )
                concat_a.append("[a_outro_silence]")

        # Concat (CRITICAL: Must interleave [v0][a0][v1][a1]... for n segments)
        # n_seg = base segments + glitch (if any) + outro (if any)
        n_seg = len(concat_v)  # Total streams = segments + glitch + outro
        concat_streams = []
        for v_lbl, a_lbl in zip(concat_v, concat_a):
            concat_streams.append(v_lbl)
            concat_streams.append(a_lbl)
        filter_complex.append(
            f"{''.join(concat_streams)}concat=n={n_seg}:v=1:a=1[v_main][a_main]"
        )
        last_v, last_a = "[v_main]", "[a_main]"

        # Music with SOTA 2026 Sidechain Ducking
        # Music lowers automatically when Trinity speaks
        music_files = list(MUSIC_DIR.glob("*.mp3"))
        if music_files:
            # NO stream_loop (causes infinite processing) - use atrim instead
            inputs.extend(["-i", str(random.choice(music_files))])
            m_idx = idx
            idx += 1

            # Calculate total video duration for music trim
            total_video_dur = sum(seg["_seg_dur"] for seg in valid_segs)
            total_video_dur += (
                (len(valid_segs) - 1) * 0.15 + 0.25 + 8
            )  # flashes + outro

            # Sidechaincompress: Voice controls music volume
            # - Base volume: 150% (VERY loud for impact)
            # - When voice detected: compresses to ~40%
            # - Smooth attack/release for natural feel
            filter_complex.append(
                f"[{m_idx}:a]atrim=0:{total_video_dur},asetpts=PTS-STARTPTS,volume=1.5[bgm_raw];"
                f"{last_a}asplit=2[voice][voice_sc];"
                f"[bgm_raw][voice_sc]sidechaincompress="
                f"threshold=0.02:ratio=6:attack=50:release=300:makeup=1[bgm_ducked];"
                f"[voice][bgm_ducked]amix=inputs=2:duration=first[a_mix]"
            )
            last_a = "[a_mix]"

        # Banner (only on main content, NOT on outro)
        # SOTA 2026: Dynamic Banner Configuration from State
        youtuber_state = load_json(MEMORIES_DIR / "youtuber" / "state.json", default={})
        placard_enabled = youtuber_state.get(
            "placard_enabled", False
        )  # Default OFF as per user request
        placard_text = youtuber_state.get("placard_text", "")

        if placard_enabled:
            banner_path = self._generate_banner(lang, placard_text)
            inputs.extend(["-i", str(banner_path)])
            b_idx = idx
            idx += 1
            # Calculate main content duration (using segment durations with pauses)
            main_dur = sum(seg["_seg_dur"] for seg in valid_segs)
            filter_complex.append(
                f"{last_v}[{b_idx}:v]overlay=0:0:enable='lt(t,{main_dur})'[v_final]"
            )
            last_v = "[v_final]"

        # SOTA 2026: Fade Out at End (2s video + audio fade)
        # Calculate total duration for fade timing
        total_dur = sum(seg["_seg_dur"] for seg in valid_segs)
        # Add flash durations (inter-segment + final)
        total_dur += (
            len(valid_segs) - 1
        ) * 0.15 + 0.25  # inter-segment flashes + final flash
        # Add outro duration (~8s)
        total_dur += 8
        fade_start = total_dur - 2.5  # Start fade 2.5s before end

        filter_complex.append(f"{last_v}fade=t=out:st={fade_start}:d=2[v_faded]")
        last_v = "[v_faded]"

        filter_complex.append(f"{last_a}afade=t=out:st={fade_start}:d=2[a_faded]")
        last_a = "[a_faded]"

        # RENDER PASS 1
        cmd = (
            [self.ffmpeg_bin, "-y"]
            + inputs
            + [
                "-filter_complex",
                ";".join(filter_complex),
                "-map",
                last_v,
                "-map",
                last_a,
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                str(temp_video),
            ]
        )

        try:
            subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
        except Exception as e:
            logger.error(f"Render Pass 1 Failed: {e}")
            return None

        # 3. BURN SUBS (PASS 2 - OPTIONAL)
        subtitles_enabled = youtuber_state.get("subtitles_enabled", True)

        if subtitles_enabled:
            # Note: on Windows paths in filter need escaping
            srt_escaped = str(full_srt_path).replace("\\", "/").replace(":", "\\:")

            # Subtitles: FontSize=22, Google Sans font, MarginV=150 to stay above mobile controls
            fontsdir_escaped = str(FONT_DIR).replace("\\", "/").replace(":", "\\:")
            cmd_subs = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(temp_video),
                "-vf",
                f"subtitles='{srt_escaped}':fontsdir='{fontsdir_escaped}':force_style='Fontname=Google Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H000000,Outline=2,MarginV=60'",
                "-c:a",
                "copy",
                str(final_output),
            ]

            try:
                subprocess.run(cmd_subs, check=True, stderr=subprocess.PIPE, text=True)
                logger.success(f"✅ Final Video (Subs): {final_output.name}")
                return final_output
            except subprocess.CalledProcessError as e:
                logger.error(f"Subtitle Burn Failed: {e}")
                logger.error(
                    f"FFmpeg stderr: {e.stderr[:500] if e.stderr else 'No stderr'}"
                )
                return temp_video  # Return video without subs if fail
            except Exception as e:
                logger.error(f"Subtitle Burn Exception: {e}")
                return temp_video
        else:
            # Skip subs, just rename temp to final
            logger.info("⏩ Subtitles disabled, skipping Pass 2")
            if final_output.exists():
                final_output.unlink()
            temp_video.rename(final_output)
            logger.success(f"✅ Final Video (No Subs): {final_output.name}")
            return final_output
            return temp_video

    def _generate_full_srt(
        self, segments, output_path, native_audio_mode: bool = False
    ):
        """
        Generates SRT using Whisper transcription with apostrophe merging.

        In NATIVE AUDIO MODE: Whisper transcribes from video files (audio is embedded).
        In LEGACY MODE: Whisper transcribes from separate audio .wav files.
        """
        import datetime

        def fmt(t):
            td = datetime.timedelta(seconds=t)
            total = int(td.total_seconds())
            ms = int((t - int(t)) * 1000)
            return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d},{ms:03d}"

        lang = "fr" if "_fr" in str(output_path) else "en"
        all_entries = []
        current_offset = 0.0

        for seg in segments:
            # In native audio mode, use video_path for transcription
            if native_audio_mode:
                media_path = Path(seg["video_path"])
            else:
                media_path = Path(seg["audio_path"])

            dur = self._get_duration(str(media_path))

            try:
                from faster_whisper import WhisperModel

                if not hasattr(self, "_whisper_model"):
                    logger.info("🎤 Loading Whisper model (base, CPU)...")
                    self._whisper_model = WhisperModel(
                        "base", device="cpu", compute_type="int8"
                    )

                segments_whisper, _ = self._whisper_model.transcribe(
                    str(media_path), language=lang, word_timestamps=True
                )

                # Collect all words first
                all_words = []
                for ws in segments_whisper:
                    if hasattr(ws, "words") and ws.words:
                        for word in ws.words:
                            all_words.append(
                                {
                                    "text": word.word.strip(),
                                    "start": word.start,
                                    "end": word.end,
                                }
                            )

                # Merge apostrophe words: "n'" + "'êtes" = "n'êtes"
                merged_words = []
                i = 0
                while i < len(all_words):
                    w = all_words[i]
                    # If current word ends with ' and next exists
                    if i + 1 < len(all_words):
                        next_w = all_words[i + 1]
                        # Merge if current ends with ' or next starts with '
                        if w["text"].endswith("'") or next_w["text"].startswith("'"):
                            # Keep apostrophe: n' + êtes = n'êtes
                            merged_text = w["text"]
                            if next_w["text"].startswith("'"):
                                merged_text += next_w["text"]  # Keep the apostrophe
                            else:
                                merged_text += next_w["text"]
                            merged_words.append(
                                {
                                    "text": merged_text,
                                    "start": w["start"],
                                    "end": next_w["end"],
                                }
                            )
                            i += 2
                            continue
                    merged_words.append(w)
                    i += 1

                # Group into 2-word chunks
                for j in range(0, len(merged_words), 2):
                    chunk_words = merged_words[j : j + 2]
                    if chunk_words:
                        all_entries.append(
                            {
                                "start": current_offset + chunk_words[0]["start"],
                                "end": current_offset + chunk_words[-1]["end"],
                                "text": " ".join(cw["text"] for cw in chunk_words),
                            }
                        )

            except Exception as e:
                logger.warning(f"⚠️ Whisper failed: {e}")
                text = seg.get("text", "")
                if text:
                    words = text.split()
                    chunk_dur = dur / max(1, len(words) // 2)
                    for k in range(0, len(words), 2):
                        all_entries.append(
                            {
                                "start": current_offset + k * chunk_dur / 2,
                                "end": current_offset + (k + 2) * chunk_dur / 2,
                                "text": " ".join(words[k : k + 2]),
                            }
                        )

            # Use segment duration (includes pause) for offset, not just audio
            seg_dur = seg.get("_seg_dur", dur)
            current_offset += seg_dur

        with open(output_path, "w", encoding="utf-8") as f:
            for idx, entry in enumerate(all_entries, 1):
                f.write(
                    f"{idx}\n{fmt(entry['start'])} --> {fmt(entry['end'])}\n{entry['text']}\n\n"
                )

        logger.success(f"✅ SRT: {len(all_entries)} entries")

    def _has_audio(self, path):
        cmd = [self.ffmpeg_bin, "-i", str(path)]
        try:
            r = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
            # Look for "Audio:" in stream info
            return "Audio:" in r.stderr
        except Exception:
            return False

    def _get_duration(self, path):
        # ... (keep existing robust logic)
        cmd = [self.ffmpeg_bin, "-i", str(path)]
        try:
            r = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
            m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", r.stderr)
            if m:
                h, m, s = map(float, m.groups())
                return h * 3600 + m * 60 + s
        except Exception:
            pass
        return 5.0

    def _generate_banner(self, lang: str, custom_text: str = "") -> str:
        """
        Generate or retrieve banner image.
        PERSISTENCE: Stores in memories/youtuber/output/visuals/banner_{lang}.png
        """
        visuals_dir = OUTPUT_BASE / "visuals"
        visuals_dir.mkdir(parents=True, exist_ok=True)
        path = visuals_dir / f"banner_{lang}.png"

        # If custom text provided, ALWAYS regenerate/overwrite
        if custom_text:
            logger.info(f"🎨 [EDITOR] Regenerating Banner (Custom Text): {custom_text}")
            self._generate_banner_image_logic(path, lang, custom_text)
            return str(path)

        # If no custom text, stick to default asset if exists
        if path.exists():
            return str(path)

        # If missing, regenerate default
        logger.info(f"🎨 [EDITOR] Generating Default Banner: {path}")
        self._generate_banner_image_logic(path, lang)
        return str(path)

    def _generate_banner_image_logic(
        self, path: Path, lang: str, custom_text: str = ""
    ):
        """
        Mix existing banner asset with dynamic text.
        Strategy:
        1. Load authorized 'banner_{lang}.png' from assets (The "Real" Pancarte)
        2. Draw text on top
        """
        # Source Asset (Restored from Git)
        source_asset = ASSETS_DIR / f"banner_{lang}.png"

        if source_asset.exists():
            img = Image.open(source_asset).convert("RGBA")
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
        else:
            logger.warning(
                f"⚠️ [EDITOR] Missing banner asset: {source_asset}. Using black fallback."
            )
            img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 1920 - 420), (1080, 1920 - 240)], fill=(0, 0, 0, 210))

        draw = ImageDraw.Draw(img)

        # Localized Banner Text
        # Localized Banner Text (Single Source of Truth)
        title, default_subtitle = BANNERS.get(lang, BANNERS["en"])

        # Use custom text if provided, otherwise default subtitle
        subtitle = custom_text if custom_text else default_subtitle

        try:
            font_title = ImageFont.truetype(str(GOOGLE_SANS_BOLD), 90)
            font_sub = ImageFont.truetype(str(GOOGLE_SANS_BOLD), 55)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = font_title

        # Calculate text widths for centering
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        sub_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        sub_width = sub_bbox[2] - sub_bbox[0]

        # Centered X positions (1080 / 2 - width / 2)
        title_x = (1080 - title_width) // 2
        sub_x = (1080 - sub_width) // 2

        # Title "TRINITY" - centered
        draw.text((title_x, 1920 - 390), title, font=font_title, fill="white")
        # Subtitle - centered
        draw.text((sub_x, 1920 - 320), subtitle, font=font_sub, fill=(180, 180, 180))

        img.save(path)
        return path


editor = VideoEditor()
