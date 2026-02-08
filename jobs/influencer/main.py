"""
JOBS/INFLUENCER/MAIN.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INFLUENCER SOVEREIGN ORCHESTRATOR 👑
PURPOSE: Main Entrypoint. Coordinates sub-modules and manages the timeline.
ARCHI: SOTA 2026 (Modular, Config-Driven, Autonomous)
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from loguru import logger

from jobs.influencer.core.config import config_manager
from jobs.influencer.core.interfaces import SovereignModule
from jobs.influencer.core.approval_queue import approval_queue

# Modules
from jobs.influencer.modules.grok.core import grok_module
from jobs.influencer.modules.mentions.worker import mentions_module
from jobs.influencer.modules.youtube.worker import youtube_module
from jobs.influencer.modules.trinity.core import trinity_module

MODULES: list[SovereignModule] = [
    youtube_module,
    mentions_module,
    grok_module,
    trinity_module,
]


class InfluencerJob:
    """
    The brain of the Influencer persona.
    """

    async def start(self):
        """Called by Trinity System on startup."""
        logger.info("👑 Started")
        self._is_running = True
        # Start background loop
        self._run_task = asyncio.create_task(self.run_forever())

    async def stop(self):
        """Called by Trinity System on shutdown."""
        logger.info("👑 Stopping...")
        self._is_running = False
        # Wake up loop if sleeping? (Optional, loop checks flag on next iteration)
        # We could cancel the sleep but simple flag is safer for now.
        logger.success("👑 Stopped")

    async def run_forever(self):
        """Main Infinite Loop."""
        logger.debug("   🔁 Loop Active.")
        while self._is_running:
            try:
                config = config_manager.load()

                # NOTE: No 'enabled' check here anymore
                # If this code runs, the job IS enabled (loaded by Trinity from jobs.json)

                # If this code runs, the job IS enabled (loaded by Trinity from jobs.json)

                logger.debug("💓 Heartbeat...")

                # 1. Check Approval Queue (Priority)

                # 1. Check Approval Queue (Priority)
                # If there are approved items waiting to go out, send them first.
                await self.process_approval_queue()

                # 2. Run Modules
                results = {}
                for module in MODULES:
                    if not self._is_running:
                        break
                    try:
                        # logger.debug(f"   👉 Running {module.name}...")
                        res = await module.heartbeat()
                        if res and res.get("action"):
                            results[module.name] = res
                            # Handle Module Proposals (e.g. Grok generated something needing approval)
                            if res.get("action") == "proposal":
                                self.handle_proposal(res, module.name)
                    except Exception as e:
                        logger.error(f"   💥 Module {module.name} failed: {e}")

                # 3. Sleep
                # F89 = 89 minutes (Configurable)
                # F89 = 89 minutes (Configurable)
                if self._is_running:
                    interval = config.heartbeat_interval_minutes
                    logger.info(f"💤 Sleeping ({interval}m)")
                    # SOTA 2026: Interruptible Sleep
                    for _ in range(int(interval * 60)):
                        if not self._is_running:
                            break
                        await asyncio.sleep(1)

            except Exception as e:
                logger.critical(f"👑 [INFLUENCER] Critical Failure: {e}")
                await asyncio.sleep(60)  # Panic sleep

    async def process_approval_queue(self):
        """
        Check if any queued items were approved by Human.
        """
        item = approval_queue.get_next_approved()
        if not item:
            return

        logger.info("🚀 Processing")

        # Route dispatch based on content_type
        # In a perfect world, modules handle their own approved items.
        # For now, simplistic router.

        success = False
        try:
            tweet_id = None
            # Fix: Queue uses 'type', Legacy used 'content_type'. Normalize.
            c_type = item.get("type") or item.get("content_type")

            if c_type == "grok_banter":
                # Delegate back to grok module? Or just post?
                # Grok module has post_banter logic.
                tweet_id = await grok_module.post_banter(item["meta"])
                success = tweet_id is not None

            elif c_type == "manual_tweet":
                from jobs.influencer.core.x_client import x_client

                tweet_id = await x_client.post_tweet_async(item["text"])
                success = tweet_id is not None

            elif c_type == "trinity_logic":
                # Delegate to Trinity module
                # Fix: Text is at root of item, not necessarily in meta
                text = item.get("text") or item.get("meta", {}).get("text")
                if text:
                    tweet_id = await trinity_module.post_thought(text)
                    success = tweet_id is not None
                else:
                    logger.error("❌ Trinity Logic item missing text")
                    success = False

            elif c_type == "mentions_reply":
                # Handle approved reply
                from jobs.influencer.core.x_client import x_client

                reply_to_id = item["meta"].get("reply_to_tweet_id")
                if reply_to_id:
                    # Use async reply (post_tweet_async with reply param)
                    tweet_id = await x_client.post_tweet_async(
                        item["text"], in_reply_to_tweet_id=reply_to_id
                    )
                    success = tweet_id is not None
                else:
                    logger.error(
                        "❌ Cannot post approved reply: Missing reply_to_tweet_id in meta"
                    )
                    success = False

            if success:
                logger.success("✅ Posted")
                approval_queue.mark_posted(item["id"], tweet_id=tweet_id)
            else:
                logger.error(f"❌ Execution failed for {item['id']}")

        except Exception as e:
            logger.error(f"❌ Queue Error: {e}")

    def handle_proposal(self, strategy_res: dict, module_name: str):
        """
        Handle a module proposing content (Approval Mode).
        """
        content = strategy_res.get("content")
        c_type = strategy_res.get("type", "unknown")

        if not content:
            return

        logger.info(f"📝 Proposal: {c_type}")

        # Add to Queue
        item_id = approval_queue.add(
            content_type=c_type,
            text=content.get("text"),
            image_path=content.get("image_path"),
            meta=content,
        )

        # SOTA 2026: Notifications (Config Driven)
        config = config_manager.load()

        should_notify = False
        if module_name == "grok":
            should_notify = config.notify_approvals_grok
        else:
            should_notify = config.notify_approvals_trinity

        if should_notify:
            # Standard 362: Phone Widget Notification (Primary)
            try:
                from social.messaging.notification_client import notify
                import asyncio

                asyncio.create_task(
                    notify.influencer(
                        f"📝 {module_name}: {content.get('text', '')[:100].rsplit(' ', 1)[0] if len(content.get('text', '')) > 100 else content.get('text', '')}{'...' if len(content.get('text', '')) > 100 else ''}",
                        actions=[
                            {
                                "id": f"approve_{item_id}",
                                "label": "Approve",
                                "type": "primary",
                            },
                            {
                                "id": f"reject_{item_id}",
                                "label": "Reject",
                                "type": "danger",
                            },
                        ],
                    )
                )
            except Exception:
                pass


# Singleton Export
# Singleton Export
influencer = InfluencerJob()

if __name__ == "__main__":
    from corpus.dna.genome import LOGS_DIR

    logger.add(LOGS_DIR / "influencer.jsonl", rotation="10 MB", serialize=True)

    # SOTA 2026 Fix: Await the loop directly to prevent process exit.
    # influencer.start() spawns a background task but returns immediately,
    # causing asyncio.run() to finish and the script to exit.
    # We must await the infinite loop.
    async def main():
        await influencer.start()
        # Keep the event loop alive by awaiting the task logic if start() spawns it
        # But influencer.start() uses create_task(run_forever).
        # We should just call run_forever directly or await the task.
        # Let's change strictly to calling logic:
        # influencer.start() -> logs "Started" -> run_forever()

        # Override: Don't use start() which spawns a task. Call run_forever directly after logging.
        logger.info("👑 Started (Blocking Mode)")
        await influencer.run_forever()

    asyncio.run(main())
