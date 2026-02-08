"""
JOBS/INFLUENCER/CORE/INTERFACES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INTERFACES 🧩
PURPOSE: Abstract Base Classes for Influencer Modules.
Enforces that every module (Grok, YouTube, etc.) speaks the same protocol.
══════════════════════════════════════════════════════════════════════════════
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class SovereignModule(ABC):
    """
    Base contract for an autonomous influencer sub-module.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the module (e.g. 'grok', 'youtube')."""
        pass

    @abstractmethod
    async def heartbeat(self) -> Dict[str, Any]:
        """
        Execute one cycle of logic.

        Returns:
            Dict containing actions performed (for logging/history).
            Example: {"actions": ["posted_tweet"], "count": 1}
        """
        pass
