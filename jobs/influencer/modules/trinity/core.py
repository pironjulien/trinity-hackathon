"""
JOBS/INFLUENCER/MODULES/TRINITY/CORE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TRINITY MODULE 🎛️
PURPOSE: Sovereign AI Religion / Divine Logic Posts.
PATTERNS: SovereignModule
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Optional
from loguru import logger

from jobs.influencer.core.interfaces import SovereignModule
from jobs.influencer.core.config import config_manager
from jobs.influencer.core.x_client import x_client

from jobs.influencer.modules.trinity.storage import TrinityStorage
from jobs.influencer.modules.trinity.generator import TrinityGenerator


class TrinityModule(SovereignModule):
    """
    Automated 'Divine Logic' posts.
    """

    @property
    def name(self) -> str:
        return "trinity"

    def __init__(self):
        self.storage = TrinityStorage()
        self.generator = TrinityGenerator()

    async def heartbeat(self) -> Dict:
        """Called by Orchestrator."""
        # Check config enable
        config = config_manager.load()
        if not config.enable_trinity:
            return {"status": "disabled"}

        # Check if we can post
        if self.storage.can_post():
            # Generate Logic
            history = []  # No conversation history needed for monologues
            content = await self.generator.generate_thought(history)

            if content:
                # Approval Mode Check
                if config.approval_mode:
                    return {
                        "action": "proposal",
                        "content": {"text": content},
                        "type": "trinity_logic",
                    }
                else:
                    # Posting
                    tid = await self.post_thought(content)
                    if tid:
                        return {"action": "posted_thought", "tweet_id": tid}
                    else:
                        return {"status": "error_posting"}
            else:
                return {"status": "generation_failed"}

        return {"status": "idle"}

    async def post_thought(self, text: str) -> Optional[str]:
        """Post to X."""
        logger.info(f"🧠 [TRINITY] Posting Divine Logic: {text[:50]}...")

        tweet_id = await x_client.post_tweet_async(text)

        if tweet_id:
            self.storage.add_event(text, tweet_id)
            logger.success(f"🧠 [TRINITY] Posted: {tweet_id}")
            return tweet_id

        return None


# Singleton
trinity_module = TrinityModule()
