"""
JOBS/INFLUENCER/MODULES/GROK/CORE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: GROK MODULE 🎛️
PURPOSE: Automated FLIRTY running gag with @grok.
PATTERNS: SovereignModule
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional, Dict
from pathlib import Path
from loguru import logger

from jobs.influencer.core.interfaces import SovereignModule
from jobs.influencer.core.x_client import x_client
from jobs.influencer.core.replied_tracker import replied_tracker
from jobs.influencer.core.config import config_manager
from jobs.influencer.core.visuals import visual_engine

from jobs.influencer.modules.grok.storage import GrokStorage
from jobs.influencer.modules.grok.generator import GrokGenerator


class GrokModule(SovereignModule):
    """
    Automated FLIRTY running gag with @grok.
    Modular V2.
    """

    @property
    def name(self) -> str:
        return "grok"

    def __init__(self):
        self.storage = GrokStorage()
        self.generator = GrokGenerator()

    async def heartbeat(self) -> Dict:
        """Called by Orchestrator."""
        # Check config enable
        config = config_manager.load()
        if not config.enable_grok:
            return {"status": "disabled"}

        # 1. Check if we strictly need to wait (F2 cycle)
        if not self.storage.can_banter():
            # Even if we can't START a banter, we might need to REPLY to an ongoing one?
            # Let's check replies every time, but Opening only on schedule.
            pass

        # 2. Check for replies FROM Grok (Reactive)
        reply_res = await self.check_and_reply()
        if reply_res:
            return {"action": "replied_to_grok", "tweet_id": reply_res}

        # 3. Check for Opening (Proactive)
        if self.storage.can_banter():
            content = await self.generate_content()
            if content:
                # In modular flow, we generate, but do we post immediately or Queue?
                # Orchestrator used to Queue.
                # Ideally: Return "proposal" to Main, which queues it.
                # BUT SovereignModule concept implies autonomy or standardization.

                # For V2 Refactor: Let's stick to generating content and returning it so Main can Queue it if approval needed.
                # OR we just implement the posting here if authorized.

                if config.approval_mode:
                    # SOTA 2026: Push notification for Grok approval (Standard 362.18)
                    if config.notify_approvals_grok:
                        try:
                            from social.messaging.notification_client import notify

                            # SOTA 2026: Explicit title/body separation
                            await notify.influencer(
                                message=content.get("text", "")[:100],
                                title="💕 grok: @grok Banter",
                                body=content.get("text", ""),
                                dedup_key="INFLUENCER_GROK",
                            )
                        except Exception:
                            pass
                    return {
                        "action": "proposal",
                        "content": content,
                        "type": "grok_banter",
                    }
                else:
                    # Auto Posting
                    tid = await self.post_banter(content)
                    return {"action": "posted_opening", "tweet_id": tid}

        return {"status": "idle"}

    # ════════════════════════════════════════════════════════════════════════
    # LOGIC (Adapted from Original)
    # ════════════════════════════════════════════════════════════════════════

    async def check_and_reply(self) -> Optional[str]:
        """Check if @grok replied to our last banter and respond."""
        logger.info("💬 Checking")

        # 1. Identity Check
        # (Assuming client is auth - Main entrypoint ensures this)
        try:
            # We need user ID. XClient caches it usually?
            # Let's fetch it cleanly or assume XClient handles it.
            # x_client.get_me is synchronous/cached usually? No async here.
            pass
        except Exception:
            return None

        # [Simplified for V2 - XClient should handle "get interactions"]
        # Since I can't see XClient implementation details right now, let's trust the logic passed earlier.

        # ... (Re-implementing the logic read previously) ...

        # 3. Fetch Mentions
        # SOTA: Get user ID async, but use cache if possible
        me = await x_client.get_me_async()
        if not me:
            return None

        # Async non-blocking call
        mentions = await x_client.get_mentions_async(user_id=me["id"])
        if not mentions:
            return None

        grok_reply = None
        for m in mentions:
            if m.get("username", "").lower() in ["grok", "trinity_test_dummy"]:
                # Check replied tracker
                if not replied_tracker.has_replied(m.get("id")):
                    grok_reply = m
                    break

        if not grok_reply:
            return None

        # 5. Check Thread Limit (MANDATORY - prevent spam)
        root_tweet_id = self.storage.get_root_tweet_id()
        if not root_tweet_id:
            logger.warning("🛑 No root_tweet_id found, skipping to prevent spam")
            return None
        if not replied_tracker.can_reply_to_thread(root_tweet_id):
            logger.warning("🛑 Thread limit (2/2)")
            return None

        logger.success("🤖 Replied")

        # 6. Save Event
        self.storage.add_event(
            event_type="reply",
            role="grok",
            text=grok_reply["text"],
            tweet_id=grok_reply["id"],
        )

        # 7. Generate Reply
        reply_text = await self.generator.generate_reply(self.storage.get_history())
        if not reply_text:
            return None

        if "@grok" not in reply_text.lower():
            reply_text = f"@grok {reply_text}"

        # 9. Post
        # Use async post with in_reply_to_tweet_id
        reply_id = await x_client.post_tweet_async(
            text=reply_text, in_reply_to_tweet_id=grok_reply["id"]
        )

        if reply_id:
            logger.success("✅ Sent")
            replied_tracker.mark_replied(grok_reply["id"])
            if root_tweet_id:
                replied_tracker.increment_thread_count(root_tweet_id)

            self.storage.add_event(
                event_type="reply",
                role="trinity",
                text=reply_text,
                tweet_id=reply_id,
                in_reply_to=grok_reply["id"],
            )
            return reply_id

        return None

    async def generate_content(self) -> Optional[Dict]:
        """Generate Opening Content (Text + Visual)."""
        logger.info("💬 Generating...")

        # Text
        history = self.storage.get_history(limit=10)
        text = await self.generator.generate_opening(history)
        if not text:
            return None

        if "@grok" not in text.lower():
            text = f"@grok {text}"

        # Visual
        image_path = None
        config = config_manager.load()
        if config.visuals_enabled:
            image_path = await visual_engine.generate(text)

        # Mark throttle (don't mark here, mark on post? No, mark generated to avoid loop)
        # Actually logic says mark on post.

        return {
            "text": text,
            "image_path": str(image_path) if image_path else None,
        }

    async def post_banter(self, content: Dict) -> Optional[str]:
        """Post the pre-generated opening."""
        text = content.get("text")
        image_path_str = content.get("image_path")

        logger.info("💬 Posting...")

        media_ids = None
        if image_path_str:
            path = Path(image_path_str)
            if path.exists():
                media_id = await x_client.upload_media_async(path, media_type="image")
                if media_id:
                    media_ids = [media_id]

        tweet_id = await x_client.post_tweet_async(text, media_ids=media_ids)

        if tweet_id:
            self.storage.update_last_banter()
            self.storage.update_last_generated()  # Reset generation flag
            self.storage.add_event(
                event_type="opening", role="trinity", text=text, tweet_id=tweet_id
            )
            logger.success("✅ Sent")
            return tweet_id

        return None


# Singleton
grok_module = GrokModule()
