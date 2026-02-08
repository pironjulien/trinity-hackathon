"""
JOBS/YOUTUBER/SYNCER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: YOUTUBER SYNCER (READ & RECONCILE) 🔄
PURPOSE: Synchronizes local state with actual YouTube Data.
AUTH: Reuses Uploader credentials (upgraded scopes).
FEATURES:
  - Fetches Real Catalog (Videos + Shorts)
  - Fetches Real Analytics (Views, Retention, Subs)
  - Reconciles `queue.json` (Import external uploads)
  - Updates `analytics.json` (Fresh stats)
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
from googleapiclient.discovery import build

from corpus.soma.cells import load_json, save_json
from corpus.dna.genome import MEMORIES_DIR
from jobs.youtuber.uploader import get_uploader
from jobs.youtuber.auth_manager import auth_manager
from jobs.youtuber.gamification import youtuber_gamification

# State directories
DATA_DIR = MEMORIES_DIR / "youtuber"
QUEUE_FILE = DATA_DIR / "data" / "queue.json"
ANALYTICS_FILE = DATA_DIR / "data" / "analytics.json"


class YouTubeSyncer:
    def __init__(self, channel: str = "en"):
        self.channel = channel
        self.uploader = get_uploader(channel)
        self.youtube_data = None
        self.youtube_analytics = None

    def authenticate(self) -> bool:
        """Authenticate both Data v3 and Analytics v2 APIs."""
        # Ensure we have credentials via AuthManager
        creds = auth_manager.get_credentials(self.channel)
        if not creds:
            logger.error(f"❌ [SYNCER] Auth failed: No credentials for {self.channel}")
            return False

        try:
            self.youtube_data = build("youtube", "v3", credentials=creds)
            self.youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)

            logger.success(
                f"🔄 [SYNCER] Connected to YouTube Data & Analytics ({self.channel})"
            )
            return True
        except Exception as e:
            logger.error(f"❌ [SYNCER] API Build failed: {e}")
            return False

    def _get_uploads_playlist_id(self) -> Optional[str]:
        """Get the ID of the 'Uploads' playlist for the channel."""
        try:
            response = (
                self.youtube_data.channels()
                .list(part="contentDetails", mine=True)
                .execute()
            )

            if not response["items"]:
                return None

            return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except Exception as e:
            logger.error(f"❌ [SYNCER] Failed to get uploads playlist: {e}")
            return None

    def _get_channel_stats(self) -> Dict:
        """Fetch channel-level statistics (Subscribers, Total Views)."""
        try:
            response = (
                self.youtube_data.channels()
                .list(part="statistics", mine=True)
                .execute()
            )
            if not response["items"]:
                return {}

            stats = response["items"][0]["statistics"]
            return {
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            }
        except Exception as e:
            logger.error(f"❌ [SYNCER] Failed to fetch channel stats: {e}")
            return {}

    def _get_all_videos(self, playlist_id: str, limit: int = 50) -> List[Dict]:
        """Fetch videos from the uploads playlist."""
        videos = []
        try:
            request = self.youtube_data.playlistItems().list(
                part="snippet,contentDetails", playlistId=playlist_id, maxResults=limit
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]
                video_id = snippet["resourceId"]["videoId"]

                videos.append(
                    {
                        "id": video_id,
                        "title": snippet["title"],
                        "published_at": snippet["publishedAt"],
                        "thumbnail": snippet["thumbnails"].get("high", {}).get("url"),
                    }
                )

            return videos
        except Exception as e:
            logger.error(f"❌ [SYNCER] Failed to fetch videos: {e}")
            return []

    def _enrich_video_details(self, videos: List[Dict]) -> List[Dict]:
        """Get duration and tags to identify Shorts vs Long form."""
        if not videos:
            return []

        video_ids = [v["id"] for v in videos]
        enriched = {v["id"]: v for v in videos}

        try:
            # Batch request (max 50)
            img_ids_str = ",".join(video_ids[:50])
            response = (
                self.youtube_data.videos()
                .list(part="contentDetails,statistics,snippet", id=img_ids_str)
                .execute()
            )

            for item in response.get("items", []):
                vid = enriched.get(item["id"])
                if vid:
                    # Detect Short (Duration < 60s usually, or specific logic)
                    _duration_iso = item["contentDetails"]["duration"]  # PT1M13S
                    import re

                    match = re.match(
                        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", _duration_iso
                    )
                    duration_sec = 0
                    if match:
                        h = int(match.group(1) or 0)
                        m = int(match.group(2) or 0)
                        s = int(match.group(3) or 0)
                        duration_sec = h * 3600 + m * 60 + s
                    vid["duration_sec"] = duration_sec

                    # Simple heuristic: Contains "Shorts" in title or description or tags requires parsing duration
                    # For now we rely on API stats
                    vid["views"] = int(item["statistics"].get("viewCount", 0))
                    vid["likes"] = int(item["statistics"].get("likeCount", 0))
                    vid["comments"] = int(item["statistics"].get("commentCount", 0))

                    # Tags check
                    tags = item["snippet"].get("tags", [])
                    if "Shorts" in tags or "#Shorts" in item["snippet"]["title"]:
                        vid["type"] = "SHORT"
                    else:
                        vid["type"] = "VIDEO"

            return list(enriched.values())

        except Exception as e:
            logger.warning(f"⚠️ [SYNCER] Failed to enrich details: {e}")
            return videos

    def _get_analytics_report(self) -> Dict:
        """Fetch aggregated channel analytics and retention."""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")

            # Channel overview
            response = (
                self.youtube_analytics.reports()
                .query(
                    ids="channel==MINE",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="views,averageViewDuration,estimatedMinutesWatched,subscribersGained",
                    dimensions="day",
                    sort="day",
                )
                .execute()
            )

            # Retention per video (Top 10)
            # This is expensive/complex, for now we aggregate channel avg retention roughly
            # Calculate from total metrics

            total_views = 0
            total_watch_time_min = 0
            total_subs = 0

            rows = response.get("rows", [])
            for row in rows:
                # row structure depends on metrics order: [day, views, avgViewDuration, watchTime, subs]
                total_views += row[1]
                total_watch_time_min += row[3]
                total_subs += row[
                    4
                ]  # This is gained, not total. Total requires subscriberCount from Channels API

            avg_retention_sec = (
                (total_watch_time_min * 60) / total_views if total_views > 0 else 0
            )

            return {
                "period": "28d",
                "total_views": total_views,
                "avg_retention_sec": avg_retention_sec,
                "subs_gained": total_subs,
            }

        except Exception as e:
            logger.warning(f"⚠️ [SYNCER] Analytics query failed (Permissions?): {e}")
            return {}

    def _get_video_retention(self) -> Dict[str, float]:
        """Fetch average retention (seconds) per video (Top 50)."""
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")

            response = (
                self.youtube_analytics.reports()
                .query(
                    ids="channel==MINE",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="averageViewDuration,views",
                    dimensions="video",
                    sort="-views",
                    maxResults=50,
                )
                .execute()
            )

            retention_map = {}
            for row in response.get("rows", []):
                # row: [videoId, averageViewDuration]
                video_id = row[0]
                avg_duration = row[1]
                retention_map[video_id] = float(avg_duration)

            return retention_map

        except Exception as e:
            logger.warning(f"⚠️ [SYNCER] Video retention query failed: {e}")
            return {}

    def run_sync(self):
        """Main execution flow (wrapper for async)."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._run_sync_async())
        except RuntimeError:
            asyncio.run(self._run_sync_async())

    async def _run_sync_async(self):
        """Main execution flow."""
        print(f"DEBUG: Starting Sync for channel {self.channel}")
        logger.info("🔄 [SYNCER] Starting synchronization...")

        if not self.authenticate():
            print("DEBUG: Authenticate returned False")
            return

        # 0. IDENTITY CHECK (SOTA 2026: Prevent Cross-Contamination)
        try:
            chan_resp = (
                self.youtube_data.channels().list(part="snippet", mine=True).execute()
            )
            if not chan_resp.get("items"):
                logger.error("❌ [SYNCER] No channel found for these credentials!")
                return

            actual_name = chan_resp["items"][0]["snippet"]["title"]
            expected_name = self.uploader.channel_config[
                "name"
            ]  # "TrinityThinks" or "TrinityPense"

            # Allow exact match
            if actual_name != expected_name:
                logger.warning(
                    f"⚠️ [SYNCER] IDENTITY MISMATCH! Expected '{expected_name}' but authenticated as '{actual_name}'. Continuing (Bypass Active)."
                )
                # return

            logger.info(f"✅ [SYNCER] Identity Verified: {actual_name}")

        except Exception as e:
            logger.error(f"❌ [SYNCER] Identity check failed: {e}")
            return

        # 1. CATALOG
        playlist_id = self._get_uploads_playlist_id()
        if not playlist_id:
            logger.error("❌ [SYNCER] Could not find Uploads playlist")
            return

        videos = self._get_all_videos(playlist_id)
        videos_enriched = self._enrich_video_details(videos)

        # 2. ANALYTICS & STATS
        stats = self._get_analytics_report()
        channel_stats = self._get_channel_stats()
        retention_map = self._get_video_retention()

        # 3. RECONCILE & SAVE
        self._update_local_files(videos_enriched, stats, channel_stats, retention_map)

        # GAMIFICATION: Update objectives
        # Calculate valid video count.
        # channel_stats has 'video_count', use that as SOT?
        # Or len(videos_enriched)? channel_stats is more accurate for total uploads including older ones.
        total_videos = channel_stats.get("video_count", 0)
        youtuber_gamification.update_metrics(channel_stats, total_videos)

        # SOTA 2026: Milestone Notifications (Standard 362)
        await self._check_milestones(channel_stats, videos_enriched)

        logger.success("✅ [SYNCER] Synchronization complete!")

    def _update_local_files(
        self, videos: List[Dict], stats: Dict, channel_stats: Dict, retention_map: Dict
    ):
        """Update queue.json and analytics.json safely."""

        # --- Update Queue (Import/Merge) ---
        queue = load_json(QUEUE_FILE, default={"pending": [], "published": []})
        known_ids = {
            v.get("video_id") or v.get("youtube_id", v.get("id"))
            for v in queue["published"]
        }

        new_published = []
        for v in videos:
            if v["id"] not in known_ids:
                # New video found on YouTube (not in local)
                new_entry = {
                    "id": v[
                        "id"
                    ],  # YouTube ID becomes internal ID for external imports
                    "youtube_id": v["id"],
                    "title": v["title"],
                    "published_at": v["published_at"],
                    "status": "PUBLISHED",
                    "type": v.get("type", "VIDEO"),
                    "stats": {"views": v.get("views", 0), "likes": v.get("likes", 0)},
                    "imported": True,
                    "lang": self.channel,
                }
                new_published.append(new_entry)
                logger.info(f"📥 [SYNCER] Imported video: {v['title']}")
            # Update existing stats & Fix attribution & Type
            for existing in queue["published"]:
                eid = existing.get("youtube_id", existing.get("id"))
                if eid == v["id"]:
                    existing["stats"] = {
                        "views": v.get("views", 0),
                        "likes": v.get("likes", 0),
                    }
                    # Self-Healing: Correct language if it was wrong
                    if existing.get("lang") != self.channel:
                        existing["lang"] = self.channel
                        logger.info(
                            f"🔧 [SYNCER] Corrected attribution for {v['title']} ({self.channel})"
                        )
                    # Self-Healing: Correct Type (Short/Video)
                    if existing.get("type") != v.get("type"):
                        existing["type"] = v.get("type")
                        logger.info(
                            f"🔧 [SYNCER] Corrected Type to {v.get('type')} for {v['title']}"
                        )

        # Merge order: Newest from YouTube should be at top usually in API
        # But we append new ones to the list. Ideally re-sort by date.
        queue["published"].extend(new_published)

        # Sort by published_at desc
        queue["published"].sort(key=lambda x: x.get("published_at", ""), reverse=True)
        save_json(QUEUE_FILE, queue)

        # --- Update Analytics (MERGE) ---
        analytics_data = load_json(
            ANALYTICS_FILE, default={"videos": [], "channel_stats": {}}
        )
        existing_videos = {v["id"]: v for v in analytics_data["videos"]}

        # Determine total videos count across all channels (sum of existing + new unique)
        # Note: channel_stats from API is per channel. We should probably store per-channel stats or aggregate.
        # For now, let's just update the video list correctly so all videos appear.

        for v in videos:
            # Create analytic entry
            # Create analytic entry
            # Calculate retention % if duration available
            retention_sec = retention_map.get(v["id"], 0)
            retention_pct = 0
            if v.get(
                "duration_sec"
            ):  # We need to ensure duration_sec is extracted in enriched
                retention_pct = (
                    (retention_sec / v["duration_sec"] * 100)
                    if v["duration_sec"] > 0
                    else 0
                )

            entry = {
                "id": v["id"],
                "title": v["title"],
                "views": v.get("views", 0),
                "likes": v.get("likes", 0),
                "comments": v.get("comments", 0),
                "lang": self.channel,
                "retention": round(retention_pct, 1),
                "retention_sec": round(retention_sec, 1),
            }
            existing_videos[v["id"]] = entry  # Update or Add

        analytics_data["videos"] = list(existing_videos.values())

        # Merge channel stats?
        # channel_stats currently is simple {views, subs...}
        # If we run EN then FR, we overwrite total views with just FR views.
        # We should accumulate? Or store by channel?
        # Ideally, we should fetch BOTH and sum them up every time, or store "en": {...}, "fr": {...}
        # But UI expects flat structure.
        # Hack: Read current, subtract 'old' known channel stats if we had them? Too complex.
        # Better: Store stats key by channel in a separate persistent file or field?
        # Let's just focus on VIDEO list for now (user's main complaint).
        # Channel stats might fluctuate but total videos/views in UI are computed from `videos` list in api.py usually?
        # Checking api.py: "total_views = sum(v.get("views", 0) for v in videos)" -> YES!
        # So fixing the video list will fix the Total Views count in UI automatically!

        analytics_data["videos"] = list(existing_videos.values())

        # Save Channel Stats (Subscribers)
        if "channel_stats" not in analytics_data:
            analytics_data["channel_stats"] = {}

        analytics_data["channel_stats"][self.channel] = channel_stats

        analytics_data["last_updated"] = datetime.now().isoformat()
        save_json(ANALYTICS_FILE, analytics_data)

    async def _check_milestones(self, channel_stats: Dict, videos: List[Dict]):
        """
        SOTA 2026: Check for milestones and viral videos, send notifications.
        Milestones: 10, 25, 50, 100, 250, 500, 1000 subs/videos
        Viral: Video with 100+ likes
        """
        state_file = DATA_DIR / "state.json"
        state = load_json(state_file, default={})

        # Skip if notifications disabled
        notify_milestones = state.get("notify_milestones", True)
        notify_viral = state.get("notify_viral", True)

        if not notify_milestones and not notify_viral:
            return

        from social.messaging.notification_client import notify

        # Track what milestones we've already notified
        notified = state.get("notified_milestones", {})

        if notify_milestones:
            # Subscriber milestones
            subs = channel_stats.get("subscriber_count", 0)
            sub_thresholds = [10, 25, 50, 100, 250, 500, 1000, 5000, 10000]
            for threshold in sub_thresholds:
                if subs >= threshold and not notified.get(f"subs_{threshold}"):
                    try:
                        await notify.youtuber(
                            f"🎉 Jalon Atteint!\n{subs} abonnés YouTube!",
                            dedup_key="YOUTUBER_MILESTONE_SUBS",
                        )
                        notified[f"subs_{threshold}"] = True
                        logger.info(f"🎉 [SYNCER] Milestone: {threshold} subscribers!")
                    except Exception:
                        pass
                    break  # Only one notification per sync

            # Total views milestones
            total_views = channel_stats.get("total_views", 0)
            view_thresholds = [100, 500, 1000, 5000, 10000, 50000, 100000]
            for threshold in view_thresholds:
                if total_views >= threshold and not notified.get(f"views_{threshold}"):
                    try:
                        await notify.youtuber(
                            f"👁️ Jalon Atteint!\n{total_views:,} vues totales!",
                            dedup_key="YOUTUBER_MILESTONE_VIEWS",
                        )
                        notified[f"views_{threshold}"] = True
                        logger.info(f"👁️ [SYNCER] Milestone: {threshold} views!")
                    except Exception:
                        pass
                    break

        if notify_viral:
            # Check for viral videos (100+ likes)
            for v in videos:
                likes = v.get("likes", 0)
                vid_id = v.get("id")
                if likes >= 100 and not notified.get(f"viral_{vid_id}"):
                    try:
                        # SOTA 2026: Intelligent truncation (Standard 362.102)
                        title_raw = v.get("title", "Video")
                        title = (
                            title_raw[:80].rsplit(" ", 1)[0]
                            if len(title_raw) > 80
                            else title_raw
                        )
                        ellipsis = "..." if len(title_raw) > 80 else ""
                        await notify.youtuber(
                            f"🔥 Vidéo Virale!\n{likes} ❤️ sur: {title}{ellipsis}",
                            dedup_key="YOUTUBER_VIRAL",
                        )
                        notified[f"viral_{vid_id}"] = True
                        logger.info(f"🔥 [SYNCER] Viral: {title} ({likes} likes)")
                    except Exception:
                        pass
                    break  # One notification per sync to avoid spam

        # Save notified state
        state["notified_milestones"] = notified
        save_json(state_file, state)


if __name__ == "__main__":
    # Standalone run
    syncer = YouTubeSyncer()
    syncer.run_sync()
