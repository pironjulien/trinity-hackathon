"""
CORPUS/SOMA/VOICE.PY - Larynx de Trinity
══════════════════════════════════════════════════════════════════════════════
MODULE: VOICE (LARYNX) 🗣️
PURPOSE: Synthèse vocale via Gattaca ROUTE_VOICE/VOICEFAST.
TECH: Gemini TTS (gemini-2.5-pro-preview-tts / flash native audio).
══════════════════════════════════════════════════════════════════════════════
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger
from corpus.brain.gattaca import gattaca, ROUTE_VOICE, ROUTE_LIVE


class Larynx:
    """
    Interface vocale SOMA utilisant Gattaca TTS.

    Routes:
    - ROUTE_VOICE (5): gemini-2.5-pro-preview-tts (quality)
    - ROUTE_LIVE (6): gemini-2.5-flash-native-audio (speed)
    """

    def __init__(self):
        self.is_active = False

    async def start(self):
        """Initialise le système vocal."""
        self.is_active = True
        logger.info("🗣️ [LARYNX] Voice System Online (Gattaca TTS)")

    async def stop(self):
        """Arrête le système vocal."""
        self.is_active = False
        logger.info("🔇 [LARYNX] Voice System Offline")

    async def speak(
        self, text: str, fast: bool = False, lang: str = "fr"
    ) -> Optional[str]:
        """
        Génère audio et retourne le path du fichier.

        Args:
            text: Texte à synthétiser
            fast: Utiliser VOICEFAST (plus rapide, moins de qualité)
            lang: Code langue (fr, en-US, etc.)

        Returns:
            Path vers le fichier audio WAV, ou None si erreur
        """
        if not self.is_active:
            logger.warning("🔇 [LARYNX] Voice system inactive")
            return None

        route = ROUTE_LIVE if fast else ROUTE_VOICE
        tts_prompt = f"[{lang} language] {text}"

        result = None
        try:
            result = await gattaca.route(tts_prompt, route_id=route)
            data = json.loads(result) if isinstance(result, str) else result

            if data.get("status") == "ok":
                path = data.get("path")
                logger.success(
                    f"🗣️ [LARYNX] Generated: {Path(path).name if path else 'unknown'}"
                )
                return path
            else:
                logger.warning(f"⚠️ [LARYNX] TTS returned: {data}")
                return None

        except json.JSONDecodeError:
            logger.error(
                f"💥 [LARYNX] Invalid JSON response: {result[:100] if result else 'empty'}"
            )
            return None
        except Exception as e:
            logger.error(f"💥 [LARYNX] Speak failed: {e}")
            return None

    async def speak_to_bytes(
        self, text: str, fast: bool = False, lang: str = "fr"
    ) -> Optional[bytes]:
        """
        Retourne les bytes audio directement (pour streaming).

        Args:
            text: Texte à synthétiser
            fast: Utiliser VOICEFAST
            lang: Code langue

        Returns:
            Bytes audio WAV, ou None si erreur
        """
        path = await self.speak(text, fast=fast, lang=lang)
        if path:
            try:
                with open(path, "rb") as f:
                    audio_bytes = f.read()
                logger.debug(f"🗣️ [LARYNX] Read {len(audio_bytes)} bytes from {path}")
                return audio_bytes
            except Exception as e:
                logger.error(f"💥 [LARYNX] Failed to read audio file: {e}")
        return None

    async def speak_to_file(
        self, text: str, filepath: Path, fast: bool = False, lang: str = "fr"
    ) -> bool:
        """
        Génère audio et sauvegarde dans le fichier spécifié.

        Args:
            text: Texte à synthétiser
            filepath: Chemin de destination
            fast: Utiliser VOICEFAST
            lang: Code langue

        Returns:
            True si succès, False sinon
        """
        audio_bytes = await self.speak_to_bytes(text, fast=fast, lang=lang)
        if audio_bytes:
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(audio_bytes)
                logger.success(f"💾 [LARYNX] Saved to {filepath}")
                return True
            except Exception as e:
                logger.error(f"💥 [LARYNX] Failed to save: {e}")
        return False


# Singleton
voice = Larynx()
