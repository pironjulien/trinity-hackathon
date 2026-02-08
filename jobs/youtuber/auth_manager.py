"""
JOBS/YOUTUBER/AUTH_MANAGER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: AUTH MANAGER 🔐
PURPOSE: Centralized YouTube OAuth2 Authentication & Token Management.
         Replaces all ad-hoc auth scripts.
FEATURES:
    - Robust Token Lifecycle (Load -> Refresh -> Auth -> Save)
    - Dual Mode: Interactive (Local Server) & OOB (Console Copy-Paste)
    - Multi-Channel Support (EN/FR)
    - CLI Interface for manual re-authentication
    - SOTA 2026: JSON Persistence & Strict Scope Enforcement
══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from loguru import logger

# Google Auth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Project Imports
from jobs.youtuber.constants import SCOPES, CHANNELS, SECRETS_DIR


class GoogleAuthManager:
    """
    Gestionnaire centralisé de l'authentification Google/YouTube.
    Implémente le pattern Singleton pour l'accès, mais peut être instancié.
    Utilise JSON pour la persistance (Sécurité++ vs Pickle).
    """

    def __init__(self):
        self.secrets_dir = SECRETS_DIR
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

    def get_credentials(self, channel: str = "en") -> Optional[Credentials]:
        """
        Récupère des identifiants valides pour la chaîne donnée.
        Gère le chargement depuis JSON, env, et le rafraîchissement automatique.
        Applique une validation STRICTE des scopes.
        """
        channel_config = CHANNELS.get(channel)
        if not channel_config:
            logger.error(f"❌ [AUTH] Channel unknown: {channel}")
            return None

        # 1. Try Local JSON (Priority)
        creds = self._load_from_json(channel)

        # 2. Try Env (Cloud/Production Persistence)
        if not creds:
            creds = self._load_from_env(channel)

        # 3. Validate & Refresh
        if creds:
            # SOTA 2026: Strict Scope Check
            if not self._validate_scopes(creds):
                logger.warning(f"⚠️ [AUTH] Scope mismatch for {channel}. Re-authentication required.")
                return None

            if creds.valid:
                return creds

            if creds.expired and creds.refresh_token:
                try:
                    logger.info(f"🔄 [AUTH] Refreshing token for {channel.upper()}...")
                    creds.refresh(Request())
                    # Save refreshed token
                    self._save_to_json(channel, creds)
                    return creds
                except Exception as e:
                    logger.warning(f"⚠️ [AUTH] Refresh failed for {channel}: {e}")
            else:
                logger.warning(f"⚠️ [AUTH] Token invalid and no refresh possible for {channel}.")

        logger.warning(f"⚠️ [AUTH] No valid credentials found for {channel}. Manual auth required.")
        return None

    def authenticate(
        self,
        channel: str = "en",
        mode: str = "interactive",
        force: bool = False,
        interaction_callback: Optional[Callable[[str], str]] = None
    ) -> bool:
        """
        Lance le processus d'authentification explicite (CLI).
        Découplé des IO via interaction_callback.

        Args:
            channel: 'en' ou 'fr'
            mode: 'interactive' (browser) ou 'oob' (console copy-paste)
            force: Si True, ignore le token existant
            interaction_callback: Fonction prenant l'URL et retournant le CODE (pour OOB).
        """
        channel_config = CHANNELS.get(channel)
        if not channel_config:
            logger.error(f"❌ [AUTH] Channel unknown: {channel}")
            return False

        if not force:
            existing = self.get_credentials(channel)
            if existing:
                logger.info(f"✅ [AUTH] Already authenticated for {channel.upper()}. Use --force to override.")
                return True

        logger.info(f"🚀 [AUTH] Starting {mode.upper()} authentication for {channel.upper()}...")

        # Load Client Secrets
        client_config = self._get_client_config()
        if not client_config:
            logger.error("❌ [AUTH] No client_secrets.json or Env configuration found.")
            return False

        try:
            if client_config.get("config_dict"):
                flow = InstalledAppFlow.from_client_config(client_config["config_dict"], SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(client_config["path"], SCOPES)

            if mode == "oob":
                if not interaction_callback:
                    logger.error("❌ [AUTH] OOB mode requires an interaction_callback.")
                    return False

                flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
                auth_url, _ = flow.authorization_url(prompt="consent")

                # Delegate IO to callback
                code = interaction_callback(auth_url)

                if not code:
                    logger.error("❌ [AUTH] No code provided by user.")
                    return False

                flow.fetch_token(code=code)

            else: # interactive
                # run_local_server handles the browser opening
                creds = flow.run_local_server(port=0)

            creds = flow.credentials
            self._save_to_json(channel, creds)
            logger.success(f"✅ [AUTH] Authentication successful for {channel.upper()}!")
            return True

        except Exception as e:
            logger.error(f"❌ [AUTH] Authentication failed: {e}")
            return False

    def _validate_scopes(self, creds: Credentials) -> bool:
        """SOTA 2026: Checks if credentials have ALL required scopes."""
        if not creds or not creds.scopes:
            return False # No scopes info = Unsafe

        current = set(creds.scopes)
        required = set(SCOPES)

        if not required.issubset(current):
            logger.debug(f"🔍 [AUTH] Missing scopes: {required - current}")
            return False
        return True

    def _load_from_json(self, channel: str) -> Optional[Credentials]:
        """Loads token from local JSON file."""
        channel_config = CHANNELS[channel]
        token_path = self.secrets_dir / channel_config["token_file"]

        if token_path.exists():
            try:
                with open(token_path, "r") as f:
                    data = json.load(f)
                    creds = Credentials.from_authorized_user_info(data, SCOPES)
                    return creds
            except Exception as e:
                logger.warning(f"⚠️ [AUTH] Failed to load JSON for {channel}: {e}")
        return None

    def _save_to_json(self, channel: str, creds: Credentials) -> None:
        """Saves token to local JSON file."""
        channel_config = CHANNELS[channel]
        token_path = self.secrets_dir / channel_config["token_file"]
        try:
            json_content = creds.to_json()
            with open(token_path, "w") as f:
                f.write(json_content)
            logger.info(f"💾 [AUTH] Token saved to {token_path}")
        except Exception as e:
            logger.error(f"❌ [AUTH] Failed to save JSON: {e}")

    def _load_from_env(self, channel: str) -> Optional[Credentials]:
        """Loads token from Environment Variable (Base64 JSON)."""
        channel_config = CHANNELS[channel]
        token_b64 = os.getenv(channel_config["token_env"])

        if token_b64:
            try:
                token_json = base64.b64decode(token_b64).decode("utf-8")
                token_info = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
                return creds
            except Exception as e:
                logger.warning(f"⚠️ [AUTH] Env auth failed for {channel}: {e}")
        return None

    def _get_client_config(self) -> Optional[Dict[str, Any]]:
        """
        Resolves Client Secrets from File or Env.
        Returns dict with either "path" (str) or "config_dict" (dict).
        """
        # 1. Try Env Secrets (JSON string or Base64)
        secrets_env = os.getenv("GOOGLE_CLIENT_SECRETS_JSON") or os.getenv("CLIENT_SECRETS_JSON")
        if not secrets_env:
            b64_env = os.getenv("YOUTUBE_OAUTH_CLIENT_BASE64") or os.getenv("GOOGLE_CLOUD_2_OAUTH_BASE64")
            if b64_env:
                try:
                    secrets_env = base64.b64decode(b64_env).decode("utf-8")
                except Exception:
                    pass

        if secrets_env:
            try:
                return {"config_dict": json.loads(secrets_env)}
            except Exception as e:
                logger.warning(f"⚠️ [AUTH] Failed to parse Env Secrets: {e}")

        # 2. Try File
        secrets_path = self.secrets_dir / "client_secrets.json"
        if secrets_path.exists():
            return {"path": str(secrets_path)}

        return None

# Singleton Instance
auth_manager = GoogleAuthManager()


def cli_interaction_callback(auth_url: str) -> str:
    """Default CLI interaction callback."""
    print("\n" + "=" * 80)
    print(f"🔓 TRINITY - AUTHENTIFICATION OOB")
    print("=" * 80)
    print("1. Click/Open this link:")
    print(f"{auth_url}")
    print("2. Copy the code displayed.")
    print("=" * 80)
    return input("📋 PASTE CODE HERE: ").strip()


def main():
    """CLI Entry Point"""
    parser = argparse.ArgumentParser(description="Trinity YouTube Auth Manager")
    parser.add_argument("--channel", choices=["en", "fr", "all"], default="en", help="Target channel")
    parser.add_argument("--mode", choices=["interactive", "oob"], default="interactive", help="Auth mode")
    parser.add_argument("--force", action="store_true", help="Force re-authentication")

    args = parser.parse_args()

    channels = ["en", "fr"] if args.channel == "all" else [args.channel]

    success = True
    for ch in channels:
        print(f"\nProcessing Channel: {ch.upper()}")

        # Use local callback for CLI
        cb = cli_interaction_callback if args.mode == "oob" else None

        if not auth_manager.authenticate(channel=ch, mode=args.mode, force=args.force, interaction_callback=cb):
            success = False
            print(f"❌ Failed to authenticate {ch.upper()}")
        else:
            print(f"✅ Authenticated {ch.upper()}")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
