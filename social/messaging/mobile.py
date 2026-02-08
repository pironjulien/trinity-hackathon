"""
Mobile App Configuration Plugin
===============================
Defines configuration constants and theme values for the Trinity Mobile App.
Also handles backend initialization for mobile integration.
"""

from dataclasses import dataclass, field
from typing import Dict
from loguru import logger


@dataclass
class MobileConfig:
    """Configuration for Trinity Mobile App (React Native)."""

    # Environment
    API_URL_ANDROID: str = "http://10.0.2.2:8089"
    API_URL_IOS: str = "http://localhost:8089"

    # Theme (Cyberpunk)
    THEME: Dict[str, str] = field(
        default_factory=lambda: {
            "background": "#0a0a0a",
            "primary": "#00ff41",  # Matrix Green
            "secondary": "#008F11",  # Darker Green
            "accent": "#ff0055",  # Cyber Pink/Red
            "text": "#e0e0e0",
            "textDim": "#808080",
            "card": "#111111",
            "border": "#333333",
        }
    )

    def get_api_url(self, platform: str = "android") -> str:
        """Returns the API URL based on platform."""
        if platform.lower() == "android":
            return self.API_URL_ANDROID
        return self.API_URL_IOS


async def setup(app):
    """Initializes the Mobile Plugin."""
    logger.info("📱 [MOBILE] Ready")

    # Expose config to app state
    app.state.mobile_config = MobileConfig()

    logger.debug(f"   + Config loaded: {app.state.mobile_config.THEME['primary']}")
