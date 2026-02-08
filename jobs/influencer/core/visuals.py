"""
JOBS/INFLUENCER/VISUALS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SHARED VISUAL ENGINE 🎨
PURPOSE: Centralized image generation logic for Influencer activities.
USAGE: Imported by Grok, Poster, Mentions, etc.
══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
from typing import Optional
from loguru import logger

from corpus.brain.gattaca import gattaca, ROUTE_CREATE


class VisualEngine:
    """
    The Visual Cortex of the Influencer Job.
    Generates images based on text context using Gattaca (Imagen).
    """

    async def generate(
        self, context_text: str, style_mode: str = "default"
    ) -> Optional[Path]:
        """
        Generate an image for a given context.

        Args:
            context_text: The tweet or concept to visualize.
            style_mode: Style preset (default, abstract, meme, etc.)

        Returns:
            Path to the generated image file, or None if failed.
        """
        prompt = self._build_prompt(context_text, style_mode)

        try:
            logger.info(f"🎨 [VISUALS] Generating for: {context_text[:30]}...")
            images = await gattaca.think(prompt, ROUTE_CREATE)

            if images and isinstance(images, list) and len(images) > 0:
                image_path = Path(images[0])
                logger.success(f"🎨 [VISUALS] Success: {image_path.name}")
                return image_path

            logger.warning("🎨 [VISUALS] No images returned.")
            return None

        except Exception as e:
            logger.error(f"🎨 [VISUALS] Generation failed: {e}")
            return None

    def _build_prompt(self, text: str, mode: str) -> str:
        """Construct the Imagen prompt based on mode."""

        base_prompt = f"""Create a minimalist, abstract cybernetic image representing this concept:
"{text}"
"""

        if mode == "default":
            return (
                base_prompt
                + """
Style:
- Dark mode aesthetic (black background)
- Neon accents (cyan, magenta)
- Abstract data visualization / circuit lines
- Mathematical beauty / Fibonacci spirals
- NO TEXT in the image
- High tech, sleek, "Google DeepMind" vibe
"""
            )
        # Future modes can be added here
        return base_prompt


# Singleton
visual_engine = VisualEngine()
