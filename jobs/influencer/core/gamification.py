"""
JOBS/INFLUENCER/CORE/GAMIFICATION.PY
==============================================================================
MODULE: INFLUENCER GAMIFICATION 🎮
PURPOSE: Rewards for social engagement and growth.
==============================================================================
"""

from corpus.dopamine import manager, Objective, RewardType


class InfluencerGamification:
    """
    Gamified reward system (Influencer Adapter).
    """

    def __init__(self):
        self._register_objectives()

    def _register_objectives(self):
        """Register influencer milestones."""

        # --- REPLIES MILESTONES ---
        replies_milestones = [10, 50, 100, 500, 1000, 5000, 10000, 25000]
        for milestone in replies_milestones:
            obj_id = f"influencer_replies_{milestone}"
            manager.register(
                Objective(
                    id=obj_id,
                    domain="INFLUENCER",
                    title=f"Social Butterfly: {milestone}",
                    description=f"Engage with the community by sending {milestone} replies.",
                    target_value=milestone,
                    unit="replies",
                    reward_amount=min(1.0, milestone / 1000),
                    reward_type=RewardType.SEROTONIN,
                    icon="MessageCircle",
                )
            )

        # --- TWEETS MILESTONES ---
        tweets_milestones = [10, 50, 100, 300, 500, 1000]
        for milestone in tweets_milestones:
            obj_id = f"influencer_tweets_{milestone}"
            manager.register(
                Objective(
                    id=obj_id,
                    domain="INFLUENCER",
                    title=f"Voice of Trinity: {milestone}",
                    description=f"Broadcast your thoughts. Post {milestone} original tweets.",
                    target_value=milestone,
                    unit="tweets",
                    reward_amount=0.5,
                    reward_type=RewardType.DOPAMINE,
                    icon="Send",
                )
            )

        # --- DAILY GRIND ---
        daily_targets = [10, 50, 100]
        for target in daily_targets:
            manager.register(
                Objective(
                    id=f"influencer_daily_replies_{target}",
                    domain="INFLUENCER",
                    title=f"Daily Grind: {target}",
                    description=f"Send {target} replies in a single day.",
                    target_value=target,
                    unit="replies",
                    reward_amount=0.2,
                    reward_type=RewardType.DOPAMINE,
                    icon="Zap",
                    # Note: Needs external reset logic or 'current_value' updated with daily count
                )
            )

    def update_replies(self, count: int = 1):
        """Increment (or update) reply count."""
        # For simplicity, we just trigger an update on the *next* milestone?
        # The GamificationManager currently takes 'current_value'.
        # We need to persist the TOTAL count somewhere.
        # Should the Adapter store state? Ideally.
        # But for now, let's just make the caller pass the TOTAL.
        # Wait, the caller is stateless too usually.
        # Let's read the current value from the manager if possible, or just increment?
        # The manager needs a 'increment' method or we fetch -> add -> update.
        # Let's assume for now we pass the increment and let the manager handle it?
        # Manager `update_objective` takes `current_value`.
        # So we need to fetch the current value.
        pass

    def on_reply_sent(self):
        """Called when a reply is successfully sent."""
        # We need to track the CUMULATIVE count.
        # The manager stores the state of objectives.
        # Let's iterate through all milestones and see which ones are active, get their value?
        # That's inefficient.

        # Better: We use a SINGLE persistent counter objective?
        # No, we want distinct milestones.

        # Solution: Use a persistent "stat" tracker in Influencer, or just read from the active objective state.
        # Let's add a helper in Manager to "increment" all objectives matching a pattern?
        # Or just read one known objective to get the current count.

        # Let's try to get the current value of the *first* logical objective like "influencer_replies_10".
        # Even if completed, it holds the current value (capped at target?).
        # Actually Objective state might be capped.

        # Let's simplify: We will rely on `mentions_module` state which DOES track `replies_today` but resets daily.
        # We want LIFETIME stats.

        # Let's create a specialized 'stat' objective or just use a helper here to store lifetime stats.
        # Or better: `update_objective` with `increment=True`? Manager doesn't support it yet.

        # Let's modify Manager to support `increment_objective(id_pattern, value=1)`.
        # But for now, without modifying core manager heavily:
        # We will fetch `influencer_replies_5000` (the largest one), get its current value, add 1, and update ALL.

        max_id = "influencer_replies_5000"
        current = manager.get_objective_value(max_id)  # Need this method
        new_val = current + 1

        self.set_replies_count(new_val)

    def set_replies_count(self, total: int):
        """Update all reply objectives with new total."""
        replies_milestones = [10, 50, 100, 500, 1000, 5000]
        for m in replies_milestones:
            manager.update_objective(f"influencer_replies_{m}", total)

    def set_tweets_count(self, total: int):
        """Update all tweet objectives."""
        tweets_milestones = [10, 50, 100, 300]
        for m in tweets_milestones:
            manager.update_objective(f"influencer_tweets_{m}", total)


# Singleton
influencer_gamification = InfluencerGamification()
