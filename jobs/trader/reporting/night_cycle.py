"""
JOBS/TRADER/REPORTING/NIGHT_CYCLE.PY
==============================================================================
MODULE: NIGHT CYCLE (Dreaming & Self-Improvement) 🌙
PURPOSE: Nightly self-reflection for continuous optimization.
         - Daily performance analysis
         - AI-generated improvement suggestions
         - Morning report generation
==============================================================================
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
from loguru import logger

from jobs.trader.config import MEMORIES_DIR, JOBS_DIR, TraderConfig


REPORT_FILE = MEMORIES_DIR / "trader" / "latest_report.md"
SUGGESTIONS_FILE = MEMORIES_DIR / "trader" / "suggestions.json"


class NightCycle:
    """
    Nightly self-improvement cycle.

    Features:
    - Runs at 03:00 for analysis and optimization
    - AI-generated improvement suggestions
    - Morning report preparation
    - Suggestion management (approve/reject)
    """

    def __init__(self):
        self._suggestions: List[Dict] = self._load_suggestions()

    def _load_suggestions(self) -> List[Dict]:
        """Load saved suggestions."""
        try:
            if SUGGESTIONS_FILE.exists():
                with open(SUGGESTIONS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_suggestions(self) -> None:
        """Save suggestions."""
        try:
            SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._suggestions, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[NIGHT] Save suggestions failed: {e}")

    async def run_night_procedure(
        self, performance: Dict, trades: List[Dict] = None
    ) -> None:
        """
        Run nightly procedure (Self-Reflection) at 03:00.

        Args:
            performance: Daily performance stats
            trades: List of recent trades
        """
        from jobs.trader.reporting.gamification import create_gamification
        from jobs.trader.reporting.hall_of_fame import create_hall_of_fame

        logger.info("🌙 [NIGHT] Entering Sleep Mode for Self-Optimization...")

        gamification = create_gamification()
        hall_of_fame = create_hall_of_fame()

        # 1. Check gamification milestones
        gamification.check_milestones(performance.get("total_profit", 0))

        # 2. Add best trade to Hall of Fame
        if trades:
            best_trade = max(trades, key=lambda t: t.get("pnl_eur", 0), default=None)
            if best_trade and best_trade.get("pnl_eur", 0) > 10:
                hall_of_fame.add_best_trade(
                    pair=best_trade.get("pair", "UNKNOWN"),
                    pnl_eur=best_trade.get("pnl_eur", 0),
                    pnl_pct=best_trade.get("pnl_pct", 0),
                    context=best_trade,
                )

        # 3. AI Analysis for optimization suggestions
        config = TraderConfig.load()
        if config.ai_enabled:
            codebase = self._scan_codebase_structure()
            new_suggestions = await self._dream_about_optimization(
                trades or [], codebase
            )

            for s in new_suggestions:
                s["id"] = (
                    f"SUGG_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._suggestions)}"
                )
                s["status"] = "pending"
                s["created"] = datetime.now().isoformat()
                self._suggestions.append(s)
                logger.debug(f"[DREAM] New Idea: {s.get('description', '')[:50]}")

        # 4. Backtest yesterday's strategy
        try:
            from jobs.trader.intelligence.backtester import create_backtester
            from jobs.trader.strategy.brain import create_brain

            yesterday_df = performance.get("yesterday_df")
            if (
                yesterday_df is not None
                and hasattr(yesterday_df, "height")
                and yesterday_df.height > 100
            ):
                backtester = create_backtester()
                brain = create_brain(config)
                backtest_result = await backtester.run(yesterday_df, brain.decide)

                if backtest_result.win_rate < 50:
                    self._suggestions.append(
                        {
                            "id": f"SUGG_BACKTEST_{datetime.now().strftime('%Y%m%d')}",
                            "type": "ALERT",
                            "description": f"Win rate dropped to {backtest_result.win_rate:.1f}% - review strategy",
                            "status": "pending",
                            "created": datetime.now().isoformat(),
                        }
                    )
                    logger.warning(
                        f"⚠️ [NIGHT] Backtest alert: {backtest_result.win_rate:.1f}% win rate"
                    )
                else:
                    logger.info(
                        f"✅ [NIGHT] Backtest: {backtest_result.win_rate:.1f}% win rate"
                    )
        except Exception as e:
            logger.debug(f"[NIGHT] Backtest skipped: {e}")

        self._save_suggestions()
        logger.success("☀️ [NIGHT] Awake & Optimized. Ideas Stored.")

    def prepare_morning_report(self) -> str:
        """
        Prepare morning report (05:00).

        Returns:
            Markdown report content
        """
        from jobs.trader.reporting.gamification import create_gamification
        from jobs.trader.reporting.hall_of_fame import create_hall_of_fame

        logger.info("[MORNING] Preparing Trader Report...")

        gamification = create_gamification()
        hall_of_fame = create_hall_of_fame()

        # Clean old suggestions
        self._clean_old_suggestions()

        # Get pending suggestions
        pending = [s for s in self._suggestions if s.get("status") == "pending"][:3]

        # Build report
        report = f"""# 📊 Trader Morning Report
*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*

## 🎯 Optimization Suggestions

"""
        if not pending:
            report += "✅ **System Optimal** - No changes suggested.\n"
        else:
            for i, s in enumerate(pending, 1):
                icon = "⚙️" if s.get("type") == "PARAM_CHANGE" else "✨"
                report += f"**{i}. {icon} {s.get('type', 'SUGGESTION')}**\n"
                report += f"> {s.get('description', 'No description')}\n"
                report += f"> *ID: `{s.get('id')}`*\n\n"

        report += f"""
## 🏆 Hall of Fame Stats

{json.dumps(hall_of_fame.get_stats(), indent=2)}

## 🎮 Gamification

{json.dumps(gamification.get_stats(), indent=2)}
"""

        # Save report
        try:
            REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REPORT_FILE, "w", encoding="utf-8") as f:
                f.write(report)
            logger.success(f"[MORNING] Report saved: {REPORT_FILE}")
        except Exception as e:
            logger.error(f"[MORNING] Save failed: {e}")

        return report

    def _scan_codebase_structure(self) -> str:
        """Generate codebase mini-map for AI."""
        structure = "CODEBASE STRUCTURE (jobs/trader):\n"
        base_path = JOBS_DIR / "trader"

        if base_path.exists():
            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if d != "__pycache__"]

                level = str(root).replace(str(base_path), "").count(os.sep)
                indent = "  " * level
                structure += f"{indent}{Path(root).name}/\n"

                subindent = "  " * (level + 1)
                for f in files:
                    if f.endswith(".py"):
                        structure += f"{subindent}{f}\n"

        return structure

    async def _dream_about_optimization(
        self, trades: List[Dict], codebase: str
    ) -> List[Dict]:
        """Ask AI for improvement suggestions."""
        trades_summary = str(trades[-20:]) if trades else "No recent trades"

        prompt = f"""NOCTURNAL TRADER ANALYSIS (Self-Reflection):

RECENT TRADES:
{trades_summary[:1000]}

CODEBASE STRUCTURE:
{codebase[:1500]}

TASK:
Generate a JSON list of 1-3 optimization suggestions.
Types: "PARAM_CHANGE", "NEW_FUNCTION", "REFACTOR"

FORMAT (JSON only):
[
    {{"type": "PARAM_CHANGE", "description": "Lower RSI threshold to 25 for better entries"}}
]"""

        try:
            from corpus.brain.gattaca import gattaca
            import asyncio

            # SOTA: Explicit F233 (233s) timeout for Route 1 (Pro is slower)
            response = await asyncio.wait_for(
                gattaca.think(prompt, route_id=1),
                timeout=233,
            )

            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"[DREAM] AI analysis failed: {e}")

        return []

    def _clean_old_suggestions(self, days: int = 7) -> None:
        """Remove suggestions older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        self._suggestions = [
            s
            for s in self._suggestions
            if s.get("created", "9999") > cutoff or s.get("status") == "approved"
        ]
        self._save_suggestions()

    def approve_suggestion(self, suggestion_id: str) -> bool:
        """Approve a suggestion."""
        for s in self._suggestions:
            if s.get("id") == suggestion_id:
                s["status"] = "approved"
                s["approved_at"] = datetime.now().isoformat()
                self._save_suggestions()
                return True
        return False

    def reject_suggestion(self, suggestion_id: str) -> bool:
        """Reject a suggestion."""
        for s in self._suggestions:
            if s.get("id") == suggestion_id:
                s["status"] = "rejected"
                self._save_suggestions()
                return True
        return False

    def get_pending_suggestions(self) -> List[Dict]:
        """Get all pending suggestions."""
        return [s for s in self._suggestions if s.get("status") == "pending"]


def create_night_cycle() -> NightCycle:
    """Factory function to create NightCycle."""
    return NightCycle()
