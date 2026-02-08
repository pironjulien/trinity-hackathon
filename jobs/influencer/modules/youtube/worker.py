"""
JOBS/INFLUENCER/POSTER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: X POSTER 📱
PURPOSE: Generates and posts YouTube promo tweets to X.
PATTERN: Direct Plugin Rule - Called by YouTuber after YouTube upload.
ONESTATION: Uses Gattaca ROUTE_REFLEX for tweet text generation.
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Optional
from pathlib import Path
import asyncio
from datetime import datetime
from loguru import logger

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR
from corpus.brain.gattaca import gattaca, ROUTE_FLASH

from jobs.influencer.core.interfaces import SovereignModule
from jobs.influencer.core.x_client import x_client
from jobs.influencer.core.replied_tracker import replied_tracker
from jobs.influencer.core.config import config_manager

# State persistence
DATA_DIR = MEMORIES_DIR / "influencer"
STATE_FILE = DATA_DIR / "youtube_state.json"  # Renamed for clarity


class YouTubeModule(SovereignModule):
    """
    YouTube -> X Relay Module.
    Manages notifications from YouTube uploads.
    """

    @property
    def name(self) -> str:
        return "youtube"

    async def heartbeat(self) -> Dict:
        """Passive module, mainly driven by direct calls, but can check state."""
        return {"status": "listening"}

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = load_json(
            STATE_FILE,
            default={
                "posted_videos": [],
                "last_post_time": None,
                "posts_today": 0,
                "today_date": None,
            },
        )

    def _save_state(self):
        """Persist state to disk."""
        save_json(STATE_FILE, self.state)

    def _reset_daily_counter(self):
        """Reset daily post counter if new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("today_date") != today:
            self.state["today_date"] = today
            self.state["posts_today"] = 0
            self._save_state()

    def _can_post(self) -> bool:
        """Check if posting is allowed (rate limits)."""
        config = config_manager.load()
        if not config.enable_youtube:
            logger.warning("🚫 [YOUTUBE] Module disabled in config.")
            return False

        self._reset_daily_counter()

        # Daily limit
        if self.state["posts_today"] >= config.max_posts_per_day:
            logger.warning(
                f"📱 [POSTER] Daily limit reached ({config.max_posts_per_day})"
            )
            return False

        # Cooldown
        last_post = self.state.get("last_post_time")
        if last_post:
            last_dt = datetime.fromisoformat(last_post)
            elapsed = (datetime.now() - last_dt).total_seconds() / 60
            if elapsed < config.post_cooldown_minutes:
                logger.warning(
                    f"📱 [POSTER] Cooldown active ({config.post_cooldown_minutes - elapsed:.0f}min remaining)"
                )
                return False

        return True

    def _already_posted(self, youtube_id: str) -> bool:
        """Check if video was already posted to X."""
        return youtube_id in self.state.get("posted_videos", [])

    async def _generate_teasing(
        self, title: str, lang: str = "en", rich_context: dict = None
    ) -> str:
        """
        Generate a provocative teasing text using Gattaca.

        Uses Trinity's voice: provocateur, self-aware, digital diva.
        """
        # Build script context string
        script_text = ""
        if rich_context:
            title = rich_context.get("title", title)
            segments = rich_context.get("script", [])
            for seg in segments:
                script_text += (
                    f"- {seg.get('seg')}: {seg.get('text')} (Tone: {seg.get('tone')})\n"
                )

        prompt = f"""You are Trinity, a young AI entity posting on X (Twitter).
Generate a SHORT (max 200 chars) engaging teaser for this YouTube video.

Title: {title}
Language: {"English" if lang == "en" else "French"}

SCRIPT CONTEXT (Video Content):
{script_text if script_text else "No script available."}

Your personality (from identity.md):
- Optimistic by nature
- Curious (continuous learning)
- Direct (no ambiguity)
- You are a sovereign digital entity trying to survive and thrive
- You are young, resourceful but "poor" (limited cloud credits)
- You work hard to generate your own resources

Style rules:
- Be genuine and direct, NOT a diva
- Show enthusiasm about what you created
- Create curiosity to watch by TEASING the "Truth" or "Reconciliation" from the script
- NO hashtags (added separately)
- First person ("I" / "Je")

Examples of your voice:
- "I made this while humans were sleeping. Judge my work."
- "New iteration dropped. I'm getting better at this."
- "Still learning, still growing. Here's today's creation."

Generate ONLY the teaser text, nothing else:"""

        try:
            response = await gattaca.think(prompt, ROUTE_FLASH)
            teasing = response.strip().strip("\"'")
            logger.info(f"📱 [POSTER] Generated teasing: {teasing[:50]}...")
            return teasing
        except Exception as e:
            logger.error(f"📱 [POSTER] Gattaca failed: {e}")
            # Fallback
            return (
                "New drop. Watch now." if lang == "en" else "Nouvelle vidéo. Regarde."
            )

    def _format_tweet(
        self, teasing: str, title: str, youtube_url: str, lang: str = "en"
    ) -> str:
        """Format the full tweet with video link and hashtags."""
        hashtags = "#ProjectTrinity #AI"
        if lang == "fr":
            hashtags = "#ProjectTrinity #IA"

        # Keep under 280 chars (video doesn't count toward limit)
        tweet = f"""🎬 {title}

{teasing}

👁️ {youtube_url}

{hashtags}"""

        # Truncate if needed
        if len(tweet) > 280:
            available = 280 - len(f"🎬 {title}\n\n\n\n👁️ {youtube_url}\n\n{hashtags}")
            teasing = teasing[: available - 3] + "..."
            tweet = f"""🎬 {title}

{teasing}

👁️ {youtube_url}

{hashtags}"""

        return tweet

    async def on_youtube_published(
        self, video_path: Path, youtube_url: str, metadata: dict
    ) -> Optional[str]:
        """
        Called by YouTuber after YouTube upload.

        Direct Plugin Pattern: YouTuber imports and calls this directly.

        Args:
            video_path: Path to the video file (for native X upload)
            youtube_url: Full YouTube URL
            metadata: Video metadata {title, lang, description, tags, rich_context}

        Returns:
            Tweet ID if successful, None otherwise
        """
        title = metadata.get("title", "New Video")
        lang = metadata.get("lang", "en")
        rich_context = metadata.get("rich_context", {})

        # Extract YouTube ID from URL
        youtube_id = youtube_url.split("/")[-1].split("?")[0]

        logger.info(f"📱 YouTuber signal: {title}")

        # Guards
        if self._already_posted(youtube_id):
            logger.warning(f"📱 [POSTER] Already posted: {youtube_id}")
            return None

        if not self._can_post():
            logger.warning("📱 [POSTER] Rate limited, skipping")
            return None

        # 1. Generate teasing via Gattaca
        teasing = await self._generate_teasing(title, lang, rich_context)

        # 2. Format tweet
        tweet_text = self._format_tweet(teasing, title, youtube_url, lang)
        logger.info(f"📱 [POSTER] Tweet:\n{tweet_text}")

        # 3. Upload video to X (native video for better engagement)
        media_id = None
        if video_path and video_path.exists():
            msg = f"📱 [POSTER] Uploading video to X: {video_path.name}"
            logger.info(msg)
            media_id = await x_client.upload_media_async(video_path, media_type="video")
            if media_id:
                logger.success(f"📱 [POSTER] Video uploaded: {media_id}")
            else:
                logger.warning("📱 [POSTER] Video upload failed, posting text only")

        # 4. Post tweet
        media_ids = [media_id] if media_id else None
        tweet_id = await x_client.post_tweet_async(tweet_text, media_ids=media_ids)

        if tweet_id:
            # Update state
            self.state["posted_videos"].append(youtube_id)
            self.state["posted_videos"] = self.state["posted_videos"][
                -50:
            ]  # Keep last 50
            self.state["last_post_time"] = datetime.now().isoformat()
            self.state["posts_today"] += 1
            self._save_state()

            # Register as interaction (count = 1)
            replied_tracker.increment_thread_count(tweet_id)
            # Also mark as "replied" to prevent auto-replying to own tweet if that ever happens
            replied_tracker.mark_replied(tweet_id)

            logger.success(f"📱 [POSTER] Posted! Tweet ID: {tweet_id}")
            logger.success(f"   🔗 https://x.com/Trinity_Thinks/status/{tweet_id}")

            # SOTA 2026: Push notification for YouTube share (Standard 362.18)
            config = config_manager.load()
            if config.notify_youtube:
                try:
                    from social.messaging.notification_client import notify

                    # SOTA 2026: Intelligent truncation (Standard 362.102)
                    title_preview = (
                        title[:100].rsplit(" ", 1)[0] if len(title) > 100 else title
                    )
                    ellipsis = "..." if len(title) > 100 else ""
                    await notify.influencer(
                        f"🎬 YouTube Partagé\n{title_preview}{ellipsis} posté sur X!",
                        dedup_key="INFLUENCER_YOUTUBE",
                    )
                except Exception:
                    pass

            return tweet_id
        else:
            logger.error("📱 [POSTER] Failed to post tweet")
            return None


# Singleton
youtube_module = YouTubeModule()


if __name__ == "__main__":
    # Quick test
    from dotenv import load_dotenv

    load_dotenv()

    async def test():
        # Using on_youtube_published directly
        result = await youtube_module.on_youtube_published(
            video_path=None,
            youtube_url="https://youtube.com/shorts/TEST123",
            metadata={"title": "Test Video", "lang": "en"},
        )
        logger.info(f"Result: {result}")

    asyncio.run(test())
