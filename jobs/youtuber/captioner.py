"""
JOBS/YOUTUBER/CAPTIONER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CAPTIONER (SRT GENERATOR) 💬
PURPOSE: Création de sous-titres .srt via Whisper transcription.
══════════════════════════════════════════════════════════════════════════════
"""

import datetime
from pathlib import Path
from loguru import logger


def format_timestamp(seconds: float):
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class Captioner:
    def __init__(self):
        self.model = None

    def _load_whisper(self):
        """Lazy load whisper model"""
        if self.model is None:
            try:
                from faster_whisper import WhisperModel

                # Use 'base' for speed, 'small' for accuracy
                self.model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("🎤 [CAPTIONER] Whisper model loaded (base)")
            except Exception as e:
                logger.warning(f"⚠️ [CAPTIONER] Whisper load failed: {e}")
                self.model = None
        return self.model

    def create_srt_from_audio(self, audio_path: Path, lang: str = "fr") -> Path:
        """
        Transcribes audio with Whisper and generates word-level SRT.
        Returns path to SRT file.
        """
        srt_path = audio_path.with_suffix(".srt")
        model = self._load_whisper()

        if model is None:
            logger.warning("⚠️ [CAPTIONER] No Whisper, skipping SRT")
            return None

        try:
            # Transcribe with word-level timestamps
            segments, info = model.transcribe(
                str(audio_path),
                language=lang[:2],  # "fr" or "en"
                word_timestamps=True,
            )

            with open(srt_path, "w", encoding="utf-8") as f:
                idx = 1
                # Group words into 3-4 word chunks for karaoke style
                current_chunk = []
                chunk_start = None

                for segment in segments:
                    if not hasattr(segment, "words") or not segment.words:
                        # Fallback: use segment text as single block
                        f.write(f"{idx}\n")
                        f.write(
                            f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n"
                        )
                        f.write(f"{segment.text.strip()}\n\n")
                        idx += 1
                        continue

                    for word in segment.words:
                        if chunk_start is None:
                            chunk_start = word.start

                        current_chunk.append(word.word.strip())

                        # Write chunk every 4 words
                        if len(current_chunk) >= 4:
                            f.write(f"{idx}\n")
                            f.write(
                                f"{format_timestamp(chunk_start)} --> {format_timestamp(word.end)}\n"
                            )
                            f.write(f"{' '.join(current_chunk)}\n\n")
                            idx += 1
                            current_chunk = []
                            chunk_start = None

                # Write remaining words
                if current_chunk and chunk_start is not None:
                    last_word_end = chunk_start + 0.5  # Fallback duration
                    f.write(f"{idx}\n")
                    f.write(
                        f"{format_timestamp(chunk_start)} --> {format_timestamp(last_word_end)}\n"
                    )
                    f.write(f"{' '.join(current_chunk)}\n\n")

            logger.success(f"✅ [CAPTIONER] SRT created: {srt_path.name}")
            return srt_path

        except Exception as e:
            logger.error(f"❌ [CAPTIONER] Transcription failed: {e}")
            return None


captioner = Captioner()
