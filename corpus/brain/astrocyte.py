"""
CORPUS/BRAIN/ASTROCYTE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ASTROCYTE (API KEY PROVIDER) 🎹
PURPOSE: Simple API key access for Gattaca.
══════════════════════════════════════════════════════════════════════════════

Single-key mode for standard API access.
"""

from loguru import logger
from corpus.dna.secrets import vault


class KeyManager:
    """
    Simple Key Manager.
    Single key access - standard API pattern.
    """

    def __init__(self):
        self.key = vault.GEMINI_API_KEY

    def get_active_key(self) -> str:
        """Get the API key."""
        if not self.key:
            logger.warning("⚠️ No API key configured")
            return ""
        return self.key


# Singleton
key_manager = KeyManager()
