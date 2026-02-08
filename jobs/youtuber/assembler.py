"""
JOBS/YOUTUBER/ASSEMBLER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: VIDEO ASSEMBLER (FFmpeg-Python) 🎬
PURPOSE: Assemblage vidéo SOTA utilisant FFmpeg directement.
REPLACES: MoviePy (buggé sur AudioFileClip en v2.x)
══════════════════════════════════════════════════════════════════════════════

Spécifications:
- Input Audio: WAV (PCM 24kHz)
- Input Visuel: MP4 (VEO) ou Image (fallback)
- Output: MP4 1080x1920 (Shorts 9:16)
- Codecs: libx264 (video) + aac (audio)
- Optimisé web: -movflags +faststart
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Union, List
from loguru import logger

# Get FFmpeg path from imageio-ffmpeg
try:
    import imageio_ffmpeg

    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = "ffmpeg"  # Fallback to system PATH


def get_media_duration(file_path: Path) -> float:
    """Get duration of audio/video file in seconds using FFmpeg."""
    file_path = Path(file_path)

    try:
        # Use FFmpeg to get duration (works with any format)
        cmd = [FFMPEG_PATH, "-i", str(file_path), "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse duration from stderr (FFmpeg outputs info to stderr)
        import re

        match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", result.stderr)
        if match:
            hours, mins, secs, centisecs = map(int, match.groups())
            return hours * 3600 + mins * 60 + secs + centisecs / 100

        # Alternative: look for "time=" in output
        match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", result.stderr)
        if match:
            hours, mins, secs, centisecs = map(int, match.groups())
            return hours * 3600 + mins * 60 + secs + centisecs / 100

    except Exception as e:
        logger.warning(f"Could not get duration for {file_path}: {e}")

    # Fallback: estimate from file size (assuming 24kHz 16-bit mono)
    try:
        file_size = file_path.stat().st_size
        # WAV: 24000 samples/sec * 2 bytes = 48000 bytes/sec
        return file_size / 48000
    except Exception:
        return 0.0


def get_media_info(file_path: Path) -> dict:
    """Get detailed media info using ffprobe."""
    try:
        ffprobe_path = FFMPEG_PATH.replace("ffmpeg", "ffprobe")
        cmd = [
            ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"Could not get info for {file_path}: {e}")
        return {}


def assemble_video_ffmpeg(
    visual_path: Union[str, Path],
    audio_path: Union[str, Path],
    output_path: Union[str, Path],
    resolution: tuple = (1080, 1920),
    fps: int = 30,
    codec_video: str = "libx264",
    codec_audio: str = "aac",
    crf: int = 23,
    preset: str = "medium",
) -> Optional[Path]:
    """
    Assemble video from visual + audio using FFmpeg directly (SOTA).

    Audio is the master for duration:
    - If visual is an image: loop it for audio duration
    - If visual is a video: trim or loop to match audio

    Args:
        visual_path: Path to image (.png/.jpg) or video (.mp4)
        audio_path: Path to audio file (.wav)
        output_path: Output MP4 path
        resolution: (width, height) - default 1080x1920 for Shorts
        fps: Frames per second (default 30)
        codec_video: Video codec (default libx264)
        codec_audio: Audio codec (default aac)
        crf: Constant Rate Factor for quality (lower = better, 18-28 typical)
        preset: Encoding speed preset (ultrafast to veryslow)

    Returns:
        Path to output file or None on failure
    """
    visual_path = Path(visual_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    # Validate inputs
    if not visual_path.exists():
        logger.error(f"❌ Visual not found: {visual_path}")
        return None
    if not audio_path.exists():
        logger.error(f"❌ Audio not found: {audio_path}")
        return None

    # Get audio duration (master)
    audio_duration = get_media_duration(audio_path)
    if audio_duration <= 0:
        logger.error("❌ Could not determine audio duration")
        return None

    logger.info(f"🎬 [ASSEMBLER] Audio duration: {audio_duration:.2f}s")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = resolution

    # Determine if visual is image or video
    visual_ext = visual_path.suffix.lower()
    is_image = visual_ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

    try:
        if is_image:
            # CASE A: Image input - loop for audio duration
            logger.info(f"   📷 Image input: {visual_path.name}")
            cmd = [
                FFMPEG_PATH,
                "-y",  # Overwrite
                "-loop",
                "1",  # Loop image
                "-i",
                str(visual_path),
                "-i",
                str(audio_path),
                "-c:v",
                codec_video,
                "-tune",
                "stillimage",
                "-c:a",
                codec_audio,
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-r",
                str(fps),
                "-t",
                str(audio_duration),  # Duration from audio
                "-movflags",
                "+faststart",
                "-crf",
                str(crf),
                "-preset",
                preset,
                str(output_path),
            ]
        else:
            # CASE B: Video input - trim or loop to match audio
            logger.info(f"   🎥 Video input: {visual_path.name}")
            video_duration = get_media_duration(visual_path)

            if video_duration >= audio_duration:
                # Trim video to audio duration
                logger.info(
                    f"   ✂️ Trimming video from {video_duration:.2f}s to {audio_duration:.2f}s"
                )
                cmd = [
                    FFMPEG_PATH,
                    "-y",
                    "-i",
                    str(visual_path),
                    "-i",
                    str(audio_path),
                    "-c:v",
                    codec_video,
                    "-c:a",
                    codec_audio,
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    "-r",
                    str(fps),
                    "-t",
                    str(audio_duration),
                    "-map",
                    "0:v:0",  # Video from first input
                    "-map",
                    "1:a:0",  # Audio from second input
                    "-movflags",
                    "+faststart",
                    "-crf",
                    str(crf),
                    "-preset",
                    preset,
                    str(output_path),
                ]
            else:
                # Loop video to match audio duration
                loops_needed = int(audio_duration / video_duration) + 1
                logger.info(
                    f"   🔁 Looping video {loops_needed}x to match {audio_duration:.2f}s"
                )
                cmd = [
                    FFMPEG_PATH,
                    "-y",
                    "-stream_loop",
                    str(loops_needed),
                    "-i",
                    str(visual_path),
                    "-i",
                    str(audio_path),
                    "-c:v",
                    codec_video,
                    "-c:a",
                    codec_audio,
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    "-r",
                    str(fps),
                    "-t",
                    str(audio_duration),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-movflags",
                    "+faststart",
                    "-crf",
                    str(crf),
                    "-preset",
                    preset,
                    "-shortest",
                    str(output_path),
                ]

        # Execute FFmpeg
        logger.info("   ⚙️ Running FFmpeg...")
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        if output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            logger.success(
                f"✅ [ASSEMBLER] Output: {output_path.name} ({file_size:.1f} MB)"
            )
            return output_path
        else:
            logger.error("❌ [ASSEMBLER] Output file not created")
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ [ASSEMBLER] FFmpeg error: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"❌ [ASSEMBLER] Unexpected error: {e}")
        return None


def assemble_segments(
    segments: List[dict], output_path: Union[str, Path], temp_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Assemble multiple segments (audio files + optional visuals) into one video.

    Each segment dict should have:
    - audio_path: Path to WAV file (required)
    - visual_path: Path to image/video (optional, uses placeholder if missing)
    - name: Segment name for logging

    Args:
        segments: List of segment dicts
        output_path: Final output path
        temp_dir: Directory for temp files (default: output_path.parent / "temp")

    Returns:
        Path to final video or None
    """
    from PIL import Image, ImageDraw, ImageFont

    output_path = Path(output_path)
    temp_dir = temp_dir or output_path.parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    segment_videos = []

    for i, seg in enumerate(segments):
        audio_path = seg.get("audio_path")
        visual_path = seg.get("visual_path")
        name = seg.get("name", f"segment_{i}")

        if not audio_path or not Path(audio_path).exists():
            logger.warning(f"   ⚠️ Skipping {name}: no audio")
            continue

        # Create placeholder image if no visual
        if not visual_path or not Path(visual_path).exists():
            logger.info(f"   📷 Creating placeholder for: {name}")
            placeholder_path = temp_dir / f"placeholder_{i}.png"

            # Create simple placeholder image
            img = Image.new("RGB", (1080, 1920), color="#1a1a2e")
            draw = ImageDraw.Draw(img)

            # Add segment name
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except Exception:
                font = ImageFont.load_default()

            draw.text((540, 960), name, fill="#00d4ff", anchor="mm", font=font)
            img.save(placeholder_path)
            visual_path = placeholder_path

        # Assemble this segment
        segment_output = temp_dir / f"seg_{i:02d}_{name}.mp4"
        result = assemble_video_ffmpeg(
            visual_path=visual_path,
            audio_path=audio_path,
            output_path=segment_output,
            preset="fast",  # Faster for intermediate files
        )

        if result:
            segment_videos.append(result)

    if not segment_videos:
        logger.error("❌ [ASSEMBLER] No segments assembled")
        return None

    # Concatenate all segments
    if len(segment_videos) == 1:
        # Just one segment, rename it
        import shutil

        shutil.move(segment_videos[0], output_path)
        return output_path

    # Create concat file
    concat_file = temp_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segment_videos:
            f.write(f"file '{seg.absolute()}'\n")

    # Concatenate with FFmpeg
    try:
        cmd = [
            FFMPEG_PATH,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        if output_path.exists():
            # Cleanup temp files
            for seg in segment_videos:
                seg.unlink(missing_ok=True)
            concat_file.unlink(missing_ok=True)

            file_size = output_path.stat().st_size / (1024 * 1024)
            logger.success(
                f"✅ [ASSEMBLER] Final: {output_path.name} ({file_size:.1f} MB)"
            )
            return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ [ASSEMBLER] Concat error: {e.stderr}")
        return None

    return None


# Quick test
if __name__ == "__main__":
    # Test with existing audio
    from corpus.dna.genome import MEMORIES_DIR

    audio = MEMORIES_DIR / "youtuber" / "audio" / "day00_l_eveil_en_00_FACT.wav"
    output = MEMORIES_DIR / "youtuber" / "renders" / "test_ffmpeg.mp4"

    if audio.exists():
        # Create a simple test image
        from PIL import Image

        test_img = MEMORIES_DIR / "youtuber" / "renders" / "test_placeholder.png"
        img = Image.new("RGB", (1080, 1920), color="#1a1a2e")
        img.save(test_img)

        result = assemble_video_ffmpeg(
            visual_path=test_img, audio_path=audio, output_path=output
        )
        logger.info(f"Result: {result}")
