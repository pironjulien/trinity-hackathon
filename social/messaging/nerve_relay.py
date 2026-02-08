"""
Nerve Signal Relay (Standard 362)
═══════════════════════════════════════════════════════════════════════════════
Relays nervous system signals to the notification system.
Replaces the legacy nerve signal handler.
═══════════════════════════════════════════════════════════════════════════════
"""

from loguru import logger
from social.messaging.notification_client import notify


async def relay_nerve_signal(level: str, signal: str, message: str) -> bool:
    """
    Relay a nerve signal to the notification system.

    Args:
        level: Signal level (URGENT, PAIN, PLEASURE, INFO)
        signal: Signal type (TRADE_WIN, CIRCUIT_BREAKER, etc.)
        message: Signal message (can be plain text or JSON)

    Returns:
        True if notification was sent successfully
    """
    import json

    # Parse potential JSON multi-modal message
    text_content = message
    actions = None

    try:
        if message.strip().startswith("{"):
            payload = json.loads(message)
            if isinstance(payload, dict):
                text_content = payload.get("text", message)
                # Convert buttons to actions format
                buttons = payload.get("buttons")
                if buttons:
                    actions = []
                    for row in buttons:
                        for btn in row:
                            actions.append(
                                {
                                    "id": btn.get("data", ""),
                                    "label": btn.get("text", ""),
                                    "type": "primary"
                                    if "APPROVE" in btn.get("data", "")
                                    else "",
                                }
                            )
    except Exception:
        pass  # Not JSON, treat as plain text

    # Format prefix based on level
    prefix = ""
    if level == "URGENT":
        prefix = "🚨 "
    elif level == "PAIN":
        prefix = "⚠️ "
    elif level == "PLEASURE":
        prefix = "💎 "
    elif signal == "TRADE_WIN":
        prefix = "💰 "

    final_text = f"{prefix}[{signal}] {text_content}"  # Full message, no truncation

    try:
        return await notify.nerve(final_text, level=level, actions=actions)
    except Exception as e:
        logger.debug(f"Nerve relay failed: {e}")
        return False


def register_nerve_relay():
    """
    Register the nerve relay with the nervous system.
    Called during Trinity startup.
    """
    try:
        from corpus.soma.nerves import nerves

        async def _on_nerve_signal(level: str, signal: str, message: str):
            await relay_nerve_signal(level, signal, message)

        nerves.subscribe(_on_nerve_signal)
        logger.debug("📱 Nerve relay registered")
    except Exception as e:
        logger.warning(f"Nerve relay registration failed: {e}")
