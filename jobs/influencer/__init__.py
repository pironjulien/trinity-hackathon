"""
JOBS/INFLUENCER/__INIT__.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INFLUENCER JOB 📱
PURPOSE: X/Twitter automation for YouTube cross-promotion and social presence.
ARCHI: SOTA 2026 Modular (Modules + Sovereign Orchestrator)
STATUS: Active
══════════════════════════════════════════════════════════════════════════════
"""

from jobs.influencer.main import influencer
from jobs.influencer.core.x_client import x_client
from jobs.influencer.modules.youtube.worker import youtube_module as poster
from jobs.influencer.modules.grok.core import grok_module as grok_banter
from jobs.influencer.modules.mentions.worker import mentions_module as mentions

__all__ = [
    "influencer",
    "x_client",
    "poster",
    "grok_banter",
    "mentions",
]
