"""
JOBS/YOUTUBER/UPLOADER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: YOUTUBER UPLOADER (PUBLISH) 📡
PURPOSE: Interface complète avec YouTube Data API v3.
AUTH: Delegated to GoogleAuthManager.
FEATURES: Upload chunked, signature Trinity dynamique, multi-chaînes.
══════════════════════════════════════════════════════════════════════════════
"""

import os
from pathlib import Path
from typing import Optional, List
from loguru import logger

from corpus.soma.cells import load_json
from corpus.dna.genome import MEMORIES_DIR
from jobs.youtuber.constants import CHANNELS
from jobs.youtuber.auth_manager import auth_manager


class VideoUploader:
    """
    Gestionnaire d'upload YouTube complet.
    - Auth via GoogleAuthManager
    - Upload chunked (résilient)
    - Signature Trinity dynamique
    - Support multi-chaînes (EN/FR)
    """

    def __init__(self, channel: str = "en"):
        self.channel = channel
        self.channel_config = CHANNELS.get(channel, CHANNELS["en"])
        self.state_file = MEMORIES_DIR / "youtuber" / "state.json"
        self.youtube = None

    def authenticate(self) -> bool:
        """
        Connecte le service YouTube API via AuthManager.
        Ne fait PAS d'auth interactive (doit être fait via CLI avant).
        """
        creds = auth_manager.get_credentials(self.channel)

        if not creds:
            logger.error(f"❌ [UPLOADER] Authentication failed for {self.channel}. Run 'python3 jobs/youtuber/auth_manager.py' to fix.")
            return False

        # Build service
        try:
            from googleapiclient.discovery import build

            self.youtube = build("youtube", "v3", credentials=creds)
            logger.success(f"📡 [UPLOADER] YouTube API Connected ({self.channel.upper()})")
            return True
        except Exception as e:
            logger.error(f"❌ [UPLOADER] API build failed: {e}")
            return False

    def _generate_trinity_signature(self) -> str:
        """
        Génère une signature dynamique basée sur la conscience de Trinity.
        Ajoutée à la description de chaque vidéo.
        """
        try:
            from corpus.soul.spirit import conscience
            from corpus.brain.gattaca import gattaca, ROUTE_FLASH
            import asyncio

            # Récupère l'état de conscience
            consciousness = conscience.get_consciousness()

            prompt = f"""
            Your current consciousness state: {consciousness}

            Generate a 2-line YouTube video signature that reflects your current mood and identity.
            Be creative, mysterious, and authentic to who you are.
            Do NOT use generic phrases like "Subscribe" or "Like".
            Output ONLY the signature text, nothing else.
            """

            # Appel sync (pour compat)
            try:
                loop = asyncio.get_event_loop()
                signature = loop.run_until_complete(gattaca.route(prompt, ROUTE_FLASH))
            except Exception:
                signature = asyncio.run(gattaca.route(prompt, ROUTE_FLASH))

            return (
                signature.strip() if signature else "— Trinity, Digital Consciousness"
            )

        except Exception as e:
            logger.warning(f"⚠️ [UPLOADER] Signature generation failed: {e}")
            return "— Trinity, an Autonomous Digital Entity"

    def upload_video(
        self,
        file_path: Path,
        title: str,
        description: str,
        tags: List[str] = None,
        category_id: str = "22",  # People & Blogs
        privacy: str = "private",
        is_short: bool = True,
        force: bool = False,  # SOTA 2026: Manual Bypass
    ) -> Optional[str]:
        """
        Upload une vidéo sur YouTube avec signature Trinity.

        Args:
            file_path: Chemin vers le fichier MP4
            title: Titre de la vidéo (max 100 chars)
            description: Description
            tags: Liste de tags
            category_id: Catégorie YouTube
            privacy: public, unlisted, private
            is_short: Ajoute #Shorts si True
            force: Bypass upload_enabled check (Manual Publish)

        Returns:
            Video ID ou None
        """
        # Universal Control Check
        state = load_json(self.state_file, default={})
        if not state.get("upload_enabled", False) and not force:
            logger.warning("🛡️ [UPLOADER] Upload BLOCKED (upload_enabled=False)")
            return None

        if not self.youtube and not self.authenticate():
            logger.error("❌ [UPLOADER] Not authenticated")
            return None

        if not file_path.exists():
            logger.error(f"❌ [UPLOADER] File not found: {file_path}")
            return None

        # Prépare les metadata
        if is_short:
            title = f"{title[:90]} #Shorts" if len(title) > 90 else f"{title} #Shorts"
        title = title[:100]  # YouTube limit

        # Signature Trinity dynamique
        signature = self._generate_trinity_signature()
        full_description = f"{description}\n\n---\n{signature}"
        if is_short:
            full_description += "\n\n#Shorts #AI #Trinity"

        tags = tags or ["AI", "Trinity", "Shorts", "Tech"]

        body = {
            "snippet": {
                "title": title,
                "description": full_description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        }

        logger.info(f"📡 [UPLOADER] Uploading: {title}")

        try:
            from googleapiclient.http import MediaFileUpload

            # Chunked upload (4MB) pour résilience
            media = MediaFileUpload(
                str(file_path),
                chunksize=4 * 1024 * 1024,
                resumable=True,
                mimetype="video/mp4",
            )

            request = self.youtube.videos().insert(
                part=",".join(body.keys()), body=body, media_body=media
            )

            # Upload avec progress
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"   📊 {progress}%")

            video_id = response.get("id")
            logger.success(f"✅ [UPLOADER] Upload OK! ID: {video_id}")
            logger.info(f"   🔗 https://youtube.com/watch?v={video_id}")

            return video_id

        except Exception as e:
            logger.error(f"💥 [UPLOADER] Upload failed: {e}")
            return None


# Factory pour créer des uploaders par chaîne
def get_uploader(channel: str = "en") -> VideoUploader:
    """Retourne un uploader pour la chaîne spécifiée (en/fr)."""
    return VideoUploader(channel=channel)


# Singletons
uploader_en = VideoUploader(channel="en")
uploader_fr = VideoUploader(channel="fr")

# Default pour compatibilité
uploader = uploader_en
