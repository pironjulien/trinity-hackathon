"""
Notification Client (Standard 362)
═══════════════════════════════════════════════════════════════════════════════
Simple client to push notifications to the Angel notification system.
Jobs and services use this to send in-app notifications.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import httpx
from loguru import logger
from typing import Optional, List, Dict
from enum import Enum


# Angel endpoint for notifications
ANGEL_HOST = os.getenv("ANGEL_HOST", "127.0.0.1")
ANGEL_PORT = int(os.getenv("ANGEL_PORT", "8089"))
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")


class NotificationSource(str, Enum):
    """Valid notification sources."""

    SYSTEM = "SYSTEM"  # Trinity core system events
    SCHEDULER = "SCHEDULER"  # Circadian scheduler (morning, noon, night)
    TRADER = "TRADER"  # Trading heart operations
    JULES = "JULES"  # Shadow Developer
    INFLUENCER = "INFLUENCER"  # Social media agent
    YOUTUBER = "YOUTUBER"  # Video production pipeline
    NERVE = "NERVE"  # Nervous system alerts


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    INFO = "INFO"  # Normal information
    WARNING = "WARNING"  # Attention needed
    CRITICAL = "CRITICAL"  # Urgent action required
    ALERT = "ALERT"  # System alert (highest)


class NotificationClient:
    """
    Client to send notifications to the Angel notification system.

    Usage:
        from social.messaging.notification_client import notify

        # Simple notification
        await notify.send("TRADER", "Position opened: BTC/USDT at $98,500")

        # Notification with actions
        await notify.send(
            source="TRADER",
            message="New position opened",
            actions=[
                {"id": "close", "label": "Close Position", "type": "danger"},
                {"id": "details", "label": "View Details", "type": "primary"},
            ]
        )

        # Typed helpers
        await notify.system("Trinity is online!")
        await notify.trader("ETH/EUR position opened at 3,245€")
        await notify.jules("PR ready for review", actions=[...])
        await notify.alert("Circuit breaker triggered!")
    """

    def __init__(self):
        self.base_url = f"http://{ANGEL_HOST}:{ANGEL_PORT}"
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def send(
        self,
        source: str,
        message: str,
        actions: Optional[List[Dict]] = None,
        priority: str = "INFO",
        body: Optional[str] = None,
        title: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """
        Send a notification to the Angel notification system.

        Args:
            source: Source identifier (TRADER, JULES, INFLUENCER, SYSTEM, etc.)
            message: Notification message text (plain text for push notifications)
            actions: Optional list of action buttons [{"id": str, "label": str, "type": str}]
                     type can be: "primary", "danger", or empty string for secondary
            priority: Priority level (INFO, WARNING, CRITICAL, ALERT)
            body: Optional rich HTML body for Phone Widget (falls back to message)
            title: Optional notification title (falls back to message[:60])
            dedup_key: Optional deduplication key. If provided, replaces any existing
                       notification with the same key (prevents spam for periodic reports)

        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            client = await self._get_client()

            params = {
                "source": source.upper(),
                "message": message,
            }

            if body:
                params["body"] = body
            if title:
                params["title"] = title
            if actions:
                params["actions"] = actions
            if dedup_key:
                params["dedup_key"] = dedup_key

            headers = {}
            if ANGEL_API_KEY:
                headers["X-Angel-Key"] = ANGEL_API_KEY

            response = await client.post(
                f"{self.base_url}/notifications/add",
                json=params,
                headers=headers,
            )

            if response.status_code == 200:
                logger.debug(f"📱 Notification sent: {source} - {message[:50]}...")
                return True
            else:
                logger.warning(f"Notification failed: {response.status_code}")
                return False

        except Exception as e:
            logger.debug(f"Notification error (Angel may be offline): {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # TYPED CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    async def system(
        self,
        message: str,
        actions: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ) -> bool:
        """Send a system notification (Trinity core events)."""
        return await self.send(
            NotificationSource.SYSTEM, message, actions, title=title, body=body
        )

    async def scheduler(
        self,
        message: str,
        actions: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """Send a scheduler notification (morning, noon, night events)."""
        return await self.send(
            NotificationSource.SCHEDULER,
            message,
            actions,
            title=title,
            body=body,
            dedup_key=dedup_key,
        )

    async def trader(
        self,
        message: str,
        actions: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """Send a trader notification (positions, signals)."""
        return await self.send(
            NotificationSource.TRADER,
            message,
            actions,
            title=title,
            body=body,
            dedup_key=dedup_key,
        )

    async def jules(
        self,
        message: str,
        actions: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """Send a Jules notification (PR, plans, decisions)."""
        return await self.send(
            NotificationSource.JULES,
            message,
            actions,
            title=title,
            body=body,
            dedup_key=dedup_key,
        )

    async def influencer(
        self,
        message: str,
        actions: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """Send an influencer notification (tweets, approvals)."""
        return await self.send(
            NotificationSource.INFLUENCER,
            message,
            actions,
            title=title,
            body=body,
            dedup_key=dedup_key,
        )

    async def youtuber(
        self,
        message: str,
        actions: Optional[List[Dict]] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """Send a youtuber notification (uploads, pipeline, milestones)."""
        return await self.send(
            NotificationSource.YOUTUBER,
            message,
            actions,
            title=title,
            body=body,
            dedup_key=dedup_key,
        )

    async def nerve(
        self, message: str, level: str = "INFO", actions: Optional[List[Dict]] = None
    ) -> bool:
        """Send a nerve signal notification."""
        prefix = {"CRITICAL": "🔴", "WARNING": "🟠", "INFO": "🟢"}.get(level, "")
        return await self.send(
            NotificationSource.NERVE, f"{prefix} {message}", actions, priority=level
        )

    async def alert(self, message: str, actions: Optional[List[Dict]] = None) -> bool:
        """Send a critical alert notification."""
        return await self.send(
            NotificationSource.SYSTEM, f"⚠️ {message}", actions, priority="ALERT"
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
notify = NotificationClient()


# Convenience function for sync contexts (fires and forgets)
def send_notification_sync(source: str, message: str, actions: list = None):
    """
    Send notification from sync code (fire and forget).
    For async code, use: await notify.send(...)
    """
    import asyncio

    async def _send():
        await notify.send(source, message, actions)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send())
    except RuntimeError:
        # No running loop, create one
        asyncio.run(_send())
