"""
JOBS/YOUTUBER/SCHEDULER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SCHEDULER (CLOCK) ⏱️
PURPOSE: Manager intelligent de la file d'attente de publication.
FEATURES:
  - File FIFO persistante
  - Auto-scheduling basé sur les analytics (heure optimale)
  - Rate limiting (1 vidéo / jour max)
══════════════════════════════════════════════════════════════════════════════
"""

import datetime
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR

# Analytics file (partagé avec producer)
ANALYTICS_FILE = MEMORIES_DIR / "youtuber" / "data" / "analytics.json"


class VideoScheduler:
    """
    Ordonnanceur intelligent de publications.

    Features:
    - File d'attente FIFO persistante
    - Calcul de l'heure optimale basé sur les analytics
    - Rate limiting (1 upload/jour par défaut)
    """

    # Heures par défaut si pas de data (19h Paris = afterwork)
    DEFAULT_OPTIMAL_HOURS = [19, 20, 18, 21, 17]

    def __init__(self):
        self.queue_file = MEMORIES_DIR / "youtuber" / "data" / "queue.json"
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # QUEUE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def add_to_queue(
        self, video_path: Path, metadata: Dict, schedule_for: datetime.datetime = None
    ) -> bool:
        """
        Ajoute une vidéo à la file d'attente.

        Args:
            video_path: Chemin vers le fichier vidéo
            metadata: {title, description, tags}
            schedule_for: Heure de publication (optionnel, sinon auto-calculé)
        """
        queue = load_json(self.queue_file, default={"pending": [], "published": []})

        # Auto-scheduling si pas d'heure spécifiée
        if not schedule_for:
            schedule_for = self.get_optimal_publish_time()

        entry = {
            "id": datetime.datetime.now().isoformat(),
            "path": str(video_path),
            "metadata": metadata,
            "scheduled_for": schedule_for.isoformat(),
            "status": "PENDING",
        }

        queue["pending"].append(entry)
        save_json(self.queue_file, queue)

        logger.info(f"⏱️ [SCHEDULER] Queued: {metadata.get('title')}")
        logger.info(f"   📅 Scheduled for: {schedule_for.strftime('%Y-%m-%d %H:%M')}")
        return True

    def get_next_due(self) -> Optional[Dict]:
        """
        Récupère la prochaine vidéo à publier SI l'heure est venue.

        Returns:
            Video entry si une est due, None sinon
        """
        queue = load_json(self.queue_file, default={"pending": []})

        if not queue.get("pending"):
            return None

        now = datetime.datetime.now()

        for video in queue["pending"]:
            scheduled = datetime.datetime.fromisoformat(
                video.get("scheduled_for", now.isoformat())
            )

            if now >= scheduled:
                logger.info(
                    f"⏱️ [SCHEDULER] Video ready: {video.get('metadata', {}).get('title')}"
                )
                return video

        # Rien de prêt
        next_video = queue["pending"][0]
        next_time = datetime.datetime.fromisoformat(
            next_video.get("scheduled_for", now.isoformat())
        )
        logger.debug(
            f"⏱️ [SCHEDULER] Next video in {(next_time - now).seconds // 60} minutes"
        )
        return None

    def mark_published(self, video_id: str, youtube_id: str):
        """Marque une vidéo comme publiée."""
        queue = load_json(self.queue_file, default={"pending": [], "published": []})

        # Trouve la vidéo
        published_video = None
        for v in queue["pending"]:
            if v["id"] == video_id:
                published_video = v
                break

        # Retire de pending, ajoute à published
        queue["pending"] = [v for v in queue["pending"] if v["id"] != video_id]

        if published_video:
            published_video["youtube_id"] = youtube_id
            published_video["published_at"] = datetime.datetime.now().isoformat()
            published_video["status"] = "PUBLISHED"

            if "published" not in queue:
                queue["published"] = []
            queue["published"].append(published_video)

            # Garde les 50 dernières publiées
            queue["published"] = queue["published"][-50:]

        save_json(self.queue_file, queue)
        logger.success(f"✅ [SCHEDULER] Published: {youtube_id}")

        # 🔗 Direct Plugin: Signal Influencer for X cross-posting
        if published_video:
            try:
                import asyncio
                from jobs.influencer.poster import poster  # type: ignore[import-not-found]

                video_path = Path(published_video.get("path", ""))
                youtube_url = f"https://youtube.com/shorts/{youtube_id}"
                metadata = published_video.get("metadata", {})

                # SOTA: Inject rich context from launch_queue.json
                try:
                    # Extract day info from path (e.g. "day00_l_eveil" -> 0)
                    path_str = str(
                        video_path.name if isinstance(video_path, Path) else video_path
                    )
                    if "day" in path_str:
                        day_part = path_str.split("_")[0].replace("day", "")
                        day_idx = int(day_part)

                        launch_queue_path = (
                            MEMORIES_DIR / "youtuber" / "data" / "launch_queue.json"
                        )
                        launch_data = load_json(launch_queue_path)

                        # Find matching day
                        launch_entry = next(
                            (
                                item
                                for item in launch_data.get("launch_queue", [])
                                if item.get("day") == day_idx
                            ),
                            None,
                        )

                        if launch_entry:
                            # Add full script content to metadata
                            lang = metadata.get("lang", "fr")
                            script_key = f"script_{lang}"
                            if script_key in launch_entry:
                                metadata["rich_context"] = launch_entry[script_key]
                                logger.info(
                                    f"   🧠 [SCHEDULER] Injected rich context for Day {day_idx}"
                                )
                except Exception as e:
                    logger.warning(f"   ⚠️ [SCHEDULER] Context injection failed: {e}")

                # Fire and forget (non-blocking)
                asyncio.create_task(
                    poster.on_youtube_published(video_path, youtube_url, metadata)
                )
                logger.info("📱 [SCHEDULER] Signaled Influencer for X cross-post")

            except Exception as e:
                # Graceful Degradation: Influencer failure doesn't break YouTuber
                logger.warning(
                    f"📱 [SCHEDULER] Influencer signal failed (graceful): {e}"
                )

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTO-SCHEDULING (basé sur analytics)
    # ═══════════════════════════════════════════════════════════════════════════

    def get_optimal_publish_time(self) -> datetime.datetime:
        """
        Calcule l'heure optimale de publication basée sur les analytics.

        Stratégie:
        1. Analyse les heures de publication des meilleures vidéos
        2. Si pas de data, utilise les heures par défaut (19h)
        3. Trouve le prochain créneau disponible (rate limit 1/jour)

        Returns:
            datetime pour la prochaine publication
        """
        optimal_hour = self._calculate_best_hour()
        next_slot = self._get_next_available_slot(optimal_hour)

        return next_slot

    def _calculate_best_hour(self) -> int:
        """Calcule la meilleure heure basée sur les analytics."""
        analytics = load_json(ANALYTICS_FILE, default={"videos": []})

        videos = analytics.get("videos", [])
        if len(videos) < 3:
            # Pas assez de data, utilise le défaut
            return self.DEFAULT_OPTIMAL_HOURS[0]

        # Analyse les heures des vidéos avec bonne retention
        hour_performance = {}

        for video in videos:
            published_at = video.get("date", "")
            retention = video.get("retention", 0)

            if published_at and retention > 0:
                try:
                    dt = datetime.datetime.fromisoformat(published_at)
                    hour = dt.hour

                    if hour not in hour_performance:
                        hour_performance[hour] = []
                    hour_performance[hour].append(retention)
                except Exception:
                    continue

        if not hour_performance:
            return self.DEFAULT_OPTIMAL_HOURS[0]

        # Trouve l'heure avec la meilleure retention moyenne
        best_hour = max(
            hour_performance.keys(),
            key=lambda h: sum(hour_performance[h]) / len(hour_performance[h]),
        )

        logger.debug(f"📊 [SCHEDULER] Best hour from analytics: {best_hour}h")
        return best_hour

    def _get_next_available_slot(self, target_hour: int) -> datetime.datetime:
        """
        Trouve le prochain créneau disponible (rate limit).

        Returns:
            datetime du prochain slot disponible
        """
        queue = load_json(self.queue_file, default={"pending": [], "published": []})
        now = datetime.datetime.now()

        # Trouve la dernière publication
        last_publish = None
        for v in queue.get("published", []):
            pub_time = v.get("published_at")
            if pub_time:
                try:
                    dt = datetime.datetime.fromisoformat(pub_time)
                    # Strip timezone to avoid naive vs aware comparison
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    if not last_publish or dt > last_publish:
                        last_publish = dt
                except Exception:
                    continue

        # Rate limit: au moins 48h entre deux publications (1 vidéo / 2 jours)
        min_next = now
        if last_publish:
            min_next = max(now, last_publish + datetime.timedelta(hours=48))

        # Trouve le prochain créneau à target_hour
        candidate = min_next.replace(
            hour=target_hour, minute=0, second=0, microsecond=0
        )

        if candidate <= min_next:
            # Déjà passé aujourd'hui, prend demain
            candidate += datetime.timedelta(days=1)

        return candidate

    def get_queue_status(self) -> Dict:
        """Retourne le statut actuel de la queue."""
        queue = load_json(self.queue_file, default={"pending": [], "published": []})

        return {
            "pending_count": len(queue.get("pending", [])),
            "published_count": len(queue.get("published", [])),
            "next_scheduled": queue["pending"][0].get("scheduled_for")
            if queue.get("pending")
            else None,
            "optimal_hour": self._calculate_best_hour(),
        }

    def is_upload_window_open(self) -> tuple[bool, float]:
        """
        Check if 48h passed since last upload.
        Returns: (is_open, hours_remaining)
        """
        queue = load_json(self.queue_file, default={"pending": [], "published": []})
        now = datetime.datetime.now()

        # Last pub
        last_publish = None
        for v in queue.get("published", []):
            pub_time = v.get("published_at")
            if pub_time:
                try:
                    dt = datetime.datetime.fromisoformat(pub_time)
                    if not last_publish or dt > last_publish:
                        last_publish = dt
                except Exception:
                    continue

        if not last_publish:
            return True, 0.0

        # Normalize to naive datetime for comparison
        if last_publish.tzinfo is not None:
            last_publish = last_publish.replace(tzinfo=None)

        next_allowed = last_publish + datetime.timedelta(hours=48)

        if now >= next_allowed:
            return True, 0.0

        remaining = (next_allowed - now).total_seconds() / 3600
        return False, remaining


# Singleton
scheduler = VideoScheduler()
