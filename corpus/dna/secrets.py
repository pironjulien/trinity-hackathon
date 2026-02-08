"""
CORPUS/DNA/SECRETS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SECRETS (THE VAULT) 🔐
PURPOSE: Load and secure credentials (API Key, GCP).
SECURITY: Strictly IN-MEMORY. No disk writes.
══════════════════════════════════════════════════════════════════════════════

"""

import os
import base64
import json
from typing import Optional, Any
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


class Vault:
    """
    The in-memory vault.
    Stores nothing, reads environment on demand.

    """

    @property
    def GEMINI_API_KEY(self) -> str:
        """Standard Gemini API Key."""
        return os.getenv("GOOGLE_API_KEY", "")



    @property
    def GCP_PROJECT_ID(self) -> str:
        """Google Cloud Project ID."""
        return self._get_required("GOOGLE_CLOUD_PROJECT")

    @property
    def GCP_CREDENTIALS_JSON(self) -> dict[str, Any]:
        """GCP Service Account credentials."""
        b64 = self._get_required("GOOGLE_CLOUD_CREDENTIALS_BASE64")
        return self._decode_base64_json(b64)

    @property
    def GOOGLE_JULES_API_KEY(self) -> str:
        """Google Jules API Key."""
        return self._get_required("GOOGLE_JULES_API_KEY")

    @property
    def GITHUB_TOKEN(self) -> str:
        """GitHub Token for auto-update."""
        return self._get_required("GITHUB_TOKEN")

    @property
    def GCP_1_PROJECT_ID(self) -> str:
        return self._get_required("GOOGLE_CLOUD_1_PROJECT")

    @property
    def GCP_1_CREDENTIALS_JSON(self) -> dict[str, Any]:
        b64 = self._get_required("GOOGLE_CLOUD_1_CREDENTIALS_BASE64")
        return self._decode_base64_json(b64)

    def _decode_base64_json(self, b64: str) -> dict[str, Any]:
        try:
            clean_b64 = b64.strip('"').strip("'")
            decoded = base64.b64decode(clean_b64).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            raise ValueError("GCP Credentials corrupted")

    # --- JOB CREDENTIALS ---
    @property
    def KRAKEN_API_KEY(self) -> Optional[str]:
        return os.getenv("KRAKEN_API_KEY")

    @property
    def KRAKEN_SECRET(self) -> Optional[str]:
        return os.getenv("KRAKEN_SECRET")

    def _get_required(self, key_name: str) -> str:
        val = os.getenv(key_name)
        if not val:
            return ""
        return val


# Singleton Instance
vault = Vault()
