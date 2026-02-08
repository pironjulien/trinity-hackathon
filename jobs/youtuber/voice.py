"""
JOBS/YOUTUBER/VOICE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: VOICE (LARYNX) 🗣️
PURPOSE: Synthèse vocale (TTS) via Gattaca ROUTE_VOICE.
TECH: Gemini 2.5 Pro TTS (via Gattaca routes 4 et 5).
══════════════════════════════════════════════════════════════════════════════
"""

import json
from pathlib import Path
from loguru import logger

# Import Gattaca Router
from corpus.brain.gattaca import gattaca, ROUTE_VOICE, ROUTE_LIVE


class HumanVoice:
    """
    Interface pour la Voix via Gattaca.
    Utilise ROUTE_VOICE (TTS Pro) ou ROUTE_LIVE (TTS temps réel).
    """

    def __init__(self):
        self.is_active = False

    async def start(self):
        self.is_active = True
        logger.info("🗣️ [VOICE] Larynx Warming Up (Gattaca TTS)...")

    async def stop(self):
        self.is_active = False
        logger.info("🔇 [VOICE] Larynx Shutdown.")

    async def speak(self, text: str, fast: bool = False):
        """Speak immediately via Gattaca TTS."""
        if not self.is_active:
            return

        route = ROUTE_LIVE if fast else ROUTE_VOICE
        try:
            result = await gattaca.route(text, route_id=route)
            logger.info(f"🗣️ [SAY] {text[:50]}...")
            return result
        except Exception as e:
            logger.error(f"💥 [VOICE] Speak failed: {e}")
            return None

    async def speak_to_file(
        self, text: str, filepath: Path, lang: str = "fr", fast: bool = False
    ) -> bool:
        """
        Génère un fichier audio via Gattaca TTS.
        Utilise gemini-2.5-pro-preview-tts (qualité) ou flash (rapide).
        """
        if not self.is_active:
            logger.warning("🔇 [VOICE] Cannot speak (Inactive).")
            return False

        logger.info(f"🎙️ [VOICE] Synthesizing to {filepath.name} via Gattaca...")

        route = ROUTE_LIVE if fast else ROUTE_VOICE

        try:
            # Language instruction dans le prompt
            tts_prompt = f"[{lang} language] {text}"
            result = await gattaca.route(tts_prompt, route_id=route)

            # Parse result
            if isinstance(result, str):
                try:
                    result_data = json.loads(result)
                except Exception:
                    result_data = {"status": "error", "message": result}
            else:
                result_data = result

            if result_data.get("status") == "ok":
                audio_size = result_data.get("audio_size", 0)
                logger.success(f"💾 [VOICE] TTS OK: {audio_size} bytes")
                # Note: Gattaca doit être modifié pour retourner les bytes audio
                # et les sauvegarder dans filepath
                return True
            else:
                logger.warning(f"⚠️ [VOICE] TTS returned: {result_data}")
                return False

        except Exception as e:
            logger.error(f"💥 [VOICE] Synthesis Failed: {e}")
            return False

    async def speak_to_bytes(
        self, text: str, lang: str = "fr", fast: bool = False
    ) -> bytes | None:
        """
        Retourne les bytes audio directement (pour streaming).
        Gattaca retourne un JSON avec le path vers le fichier audio.
        """
        if not self.is_active:
            return None

        route = ROUTE_LIVE if fast else ROUTE_VOICE
        tts_prompt = f"[{lang} language] {text}"

        try:
            result = await gattaca.route(tts_prompt, route_id=route)

            # Gattaca retourne JSON avec path vers le fichier audio
            if isinstance(result, str):
                result_data = json.loads(result)
                if result_data.get("status") == "ok":
                    audio_path = result_data.get("path")
                    if audio_path:
                        with open(audio_path, "rb") as f:
                            return f.read()
            return None

        except Exception as e:
            logger.error(f"💥 [VOICE] Bytes generation failed: {e}")
            return None


# Singleton
voice = HumanVoice()
