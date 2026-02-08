"""
CORPUS/NERVOUS_SYSTEM/PUSH_CLIENT.PY
================================================================================
MODULE: FCM Push Notification Client
PURPOSE: Send push notifications via Firebase Cloud Messaging (Standard 362)
PROTOCOL: Uses Firebase Admin SDK with service account credentials
================================================================================
"""

import os
import httpx
from loguru import logger
from typing import List, Dict, Optional


# Firebase FCM HTTP v1 API
FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# Load service account from environment or file
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "trinity2-482313")


async def _get_access_token() -> str:
    """
    Get OAuth2 access token for FCM using service account.
    Priority: GOOGLE_CLOUD_1_CREDENTIALS_BASE64 > GOOGLE_APPLICATION_CREDENTIALS > ADC
    """
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        import base64
        import json

        # Priority 1: Base64-encoded credentials (Trinity standard)
        creds_base64 = os.getenv("GOOGLE_CLOUD_1_CREDENTIALS_BASE64", "").strip('"')
        if creds_base64:
            try:
                creds_json = json.loads(base64.b64decode(creds_base64).decode("utf-8"))
                credentials = service_account.Credentials.from_service_account_info(
                    creds_json,
                    scopes=["https://www.googleapis.com/auth/firebase.messaging"],
                )
                credentials.refresh(Request())
                return credentials.token
            except Exception as e:
                logger.warning(f"[PUSH] Base64 creds failed: {e}")

        # Priority 2: Service account file
        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if sa_path and os.path.exists(sa_path):
            credentials = service_account.Credentials.from_service_account_file(
                sa_path, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
            )
            credentials.refresh(Request())
            return credentials.token

        # Fallback: ADC
        import google.auth

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/firebase.messaging"]
        )
        credentials.refresh(Request())
        return credentials.token

    except Exception as e:
        logger.error(f"[PUSH] Failed to get access token: {e}")
        raise


async def send_fcm_notification(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict] = None,
    icon: str = "ic_notification",
) -> Dict:
    """
    Send push notification to multiple devices via FCM HTTP v1 API.

    Args:
        tokens: List of FCM registration tokens
        title: Notification title
        body: Notification body
        data: Optional data payload
        icon: Android notification icon

    Returns:
        Dict with success/failure counts
    """
    if not tokens:
        return {"success": 0, "failure": 0}

    try:
        access_token = await _get_access_token()
    except Exception:
        # Fallback: Try legacy HTTP API (no auth required for testing)
        logger.warning("[PUSH] Using legacy FCM - production requires service account")
        return await _send_legacy_fcm(tokens, title, body, data)

    url = FCM_SEND_URL.format(project_id=FIREBASE_PROJECT_ID)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    success = 0
    failure = 0

    async with httpx.AsyncClient() as client:
        for token in tokens:
            message = {
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body": body,
                    },
                    "android": {
                        "notification": {
                            "icon": icon,
                            "color": "#00FFFF",  # Cyan Trinity color
                            "channel_id": "trinity_notifications",
                            # SOTA 2026: REMOVED click_action to allow 'link' to drive ACTION_VIEW Intent
                            # "click_action": "FLUTTER_NOTIFICATION_CLICK",
                            # SOTA 2026: Native Deep Link URL
                            "link": f"trinity://msg/{data.get('notification_id')}"
                            if data and data.get("notification_id")
                            else None,
                        },
                        # SOTA 2026: Data at android level ensures Intent extras receive it
                        "data": {k: str(v) for k, v in data.items()} if data else {},
                    },
                }
            }

            # Also add data at message level for JS-side handling
            if data:
                message["message"]["data"] = {k: str(v) for k, v in data.items()}

            try:
                response = await client.post(url, headers=headers, json=message)
                if response.status_code == 200:
                    success += 1
                    logger.debug(f"[PUSH] Sent to {token[:20]}...")
                else:
                    failure += 1
                    logger.warning(f"[PUSH] Failed: {response.text}")
            except Exception as e:
                failure += 1
                logger.error(f"[PUSH] Error: {e}")

    logger.info(f"[PUSH] Sent: {success}/{len(tokens)}")
    return {"success": success, "failure": failure}


async def _send_legacy_fcm(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict] = None,
) -> Dict:
    """
    Fallback: Send via legacy FCM HTTP API (deprecated but simpler).
    Requires FCM_SERVER_KEY environment variable.
    """
    server_key = os.getenv("FCM_SERVER_KEY")
    if not server_key:
        logger.error("[PUSH] FCM_SERVER_KEY not set - cannot send push")
        return {"success": 0, "failure": len(tokens), "error": "No FCM_SERVER_KEY"}

    url = "https://fcm.googleapis.com/fcm/send"
    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "registration_ids": tokens,
        "notification": {
            "title": title,
            "body": body,
            "icon": "ic_notification",
            "color": "#00FFFF",
        },
    }

    if data:
        payload["data"] = data

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            result = response.json()
            return {
                "success": result.get("success", 0),
                "failure": result.get("failure", 0),
            }
        else:
            logger.error(f"[PUSH] Legacy FCM failed: {response.text}")
            return {"success": 0, "failure": len(tokens)}
