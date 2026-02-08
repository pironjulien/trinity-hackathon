from pathlib import Path
import os
import imageio_ffmpeg
from loguru import logger
from moviepy import VideoFileClip, concatenate_videoclips

logger.info("--- DIAGNOSTIC MULTI-CLIP START ---")
exe = imageio_ffmpeg.get_ffmpeg_exe()
os.environ["IMAGEIO_FFMPEG_EXE"] = exe
logger.info(f"FFMPEG: {exe}")

base = Path(
    r"c:\Users\julie\OneDrive\Documents\Travail\trinity\memories\youtuber\video_clips"
)
files = [
    base / "day00_l_eveil_fr_00_fact.mp4",
    base / "day00_l_eveil_fr_01_truth.mp4",
    base / "day00_l_eveil_fr_02_reconciliation.mp4",
]

clips = []
for f in files:
    logger.info(f"Loading {f.name}...")
    try:
        c = VideoFileClip(str(f), audio=False)
        logger.info(f"  Duration: {c.duration}")
        clips.append(c)
    except Exception as e:
        logger.error(f"  ERROR loading {f.name}: {e}")

logger.info(f"Concatenating {len(clips)} clips (CHAIN)...")
try:
    final = concatenate_videoclips(clips, method="chain")
    logger.info(f"Total Duration: {final.duration}")
    logger.info("Writing 1s test...")
    final.subclip(0, 1).write_videofile("test_multi.mp4", codec="libx264", audio=False)
    logger.success("SUCCESS")
except Exception as e:
    logger.error(f"ERROR: {e}")

logger.info("--- DIAGNOSTIC MULTI-CLIP END ---")
