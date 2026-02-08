import sys
import os
import json
import base64
from dotenv import load_dotenv

# Add project root to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
load_dotenv()


def check_redirects():
    print("\n" + "=" * 80)
    print("🔍 INSPECTION CONFIGURATION OAUTH (AVEC DOTENV)")
    print("=" * 80)

    # Load secrets
    client_config = None
    secrets_env = os.getenv("GOOGLE_CLIENT_SECRETS_JSON") or os.getenv(
        "CLIENT_SECRETS_JSON"
    )

    if not secrets_env:
        b64_env = os.getenv("YOUTUBE_OAUTH_CLIENT_BASE64") or os.getenv(
            "GOOGLE_CLOUD_2_OAUTH_BASE64"
        )
        if b64_env:
            try:
                secrets_env = base64.b64decode(b64_env).decode("utf-8")
                print("✅ Secrets trouvés (Base64 Env)")
            except Exception as e:
                print(f"❌ Erreur décodage Base64: {e}")
    else:
        print("✅ Secrets trouvés (JSON Env)")

    if secrets_env:
        try:
            client_config = json.loads(secrets_env)
            # Handle "installed" or "web" wrapper
            inner = client_config.get("installed") or client_config.get("web")
            if inner:
                uris = inner.get("redirect_uris", [])
                print(f"🌐 REDIRECT_URIS AUTORISÉES : {uris}")
            else:
                print("❌ Structure JSON invalide (pas de 'installed' ou 'web')")
        except Exception as e:
            print(f"❌ Erreur parsing JSON: {e}")
    else:
        print("❌ Aucun secret trouvé dans l'environnement.")


if __name__ == "__main__":
    check_redirects()
