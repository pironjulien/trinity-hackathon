try:
    import firebase_admin  # type: ignore[import-not-found]
    from firebase_admin import credentials, messaging  # type: ignore[import-not-found]
except ImportError:
    firebase_admin = None  # type: ignore
    credentials = None  # type: ignore
    messaging = None  # type: ignore

import os
import logging
from pathlib import Path

# SOTA 2026: Trinity Notification System
# Uses service-account.json for auth (must be provided by user)


class TrinityNotifier:
    def __init__(self):
        self.logger = logging.getLogger("TrinityNotifier")

        # Path relative to project root
        root_dir = Path(__file__).resolve().parent.parent
        cred_path = (
            root_dir / "social" / "android" / "keystore" / "service-account.json"
        )

        if not os.path.exists(cred_path):
            self.logger.error(f"❌ Service Account Key missing at: {cred_path}")
            return

        try:
            # Initialize Firebase Admin SDK if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self.logger.info("✅ Firebase Admin Initialized")
            else:
                self.logger.info("ℹ️ Firebase Admin already initialized")

        except Exception as e:
            self.logger.error(f"❌ Failed to init Firebase: {e}")

    def send_push(self, token, title, body, data=None):
        """
        Sends a native push notification to a specific device.
        """
        if not token:
            self.logger.warning("⚠️ No token provided for push")
            return False

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )

            # Send a message to the device corresponding to the provided
            # registration token.
            response = messaging.send(message)
            self.logger.info(f"🚀 Sent message: {response}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to send push: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    notifier = TrinityNotifier()

    # SYSTEM TEST: Replace with your actual token from the App UI Logs
    # notifier.send_push(
    #    token="DEVICE_TOKEN_FROM_APP_LOGS",
    #    title="Trinity System",
    #    body="I am now strictly Google Native."
    # )
