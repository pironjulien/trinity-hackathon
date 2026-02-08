"""
JOBS/YOUTUBER/GAMIFICATION.PY
==============================================================================
MODULE: YOUTUBER GAMIFICATION 🎮
PURPOSE: Rewards for channel growth and content creation.
==============================================================================
"""

from typing import Dict
from corpus.dopamine import manager, Objective, RewardType


class YouTuberGamification:
    """
    Gamified reward system (YouTuber Adapter).
    """

    def __init__(self):
        self._register_objectives()

    def _register_objectives(self):
        """Register channel milestones."""

        # --- VIDEO UPLOADS ---
        upload_milestones = [1, 5, 10, 50, 100, 200, 500, 1000]
        for milestone in upload_milestones:
            obj_id = f"youtube_uploads_{milestone}"
            manager.register(
                Objective(
                    id=obj_id,
                    domain="YOUTUBE",
                    title=f"Broadcast Empire: {milestone}",
                    description=f"Build the library. Upload {milestone} videos.",
                    target_value=milestone,
                    unit="vids",
                    reward_amount=0.5,
                    reward_type=RewardType.DOPAMINE,
                    icon="Video",
                )
            )

        # --- SUBSCRIBERS ---
        sub_milestones = [100, 500, 1000, 5000, 10000, 25000, 50000, 100000]
        for milestone in sub_milestones:
            obj_id = f"youtube_subs_{milestone}"
            manager.register(
                Objective(
                    id=obj_id,
                    domain="YOUTUBE",
                    title=f"Audience Growth: {milestone}",
                    description=f"Grow the tribe to {milestone} subscribers.",
                    target_value=milestone,
                    unit="subs",
                    reward_amount=0.8,
                    reward_type=RewardType.SEROTONIN,  # Long term satisfaction
                    icon="Users",
                )
            )

        # --- TOTAL VIEWS ---
        view_milestones = [1000, 5000, 10000, 50000, 100000, 1000000, 5000000, 10000000]
        for milestone in view_milestones:
            obj_id = f"youtube_views_{milestone}"
            manager.register(
                Objective(
                    id=obj_id,
                    domain="YOUTUBE",
                    title=f"Viral Hit: {milestone} Views",
                    description=f"Accumulate {milestone} total channel views.",
                    target_value=milestone,
                    unit="views",
                    reward_amount=min(1.0, milestone / 50000),
                    reward_type=RewardType.DOPAMINE,
                    icon="Eye",
                )
            )

    def update_metrics(self, stats: Dict, total_videos: int):
        """
        Update objectives based on synced stats.
        Args:
            stats: Dict with 'total_views', 'subscriber_count' (from channel stats)
            total_videos: Count of uploaded videos
        """
        # Uploads
        uploads = [1, 5, 10, 50, 100]
        for m in uploads:
            manager.update_objective(f"youtube_uploads_{m}", float(total_videos))

        # Subscribers
        subs = stats.get("subscriber_count", 0)
        sub_milestones = [100, 500, 1000, 5000, 10000]
        for m in sub_milestones:
            manager.update_objective(f"youtube_subs_{m}", float(subs))

        # Views
        views = stats.get("total_views", 0)
        view_milestones = [1000, 5000, 10000, 50000, 100000, 1000000]
        for m in view_milestones:
            manager.update_objective(f"youtube_views_{m}", float(views))


# Singleton
youtuber_gamification = YouTuberGamification()
