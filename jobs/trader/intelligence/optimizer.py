"""
JOBS/TRADER/INTELLIGENCE/OPTIMIZER.PY
==============================================================================
MODULE: STRATEGY OPTIMIZER (AI Feature) 🧠
PURPOSE: Global strategy optimization via backtesting.
         Compares Mitraillette vs Sniper, proposes mode switches.
==============================================================================
"""

import asyncio
import time
from typing import Dict, List, Optional
from loguru import logger

from jobs.trader.config import (
    MITRAILLETTE_RANGES,
    SNIPER_RANGES,
    TraderConfig,
    MEMORIES_DIR,
    F13,
    F55,
    DEEP_HISTORY,
    SCAN_TOP_X,
)


class OptimizerService:
    """
    Global Market Optimizer - PHI-Based Strategy Tuning.

    Features:
    - Analyzes ALL scanned pairs (not just owned)
    - Tests BOTH modes × 3 variations = 6 strategies
    - Proposes mode switch with detailed justification
    - Uses pure mathematics, AI validates with context
    - Runs every F233 (233 min ~4h) globally
    """

    def __init__(self):
        self._params_cache: Dict[str, dict] = {}
        self._last_optimization: float = 0
        self._cooldown = F55 * 60  # 55 minutes (More frequent)
        self._current_mode: str = "mitraillette"
        self._current_variation: str = "DEFAULT"
        self._last_results: Dict = {}
        self._history: List[Dict] = []

    def get_params(self, pair: str) -> dict:
        """Get cached optimized params for a pair."""
        return self._params_cache.get(pair, {})

    def get_ranges(self, mode: str) -> dict:
        """Get PHI ranges for mode."""
        return SNIPER_RANGES if mode == "sniper" else MITRAILLETTE_RANGES

    async def run_global_optimization(
        self, pairs: List[str], current_mode: str = "mitraillette"
    ) -> Dict:
        """
        Global optimization across all pairs.

        Process:
        1. Get all scanned pairs
        2. Backtest 6 strategies (2 modes × 3 variations)
        3. Calculate global PnL for each
        4. Propose to AI with detailed stats
        """

        now = time.time()

        # Cooldown check
        if now - self._last_optimization < self._cooldown:
            remaining = int((self._cooldown - (now - self._last_optimization)) / 60)
            logger.debug(f"🧠 [OPT] Cooldown: {remaining} min remaining")
            return {}

        self._last_optimization = now
        logger.info(
            f"🧠 [OPT] ═══ CYCLE START ═══ | {len(pairs)} pairs | Current: {current_mode}"
        )

        # SOTA v5.4: Auto-fetch pairs if list is empty (Self-Healing)
        if len(pairs) < 10:
            logger.warning(
                f"🧠 [OPT] Input pairs too low ({len(pairs)}). Auto-fetching valid pairs..."
            )
            try:
                # 1. Try to load from scan results (Market Pulse)
                from jobs.trader.data.pulse import MarketPulse

                pulse = MarketPulse()
                scanned = await pulse.get_top_market_pairs(limit=SCAN_TOP_X)
                pairs = [p["pair"] for p in scanned]
                logger.info(
                    f"🧠 [OPT] Auto-fetched {len(pairs)} pairs from MarketPulse"
                )
            except Exception:
                # 2. Fallback to hardcoded top assets if pulse fails
                pairs = [
                    "BTC/EUR",
                    "ETH/EUR",
                    "SOL/EUR",
                    "XRP/EUR",
                    "DOGE/EUR",
                    "ADA/EUR",
                    "DOT/EUR",
                    "LINK/EUR",
                    "LTC/EUR",
                    "MATIC/EUR",
                    "TRX/EUR",
                    "XLM/EUR",
                ]
                logger.warning(f"🧠 [OPT] Fallback to {len(pairs)} rigid pairs")

        if len(pairs) < 5:  # Lower threshold after fallback attempt
            logger.warning("🧠 [OPT] Still not enough pairs. Optimization aborted.")
            return {}

        # SOTA v5.5: Filter pairs that have data in Chronos
        from jobs.trader.data.history import create_history

        history = create_history()
        valid_pairs = []
        missing_pairs = []
        for pair in pairs:
            count = await history.count_candles(pair, "15m")
            if count >= 200:
                valid_pairs.append(pair)
            else:
                missing_pairs.append((pair, count))

        # Log diagnostic info (DEBUG: expected behavior for new/low-volume pairs)
        if missing_pairs:
            sample = missing_pairs[:5]  # Show first 5
            logger.debug(
                f"🧠 [OPT] Insufficient history: {[f'{p}({c})' for p, c in sample]}..."
            )

        if len(valid_pairs) < 5:
            # Get Chronos stats for debugging
            stats = history.get_stats()
            logger.warning(
                f"🧠 [OPT] Only {len(valid_pairs)} pairs with data. "
                f"Chronos has {stats['pairs']} pairs total. Need ≥5. Aborting."
            )
            return {}

        logger.info(f"🧠 [OPT] {len(valid_pairs)}/{len(pairs)} pairs have Chronos data")
        pairs = valid_pairs

        # Test all 6 variations
        all_results = {}
        variations = ["LOW", "DEFAULT", "HIGH"]

        for mode in ["mitraillette", "sniper"]:
            for variation in variations:
                key = f"{mode}_{variation}"
                logger.debug(f"[OPTIMIZER] Testing {key}...")

                results = await self._backtest_mode(mode, pairs, variation)

                if results:
                    avg_pnl = sum(r["pnl"] for r in results) / len(results)
                    total_trades = sum(r["trades"] for r in results)
                    avg_wr = sum(r["win_rate"] for r in results) / len(results)

                    all_results[key] = {
                        "mode": mode,
                        "variation": variation,
                        "pnl": avg_pnl,
                        "trades": total_trades,
                        "win_rate": avg_wr,
                        "pairs_tested": len(results),
                    }

        self._last_results = {
            "variations": all_results,
            "pairs_count": len(pairs),
            "timestamp": now,
        }

        if not all_results:
            return {}

        # Rank by PnL
        ranked = sorted(all_results.items(), key=lambda x: x[1]["pnl"], reverse=True)
        best_key, best = ranked[0]
        current_key = f"{current_mode}_{self._current_variation}"
        current_data = all_results.get(current_key, best)

        improvement = best["pnl"] - current_data["pnl"]

        # Log results
        logger.info("🧠 Optimization results:")
        for i, (key, data) in enumerate(ranked):
            marker = "👑" if i == 0 else "  "
            curr = " (CURRENT)" if key == current_key else ""
            logger.info(
                f"{marker} #{i + 1} {key}: {data['pnl']:+.2f}% | {data['win_rate']:.0f}% WR{curr}"
            )

        # Need >3% improvement to switch
        if improvement <= 3.0 or best_key == current_key:
            logger.info(
                f"🧠 [OPT] ✅ OPTIMAL | Mode: {current_key} | Δ potentiel: {improvement:+.2f}% (seuil: >3%)"
            )
            logger.info("🧠 [OPT] → Pas d'appel IA nécessaire (mode déjà optimal)")
            logger.info(
                f"🧠 [OPT] ═══ CYCLE END ═══ | Status: optimal | Mode: {current_mode}"
            )
            return {"mode": current_mode, "status": "optimal"}

        # Propose to AI
        config = TraderConfig.load()
        # SOTA v5.8: Force AI Optimization if in 'ia' mode OR if explicit switch is ON
        should_optimize = (config.mode == "ia") or config.ai_enabled

        if should_optimize:
            logger.info(
                f"🧠 [OPT] 📡 CONSULTING AI | {current_key} → {best_key} | Δ={improvement:+.2f}%"
            )
            decision = await self._ask_ai_approval(
                current_key, best_key, improvement, all_results
            )
            logger.info(f"🧠 [OPT] 🤖 AI DECISION: {decision}")
            if decision == "SWITCH":
                self._current_mode = best["mode"]
                self._current_variation = best["variation"]
                self._history.append(
                    {
                        "timestamp": now,
                        "from": current_key,
                        "to": best_key,
                        "improvement": improvement,
                    }
                )
                logger.success(f"🧠 [OPT] SWITCHED: {current_key} → {best_key}")
                logger.info(
                    f"🧠 [OPT] ═══ CYCLE END ═══ | Status: switched | Mode: {best['mode']}"
                )
                return {
                    "mode": best["mode"],
                    "status": "switched",
                    "improvement": improvement,
                }

        logger.info("🧠 [OPT] 🤖 AI refused switch (KEEP)")
        logger.info(f"🧠 [OPT] ═══ CYCLE END ═══ | Status: kept | Mode: {current_mode}")
        return {"mode": current_mode, "status": "kept"}

    async def _backtest_mode(
        self, mode: str, pairs: List[str], variation: str = "DEFAULT"
    ) -> List[Dict]:
        """Backtest a mode across multiple pairs."""
        from jobs.trader.intelligence.backtester import create_backtester
        from jobs.trader.data.history import create_history
        from jobs.trader.strategy.signals import Signal

        logger.info(f"🧠 [OPT] Backtesting {mode}_{variation} on {len(pairs)} pairs...")
        history = create_history()
        backtester = create_backtester()
        ranges = self.get_ranges(mode)
        results = []

        var_idx = {"LOW": 0, "DEFAULT": 1, "HIGH": 2}.get(variation, 1)

        async def backtest_single(pair: str) -> Optional[Dict]:
            try:
                df = await history.get_candles(pair, "15m", limit=DEEP_HISTORY)
                if df.height < 200:
                    return None

                params = {
                    "rsi_oversold": ranges["rsi_oversold"][var_idx],
                    "stop_loss": ranges["stop_loss"][var_idx],
                    "tp1": ranges["tp1"][var_idx],
                }

                async def test_strategy(test_df):
                    if test_df.height < 55:
                        return Signal.hold(pair, "Not enough data", 0)

                    closes = test_df["close"].to_list()
                    if len(closes) > 14:
                        changes = [closes[i] - closes[i - 1] for i in range(-14, 0)]
                        gains = sum(c for c in changes if c > 0)
                        losses = abs(sum(c for c in changes if c < 0))
                        rs = gains / losses if losses > 0 else 100
                        rsi = 100 - (100 / (1 + rs))
                    else:
                        rsi = 50

                    if rsi < params["rsi_oversold"]:
                        price = closes[-1]
                        sl = price * (1 - params["stop_loss"])
                        tp = price * (1 + params["tp1"])
                        return Signal.buy(pair, price, f"RSI={rsi:.1f}", 70, sl, tp)
                    return Signal.hold(pair, "RSI too high", closes[-1])

                result = await backtester.run(
                    df,
                    test_strategy,
                    stop_loss_pct=params["stop_loss"] * 100,
                    take_profit_pct=params["tp1"] * 100,
                )
                return {
                    "pair": pair,
                    "pnl": result.total_pnl_pct,
                    "trades": result.total_trades,
                    "win_rate": result.win_rate,
                }
            except Exception as e:
                logger.warning(f"🧠 [OPT] Backtest failed {pair}: {e}")
                return None

        # Process in batches with progress logging
        total_batches = (len(pairs) + F13 - 1) // F13
        for batch_idx, i in enumerate(range(0, len(pairs), F13)):
            batch = pairs[i : i + F13]
            logger.debug(f"🧠 [OPT] Batch {batch_idx + 1}/{total_batches}...")
            batch_results = await asyncio.gather(*[backtest_single(p) for p in batch])
            results.extend([r for r in batch_results if r])

        logger.info(f"🧠 [OPT] {mode}_{variation} → {len(results)} valid results")
        return results

    async def _ask_ai_approval(
        self, current: str, best: str, improvement: float, results: Dict
    ) -> str:
        """Ask AI to approve mode switch with detailed analysis."""
        try:
            from corpus.brain.gattaca import gattaca
            from corpus.soma.cells import load_json, save_json

            # Get detailed stats for AI analysis
            current_data = results.get(current, {})
            best_data = results.get(best, {})
            worst_key = min(results.keys(), key=lambda k: results[k].get("pnl", 0))
            worst_data = results.get(worst_key, {})

            # Build results table
            ranked = sorted(
                results.items(), key=lambda x: x[1].get("pnl", 0), reverse=True
            )
            results_table = "\n".join(
                [
                    f"#{i + 1} {key}: {data.get('pnl', 0):+.2f}% PnL | {data.get('trades', 0)} trades | {data.get('win_rate', 0):.0f}% WR"
                    for i, (key, data) in enumerate(ranked)
                ]
            )

            # Calculate spread and consistency metrics
            pnl_spread = best_data.get("pnl", 0) - worst_data.get("pnl", 0)
            wr_diff = best_data.get("win_rate", 0) - current_data.get("win_rate", 0)
            trades_ratio = best_data.get("trades", 1) / max(
                current_data.get("trades", 1), 1
            )

            prompt = f"""🧠 STRATEGY OPTIMIZATION ANALYSIS - Expert Decision Required

═══════════════════════════════════════════════════════════════
📊 BACKTEST SUMMARY
═══════════════════════════════════════════════════════════════
• Pairs Tested: {best_data.get("pairs_tested", 0)} cryptocurrencies
• Data Depth: ~1 year of 15-minute candles (Deep Historical)
• Strategies Tested: 6 (2 modes × 3 RSI/SL variations)

═══════════════════════════════════════════════════════════════
🏆 COMPLETE RANKING (sorted by PnL)
═══════════════════════════════════════════════════════════════
{results_table}

═══════════════════════════════════════════════════════════════
📈 DETAILED COMPARISON
═══════════════════════════════════════════════════════════════

▸ CURRENT STRATEGY: {current}
  • PnL: {current_data.get("pnl", 0):+.2f}%
  • Volume: {current_data.get("trades", 0)} trades exécutés
  • Win Rate: {current_data.get("win_rate", 0):.1f}%

▸ CHALLENGER (BEST): {best}
  • PnL: {best_data.get("pnl", 0):+.2f}%
  • Volume: {best_data.get("trades", 0)} trades exécutés
  • Win Rate: {best_data.get("win_rate", 0):.1f}%

▸ WORST PERFORMER: {worst_key}
  • PnL: {worst_data.get("pnl", 0):+.2f}%

═══════════════════════════════════════════════════════════════
🔬 ANALYSIS METRICS
═══════════════════════════════════════════════════════════════
• Improvement potentiel: +{improvement:.2f}%
• Delta Win Rate: {wr_diff:+.1f}%
• Spread PnL (best-worst): {pnl_spread:.2f}%
• Ratio Trades (best/current): {trades_ratio:.2f}x

═══════════════════════════════════════════════════════════════
🧠 DECISION CRITERIA
═══════════════════════════════════════════════════════════════
Évalue ces points avec rigueur:

1. CONSISTANCE: Le challenger a-t-il un Win Rate >= current?
   Si WR baisse significativement (>5%), c'est un red flag.

2. SIGNIFIANCE: +{improvement:.2f}% justifie-t-il un changement?
   Seuil recommandé: >3% pour justifier le risque de transition.

3. LOGIQUE MARCHÉ: Le mode {best_data.get("mode", "unknown").upper()} est-il adapté?
   • SNIPER = Marchés volatils, swings longs, patience.
   • MITRAILLETTE = Marchés calmes, scalping rapide, volume.

4. RISQUE DE SURFIT: Les résultats sont-ils trop beaux?
   Un PnL >50% avec peu de trades peut indiquer un overfit.

═══════════════════════════════════════════════════════════════
📝 TON VERDICT
═══════════════════════════════════════════════════════════════
Réponds avec:
• "SWITCH" pour approuver le changement vers {best}
• "KEEP" pour conserver {current}

Justifie ta décision en 2-3 phrases maximum.
Prends en compte le risk/reward et la cohérence des métriques."""

            # ROUTE 1 = Gemini Pro (Genius) - We're not in a hurry, quality matters
            # SOTA: Explicit F233 (233s) timeout for Route 1 (Pro is slower)
            response = await asyncio.wait_for(
                gattaca.think(prompt, route_id=1),
                timeout=233,
            )

            # ALWAYS save optimization results (for mode "ia" to read)
            import time

            config_path = MEMORIES_DIR / "trader" / "active_config.json"
            config = load_json(config_path, default={})

            # Always update recommended (even if not switching)
            config["recommended_mode"] = best_data.get("mode", "mitraillette")
            config["recommended_variation"] = best_data.get("variation", "DEFAULT")
            config["last_optimization"] = time.time()
            config["optimization_results"] = {
                k: {
                    "pnl": v.get("pnl", 0),
                    "wr": v.get("win_rate", 0),
                    "trades": v.get("trades", 0),
                }
                for k, v in results.items()
            }
            config["ai_analysis"] = response[:500]
            logger.info(
                f"🧠 [OPT] 📝 AI Reasoning: {response[:200].replace(chr(10), ' ')}..."
            )

            if "SWITCH" in response.upper():
                config["active_mode"] = best_data.get("mode", "mitraillette")
                config["active_variation"] = best_data.get("variation", "DEFAULT")
                config["last_mode_switch"] = time.time()
                config["mode_switch_reason"] = (
                    f"Backtested +{improvement:.1f}% improvement"
                )
            elif "active_mode" not in config:
                # Initialize active_mode from current (e.g. "sniper_DEFAULT" -> "sniper")
                config["active_mode"] = (
                    current.split("_")[0] if "_" in current else "mitraillette"
                )
                config["active_variation"] = (
                    current.split("_")[1] if "_" in current else "DEFAULT"
                )

            save_json(config_path, config)

            # SOTA v5.7: Sync Panel (trader.json) with AI Decision
            if "SWITCH" in response.upper():
                new_variation = best_data.get("variation", "DEFAULT")
                new_level = {"LOW": 0, "DEFAULT": 1, "HIGH": 2}.get(new_variation, 1)

                try:
                    trader_conf = TraderConfig.load()
                    # Only update if we are indeed in AI mode to avoid overriding Manual user lock
                    if trader_conf.mode == "ia" and not trader_conf.ai_lock_level:
                        if trader_conf.level != new_level:
                            logger.info(
                                f"🧠 [OPT] Syncing Panel Level: {trader_conf.level} -> {new_level}"
                            )
                            trader_conf.level = new_level
                            trader_conf.save()
                except Exception as e:
                    logger.error(f"🧠 [OPT] Failed to sync panel: {e}")

            if "SWITCH" in response.upper():
                # Add to history
                self._history.append(
                    {
                        "timestamp": time.time(),
                        "from": current,
                        "to": best,
                        "improvement": improvement,
                        "ai_response": response[:200],
                    }
                )

                # SOTA 2026: Send Mutation Notification (Standard 362.102)
                try:
                    trader_conf = TraderConfig.load()
                    if trader_conf.notify_mutations:
                        from social.messaging.notification_client import notify

                        # Parse OLD mode and level for display
                        old_mode = (
                            current.split("_")[0].upper()
                            if "_" in current
                            else "MITRAILLETTE"
                        )
                        old_variation = (
                            current.split("_")[1] if "_" in current else "DEFAULT"
                        )
                        old_level_display = {
                            "LOW": "PASSIF",
                            "DEFAULT": "NORMAL",
                            "HIGH": "AGRESSIF",
                        }.get(old_variation, "NORMAL")
                        old_mode_icon = "🎯" if old_mode == "SNIPER" else "⚡"

                        # Parse NEW mode and level for display
                        new_mode = best_data.get("mode", "mitraillette").upper()
                        new_variation = best_data.get("variation", "DEFAULT")
                        level_display = {
                            "LOW": "PASSIF",
                            "DEFAULT": "NORMAL",
                            "HIGH": "AGRESSIF",
                        }.get(new_variation, "NORMAL")
                        mode_icon = "🎯" if new_mode == "SNIPER" else "⚡"
                        level_icon = {
                            "PASSIF": "🛡️",
                            "NORMAL": "⚖️",
                            "AGRESSIF": "🔥",
                        }.get(level_display, "⚖️")

                        await notify.trader(
                            message=f"🧠 IA → {mode_icon} {new_mode} {level_icon} {level_display}",
                            title="🔄 MUTATION STRATÉGIE",
                            body=f"<div class='report'>"
                            f"<div class='report-section'>"
                            f"<div class='report-section-title'>🔄 Changement de Stratégie</div>"
                            f"<div class='report-row'><span class='label'>Avant </span><span class='value'>{old_mode_icon} {old_mode} ({old_level_display})</span></div>"
                            f"<div class='report-row'><span class='label'>Après </span><span class='value'>{mode_icon} {new_mode} ({level_display})</span></div>"
                            f"<div class='report-row'><span class='label'>Amélioration </span><span class='value positive'>+{improvement:.2f}%</span></div>"
                            f"</div></div>",
                            dedup_key="TRADER_MUTATION",
                        )
                        logger.info("📤 [OPT] Mutation notification sent")
                except Exception as e:
                    logger.debug(f"🧠 [OPT] Mutation notify failed: {e}")

                return "SWITCH"

            return "KEEP"
        except Exception as e:
            logger.error(f"🧠 [OPT] ❌ AI CALL FAILED: {e}")
            return "KEEP"

    def optimize_rsi(self, pair: str, mode: str = "mitraillette") -> None:
        """Legacy method - triggers global optimization if cooldown passed."""
        import asyncio

        asyncio.create_task(self.run_global_optimization([], mode))


def create_optimizer() -> OptimizerService:
    """Factory function to create OptimizerService."""
    return OptimizerService()
