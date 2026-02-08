"""
JOBS/YOUTUBER/VISUALS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: VISUAL GENERATOR (L'OEIL) 👁️
FIX: Priorité absolue à l'image fournie (Face Fidelity) vs hallucinations Matrix.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json

from pathlib import Path
from typing import Optional, List
from loguru import logger

try:
    from google.cloud import storage

    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

from corpus.soma.cells import save_json, load_json
from corpus.dna.genome import MEMORIES_DIR
from corpus.brain.gattaca import gattaca, ROUTE_SOCIAL

# Face Lock reference images directory
YOUTUBER_ASSETS_DIR = Path(__file__).parent / "assets"


class VisualAssembler:
    def __init__(self):
        self.output_dir = MEMORIES_DIR / "youtuber" / "output" / "visuals"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = MEMORIES_DIR / "youtuber" / "state.json"
        self._gcs_client = None

    def _get_gcs_client(self):
        if GCS_AVAILABLE and not self._gcs_client:
            try:
                self._gcs_client = storage.Client()  # type: ignore[possibly-undefined]
            except Exception:
                pass
        return self._gcs_client

    def _upload_to_gcs(self, local_path: Path, bucket_name: str) -> Optional[str]:
        client = self._get_gcs_client()
        if not client:
            return None
        try:
            bucket = client.bucket(bucket_name)
            blob_name = f"youtuber/assets/{local_path.name}"
            blob = bucket.blob(blob_name)
            if not blob.exists():
                blob.upload_from_filename(str(local_path))
            return f"gs://{bucket_name}/{blob_name}"
        except Exception:
            return None

    async def generate_video(
        self, prompt: str, target_path: Optional[Path] = None, veo_prompt: str = None
    ) -> Optional[Path]:
        """
        Génère une vidéo avec Veo 3.1 NATIVE AUDIO.

        Args:
            prompt: Fallback prompt (ancien format)
            target_path: Chemin de sortie
            veo_prompt: NOUVEAU - Prompt complet avec dialogue intégré pour audio natif
        """
        if target_path and target_path.exists():
            return target_path

        # VEO 3.1 CHARACTER BLOCK for face consistency
        CHARACTER_BLOCK = (
            "Same woman from reference image. A photorealistic cyberpunk woman with pale Caucasian features, "
            "high cheekbones, and a symmetrical face, featuring shoulder-length wavy hair that transitions "
            "from dark roots into glowing strands of neon cyan, electric blue, and violet, resembling flowing "
            "fiber-optic cables. Her most striking features are her piercing, iris-less luminous white eyes "
            "that emit a soft glow, and her skin which is overlayed with intricate, glowing circuitry patterns "
            "in teal and magenta that trace the contours of her forehead, cheeks, and jawline, creating a "
            "translucent digital skin effect. She exudes a synthetic, AI-generated aura, appearing to wear "
            "a bio-digital suit that blends seamlessly with the circuitry on her neck, bathed in cool, "
            "high-contrast cinematic lighting that emphasizes the bioluminescent elements of her design. "
        )

        # Use veo_prompt if provided (new format with dialogue), else fallback
        if veo_prompt:
            full_prompt = veo_prompt
            logger.info(f"🎬 [VEO 3.1] Native Audio Mode: {veo_prompt[:50]}...")
        else:
            # Legacy format - add character block
            full_prompt = (
                f"{CHARACTER_BLOCK}{prompt}. "
                f"Style: vertical 9:16, photorealistic, cinematic lighting, 8k, high resolution, dark tech atmosphere."
            )

        state = load_json(self.state_file, default={})

        # CHECK MOCK MODE
        if state.get("mock_mode", False):
            if not target_path:
                # Generate temp path if none provided
                target_path = self.output_dir / f"mock_{abs(hash(prompt))}.mp4"
            return await self._generate_mock_video(prompt, target_path)

        try:
            logger.info("🎬 [VEO 3.1] Generating with NATIVE AUDIO...")

            # FACE LOCK: SDK generate_videos correctly handles referenceImages
            result = await asyncio.wait_for(
                gattaca.route(
                    full_prompt,
                    route_id=ROUTE_SOCIAL,
                    use_face_lock=True,  # Re-enabled: SDK supports referenceImages
                    generate_audio=True,  # Request native audio
                ),
                timeout=180,
            )
            data = self._parse_result(result)

            if data.get("status") == "ok" and data.get("path"):
                final_path = Path(data.get("path"))
                if target_path:
                    import shutil

                    shutil.move(final_path, target_path)
                    final_path = target_path
                logger.success(
                    f"⚡ [VEO 3.1] Fast success (with audio): {final_path.name}"
                )
                return final_path

            # NO FALLBACK TO PRO - Credit Conservation Mode
            logger.error("❌ [VEO] Fast failed - no Pro fallback (credit conservation)")
            return None
        except Exception as e:
            logger.error(f"💥 [VEO] Error: {e}")
            return None

    async def _generate_mock_video(self, prompt: str, target_path: Path) -> Path:
        """Generates a dummy video using FFmpeg for testing (PIL based)."""
        logger.warning(f"🧪 [MOCK] Generating dummy video for: {prompt[:30]}...")

        # Ensure target dir exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp image with PIL
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (1080, 1920), color="black")
            draw = ImageDraw.Draw(img)

            # Draw text
            text = f"MOCK:\n{prompt[:30]}..."
            try:
                # Try to find a font, fallback to default
                font_path = Path(__file__).parent / "fonts" / "GoogleSans-Bold.ttf"
                font = ImageFont.truetype(str(font_path), 60)
            except Exception:
                font = ImageFont.load_default()

            # Simple centering logic
            draw.text((100, 900), text, font=font, fill="white")

            temp_img = target_path.with_suffix(".png")
            img.save(temp_img)

            # Convert to Video using FFmpeg
            cmd = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(temp_img),
                "-f",
                "lavfi",
                "-i",
                "sine=f=440:b=4:d=4",
                "-c:v",
                "libx264",
                "-t",
                "4",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(target_path),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if temp_img.exists():
                temp_img.unlink()

            return target_path

        except Exception as e:
            logger.error(f"❌ [MOCK] Failed: {e}")
            return None

    async def generate_all_segments(
        self, segments: List[dict], lang: str = "fr"
    ) -> List[Optional[Path]]:
        """
        Génère tous les segments vidéo avec Veo 3.1 (audio natif).
        SOTA 2026: Génération SÉQUENTIELLE (quota Veo).

        Visual Structure (3-segment format):
        - Segment 0 (FACT): Trinity speaks to camera
        - Segment 1 (TRUTH): Subject visual only (no Trinity)
        - Segment 2 (RECONCILIATION): Trinity + subject together
        """
        # CHARACTER_BLOCK for Trinity consistency
        TRINITY_BLOCK = (
            "Same woman from reference image. A photorealistic cyberpunk woman with "
            "shoulder-length wavy hair in neon cyan/violet, glowing white eyes, "
            "circuitry patterns on skin, wearing a bio-digital suit. "
        )

        results = []
        total = len(segments)

        for i, seg in enumerate(segments):
            target = seg.get("_target_path")
            visual_prompt = seg.get("visual", "")
            dialogue_text = seg.get("text", "")
            lang_label = "French" if lang == "fr" else "English"
            seg_type = seg.get("seg", "").upper()

            # VISUAL STRATEGY BY SEGMENT POSITION
            if i == 0:
                # FIRST SEGMENT: Trinity speaks to camera
                scene = f"{TRINITY_BLOCK}{visual_prompt}."
                if dialogue_text:
                    veo_prompt = f'{scene} She speaks directly to camera in {lang_label}, saying: "{dialogue_text}"'
                else:
                    veo_prompt = scene

            elif i == total - 1 and seg_type == "RECONCILIATION":
                # LAST SEGMENT: Trinity + subject together
                scene = f"{TRINITY_BLOCK}{visual_prompt}."
                if dialogue_text:
                    veo_prompt = f'{scene} She speaks warmly to camera in {lang_label}, saying: "{dialogue_text}"'
                else:
                    veo_prompt = scene

            else:
                # MIDDLE SEGMENTS: Subject visual only (NO Trinity)
                scene = (
                    f"{visual_prompt}. Cinematic 9:16 vertical format, photorealistic."
                )
                if dialogue_text:
                    # Voice-over style, not on-screen character
                    veo_prompt = f'{scene} A woman\'s voice in {lang_label} narrates: "{dialogue_text}"'
                else:
                    veo_prompt = scene

            logger.info(f"🎬 [VEO] Segment {i + 1}/{total} ({seg_type})")
            logger.debug(
                f"📝 Strategy: {'Trinity' if i == 0 or (i == total - 1 and seg_type == 'RECONCILIATION') else 'Subject only'}"
            )

            try:
                result = await self.generate_video(
                    prompt=visual_prompt,
                    target_path=target,
                    veo_prompt=veo_prompt,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"❌ [VEO] Segment {i + 1} failed: {e}")
                results.append(None)
        return results

    async def create_visual_plan(
        self, script_path: Path, audio_dir: Path = None
    ) -> Optional[Path]:
        """
        Crée un plan visuel pour l'éditeur.

        VEO 3.1 MODE: Les vidéos contiennent déjà l'audio natif.
        audio_dir est ignoré (gardé pour compatibilité).
        """
        script = load_json(script_path)
        if not script:
            return None

        segments = script.get("script", [])
        basename = script_path.stem.replace("script_", "")

        # Extract language from script
        lang = script.get("_meta", {}).get("lang") or script.get("lang", "en")

        for i, seg in enumerate(segments):
            seg["_target_path"] = (
                self.output_dir / f"video_{basename}_{i:02d}_{seg['seg']}.mp4"
            )

        video_paths = await self.generate_all_segments(segments, lang=lang)

        visual_segments = []
        for i, (seg, v_path) in enumerate(zip(segments, video_paths)):
            # VEO 3.1: Video contains audio - no separate audio file needed
            visual_segments.append(
                {
                    "video_path": str(v_path)
                    if v_path and isinstance(v_path, Path)
                    else None,
                    "audio_path": None,  # VEO 3.1: Audio is IN the video
                    "has_native_audio": True,  # NEW: Flag for editor
                    "text": seg.get("text", ""),
                }
            )

        # VALIDATION: Ensure all segments have valid video paths before saving plan
        missing_videos = [
            i for i, s in enumerate(visual_segments) if not s.get("video_path")
        ]
        if missing_videos:
            logger.error(
                f"❌ [VISUALS] VEO generation failed for segments: {missing_videos}"
            )
            logger.error(
                "   ⚠️ Aborting plan creation - all segments must have valid videos"
            )
            return None

        plan = {
            "title": script.get("title"),
            "lang": script.get("lang") or script.get("_meta", {}).get("lang", "en"),
            "native_audio": True,  # NEW: Flag indicating VEO 3.1 native audio mode
            "segments": visual_segments,
        }
        plan_path = script_path.parent / f"plan_{script_path.stem}.json"
        save_json(plan_path, plan)
        return plan_path

    def _parse_result(self, result):
        if isinstance(result, str):
            try:
                return json.loads(result)
            except Exception:
                pass
        return result if isinstance(result, dict) else {"status": "error"}


visuals = VisualAssembler()
