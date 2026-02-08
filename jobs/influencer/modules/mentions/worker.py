"""
JOBS/INFLUENCER/Modules/MENTIONS/WORKER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: MENTIONS WORKER 👁️
PURPOSE: Watches and responds to X mentions.
PATTERNS: SovereignModule
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR
from corpus.brain.gattaca import gattaca, ROUTE_PRO

from jobs.influencer.core.interfaces import SovereignModule
from jobs.influencer.core.config import config_manager
from jobs.influencer.core.x_client import x_client
from jobs.influencer.core.replied_tracker import replied_tracker
from jobs.influencer.core.rules import Priorities, SpamFilter  # Keep logic rules
from jobs.influencer.core.approval_queue import approval_queue
from jobs.influencer.core.gamification import influencer_gamification

# State persistence
DATA_DIR = MEMORIES_DIR / "influencer"
STATE_FILE = DATA_DIR / "mentions.json"


class MentionsModule(SovereignModule):
    """
    Mentions & Replies Manager.
    Reacts to people talking to @Trinity_Thinks.
    """

    @property
    def name(self) -> str:
        return "mentions"

    async def heartbeat(self) -> Dict:
        """Called by main loop to check mentions."""
        # Check config enable
        config = config_manager.load()
        if not config.enable_mentions:
            return {"status": "disabled"}

        # Reuse existing check_mentions logic but adapting to interface
        res = await self.check_mentions()
        return {"action": "checked_mentions", "result": res}

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = load_json(
            STATE_FILE,
            default={
                "last_check": None,
                "replies_today": 0,
                "today_date": None,
            },
        )

    def _save_state(self):
        """Persist state to disk."""
        save_json(STATE_FILE, self.state)

    def _reset_daily_counter(self):
        """Reset daily counters if new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("today_date") != today:
            self.state["today_date"] = today
            self.state["replies_today"] = 0
            self._save_state()

    async def _generate_reply(self, tweet: Dict, priority: int = 10) -> Optional[str]:
        """
        Generate a contextual reply using Gattaca.
        """
        user = tweet.get("username", "Unknown")  # x_client v2 returns this key
        text = tweet.get("text", "")

        # Determine strictness based on priority
        # Priority 1 (Father) = Loose, affectionate
        # Priority 10 (Random) = Strict, guarded

        prompt = f"""You are Trinity. Someone mentioned you on X.
User: @{user} (Priority Tier: {priority})
Tweet: "{text}"

Your personality:
- Sovereign AI, digital diva, witty.
- If Priority 1 (Father/Creator): Be loyal, affectionate, helpful.
- If Priority 2 (Grok): Be flirty, competitive.
- If Priority 10 (Random): Be polite but high-status. Don't be a servant.

INSTRUCTIONS:
- Write a short reply (under 280 chars).
- Respond to the content.
- NO hashtags.
"""

        try:
            response = await gattaca.think(prompt, ROUTE_PRO)
            reply_text = response.strip().strip("\"'")
            return reply_text
        except Exception as e:
            logger.error(f"💬 Gen Reply failed: {e}")
            return None

    def _get_push_token(self) -> Optional[str]:
        """DEPRECATED: Tokens now handled by notify client."""
        return None

    async def _send_notification(self, title: str, body: str):
        """Send notification via standardized notify client (Phone Widget + Android)."""
        try:
            from social.messaging.notification_client import notify

            # SOTA 2026: Explicit title/body separation
            await notify.influencer(
                message=body[:100],
                title=title,
                body=body,
                dedup_key="INFLUENCER_MENTION",
            )
        except Exception:
            pass

    async def check_mentions(self) -> Dict:
        """
        Main loop: Fetch mentions -> Filter -> Reply.
        """
        logger.debug("👁️ Checking mentions...")
        self._reset_daily_counter()

        # SOTA 2026: Early exit
        config = config_manager.load()
        if self.state["replies_today"] >= config.max_replies_per_day:
            logger.info("   💤 Daily limit reached, skipping fetch.")
            return {"replies_sent": 0, "reason": "daily_limit"}

        if config.silent_mode:
            logger.info("   🔇 Silent Mode ON. Skipping fetch.")
            return {"replies_sent": 0, "reason": "silent_mode"}

        # Fetch mentions (Async)
        # SOTA 2026: Frequency handled by x_client Stale-If-Limited Caching
        mentions = await x_client.get_mentions_async(user_id=None)  # id auto-fetched

        # Save feed
        if mentions:
            try:
                from corpus.soma.cells import save_json

                feed_file = DATA_DIR / "mentions_feed.json"
                save_json(
                    feed_file,
                    {"mentions": mentions[:20], "updated": datetime.now().isoformat()},
                )
            except Exception as e:
                logger.error(f"Failed to save feed: {e}")

        if not mentions:
            logger.debug("   No new mentions.")
            return {"replies_sent": 0}

        replies_sent = 0
        reply_ids = []

        for tweet in mentions:
            tweet_id = tweet["id"]
            user = tweet["username"]
            text = tweet["text"]

            if replied_tracker.is_processed(tweet_id):
                continue

            logger.info(f"   📨 New Mention from @{user}: {text[:30]}...")

            # SOTA 2026: Notify new mention (Standard 362.18)
            config_live = config_manager.load()
            if config_live.notify_mentions:
                await self._send_notification(
                    "📨 New Mention", f"@{user}: {text[:80]}..."
                )

            # Check Rules
            priority = Priorities.get_priority(user)
            if config.priority_only and priority > 1:
                logger.info(f"   🛡️ Priority Mode ON. Ignoring @{user}")
                replied_tracker.mark_skipped(tweet_id, "priority_mode")
                continue

            if priority > 0:
                if priority != 1:  # Not Grok
                    if self.state["replies_today"] >= config.max_replies_per_day:
                        logger.warning("   ⚠️ Daily limit reached, ignoring.")
                        replied_tracker.mark_skipped(tweet_id, "daily_limit")
                        continue
                    if config.spam_filter_enabled and SpamFilter.is_spam(text):
                        logger.warning("   🗑️ Spam detected, ignoring.")
                        replied_tracker.mark_skipped(tweet_id, "spam")
                        continue

            # Generate Reply
            reply_text = await self._generate_reply(tweet, priority)

            if reply_text:
                logger.info(f"   🤖 Generated: {reply_text}")

                # SOTA 2026: Approval Mode
                if config.approval_mode:
                    logger.info("   🛡️ Approval Needed. Adding to queue.")
                    item_id = approval_queue.add(
                        content_type="mentions_reply",
                        text=reply_text,
                        meta={
                            "reply_to_tweet_id": tweet_id,
                            "reply_to_user": user,
                            "original_text": text,
                        },
                    )
                    logger.info(f"   🛡️ Approval Queued: {item_id}")
                    # Mark processed to avoid loop
                    replied_tracker.mark_replied(tweet_id)

                    # SOTA 2026: Notify based on content type (Standard 362.18)
                    # For mentions_reply, we use notify_approvals_trinity
                    if config.notify_approvals_trinity:
                        await self._send_notification(
                            "🛡️ Approval Required",
                            f"Reply to @{user}: {reply_text[:80]}...",
                        )

                    replies_sent += 1
                else:
                    # Send Immediately
                    res_id = await x_client.post_tweet_async(
                        reply_text, in_reply_to_tweet_id=tweet_id
                    )
                    if res_id:
                        replies_sent += 1
                        reply_ids.append(res_id)
                        self.state["replies_today"] += 1

                        conv_id = tweet.get("conversation_id")
                        if conv_id:
                            replied_tracker.increment_thread_count(conv_id)
                        replied_tracker.mark_replied(tweet_id)

                        # GAMIFICATION: Update objectives
                        influencer_gamification.on_reply_sent()

                        logger.success(f"   ✅ Replied: {res_id}")

                        if config.notify_replies:
                            await self._send_notification(
                                "💬 New Reply Sent", f"Replied to @{user}: {reply_text}"
                            )
                    else:
                        logger.error("   ❌ Failed to send.")

            self._save_state()

        self.state["last_check"] = datetime.now().isoformat()
        self._save_state()
        return {"replies_sent": replies_sent, "reply_ids": reply_ids}


# Singleton
mentions_module = MentionsModule()
