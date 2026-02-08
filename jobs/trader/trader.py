"""
JOBS/TRADER/TRADER.PY
==============================================================================
MODULE: TRADING HEART v4.0 SOTA 🫀
PURPOSE: Complete orchestrator with all legacy intelligence restored.
TARGET: SOTA Orchestration (Circuit Breaker, Scheduler, Persistence)
==============================================================================
"""

import asyncio
import schedule
from datetime import datetime
from typing import Optional, Dict, List
from corpus.soma.nerves import logger  # SOTA: Use central nerves config (DEBUG level)

from jobs.trader.config import (
    TraderConfig,
    PHI,
    F18,
    F34,
    F89,
    MEMORIES_DIR,
    FORBIDDEN_SELL_ASSETS,
    CAGNOTTE_BTC_THRESHOLD,
    BTC_SACRED_PAIR,
    SCAN_TOP_X,
)
from jobs.trader.kraken.exchange import (
    KrakenExchange,
    create_exchange,
    cancel_stale_orders,
)
from jobs.trader.kraken.api import KrakenAPI, create_api
from jobs.trader.strategy.brain import TradingBrain, create_brain
from jobs.trader.strategy.signals import Signal
from jobs.trader.execution.positions import PositionManager, create_position_manager
from jobs.trader.execution.scanner import MarketScanner, create_scanner
from jobs.trader.intelligence.optimizer import OptimizerService, create_optimizer
from jobs.trader.intelligence.portfolio import (
    PortfolioManager,
    create_portfolio_manager,
)
from jobs.trader.reporting.night_cycle import NightCycle, create_night_cycle
from jobs.trader.data.pulse import MarketPulse, create_pulse
from jobs.trader.data.history import Chronos, create_history, initialize_deep_history
from jobs.trader.data.feed import KrakenFeed, create_feed
from jobs.trader.intelligence.quantum import quantum  # ⚛️ QRP Logic
from jobs.trader.intelligence.memory import (
    GoldenMemory,
    create_memory,
)  # 🧠 Pattern Memory
from social.messaging.notification_templates import (
    render_trade_notification as render_rich_trade,
    render_sacred_acquisition,
    TradeData,
    TradeSide,
)

# SAFE IMPORTS (Degraded Mode Support)
from jobs.trader.utils import atomic_save_json

# SOTA 2026: Using notify client for notifications


try:
    from corpus.soma.cells import load_json, save_json
    from corpus.soma.nerves import nerves
    from corpus.brain.circadian import circadian
except ImportError:
    import json

    def load_json(path, default=None):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return default

    def save_json(path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=4)

    class MockNerves:
        def fire(self, *args, **kwargs):
            pass

    nerves = MockNerves()

    class MockCircadian:
        def get_current_energy(self):
            return 1.0

    circadian = MockCircadian()
    logger.warning("⚠️ Corpus Degraded")

from jobs.trader.reporting.gamification import create_gamification
from jobs.trader.strategy.ai import ask_for_strategy_switch

# SOTA 2026: Dual-Channel Notifications (Phone Widget + Android FCM)
try:
    from social.messaging.notification_client import notify
except ImportError:
    notify = None
    logger.warning("⚠️ Notification Client Degraded")


STATE_FILE = MEMORIES_DIR / "trader" / "state.json"


class TradingHeart:
    """
    Trading Heart v4.0 - Minimal Orchestrator.

    All business logic is delegated to specialized modules:
    - Exchange: kraken/exchange.py
    - API: kraken/api.py (Earn, Logic)
    - Analysis: data/indicators.py
    - Decisions: strategy/brain.py
    - Execution: execution/positions.py
    - Intelligence: intelligence/optimizer.py & portfolio.py
    - Dreaming: reporting/night_cycle.py
    """

    def __init__(self, config: TraderConfig = None):
        """
        Initialize TradingHeart.

        Args:
            config: Runtime config (loads from trader.json if not provided)
        """
        self.config = config or TraderConfig.load()

        # Components (factory pattern - no singletons)
        self.exchange: KrakenExchange = create_exchange()
        self.feed: KrakenFeed = create_feed()
        self.api: KrakenAPI = create_api(self.exchange)
        self.brain: TradingBrain = create_brain(self.config)
        self.positions: PositionManager = create_position_manager()
        self.scanner: MarketScanner = create_scanner()
        self.optimizer: OptimizerService = create_optimizer()
        self.portfolio: PortfolioManager = create_portfolio_manager()
        self.night_cycle: NightCycle = create_night_cycle()
        self.gamification = create_gamification()
        # RESTORED: Critical Intelligence Modules
        self.pulse: MarketPulse = create_pulse()
        self.history: Chronos = create_history()
        self.golden_memory: GoldenMemory = create_memory()  # 🧠 Pattern Memory

        # State
        self.running: bool = False
        self.paused: bool = self.config.paused
        self.cycle_count: int = 0
        self._last_staked_hour = -1
        self._last_staked_hour = -1
        self._started_at: Optional[datetime] = None

        # Trade Buffering
        self._trade_buffer: List[Dict] = []
        self._buffer_lock = asyncio.Lock()

        # SOTA: Patrol Mode Offset (Round Robin)
        self._scan_offset: int = 0

        # SOTA v5.0: Event-Driven Architecture
        self._analysis_queue = asyncio.Queue()
        self._last_analysis_price: Dict[str, float] = {}
        self.MIN_VARIATION = 0.001  # 0.1% trigger

        # SOTA v5.9: Quantum Sniper Override state
        self._quantum_sniper_active: bool = False
        self._quantum_sniper_direction: str = ""  # BULLISH/BEARISH

        # SOTA 2026: Cached report for Web API (avoids Kraken lock contention)
        self._cached_report: Dict = {"sync_status": "BOOTING"}
        self._load_hot_start_cache()

    # ═══════════════════════════════════════════════════════════════════════════
    # DUAL-CHANNEL NOTIFICATIONS (Standard 362)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _notify(
        self,
        message: str,
        actions: list = None,
        phone_only: bool = False,
        body: str = None,
        title: str = None,
        dedup_key: str = None,
    ) -> None:
        """
        Send notification to Phone Widget + Android FCM (Standard 362.18 SOTA 2026).

        Args:
            message: Full message (will be stripped for Phone)
            actions: Optional action buttons for phone widget [{"id": str, "label": str, "type": str}]
            phone_only: If True, only notify phone (skip other channels)
            body: Optional rich HTML body for Phone Widget (glassmorphism cards)
            title: Optional notification title
            dedup_key: Optional. If provided, replaces any existing notification with same key
        """
        # SOTA 2026: Phone Widget is the primary notification channel

        # 2. Send to Phone Widget - FULL CONTENT (Standard 362.18)
        if not phone_only and notify:
            try:
                import re

                # Strip HTML for Phone Widget display, but keep FULL content
                clean_msg = re.sub(r"<[^>]+>", "", message)

                await notify.send(
                    source="TRADER",
                    message=clean_msg,
                    actions=actions or [],
                    body=body,  # Rich HTML for Phone Widget
                    title=title,  # Custom title
                    dedup_key=dedup_key,  # SOTA 2026: Deduplication
                )
            except Exception as e:
                logger.debug(f"Phone notify failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    async def start(self) -> None:
        """Start the trading engine (HARDENED: retry + abort)."""
        self.running = True
        self._started_at = datetime.now()
        logger.info("🏎️ Heart Starting")

        # Immediate cache update moved to after connection to fix Race Condition
        # asyncio.create_task(self._refresh_cache())

        # Register with API for UI access
        try:
            from jobs.trader.api import set_trader_instance

            set_trader_instance(self)
        except Exception as e:
            logger.warning(f"⚠️ API Skip: {e}")

        try:
            # 0. Restore cycle count from previous session
            self._restore_cycle_count()

            # 1. Connect Exchange (with Fibonacci retry)
            logger.debug("[HEART] Connecting Exchange...")
            if not await self._connect_with_retry(self.exchange.connect, "EXCHANGE"):
                logger.critical("❌ Exchange Failed")
                nerves.fire("CRITICAL", "STARTUP_ABORT", "Exchange connection failed")
                self.running = False
                return
            logger.success("✅ Exchange Ready")

            # SOTA 2026: Defer cache refresh to avoid race condition with sync_positions
            # Both _refresh_cache() and sync_positions_from_kraken() call fetch_all_balances()
            # Concurrent calls cause aiohttp/TCP deadlock. Cache will be refreshed after sync.
            # asyncio.create_task(self._refresh_cache())

            # 2. Sync Portfolio with Kraken (with timeout to prevent startup hang)
            logger.debug("[HEART] Syncing portfolio...")
            try:
                await asyncio.wait_for(
                    self.positions.sync_positions_from_kraken(self.exchange, self.api),
                    timeout=30.0,  # Reasonable timeout for Kraken API
                )
                logger.success("✅ Portfolio Synced")
            except asyncio.TimeoutError:
                logger.warning(
                    "⚠️ Sync Timeout - continuing without full portfolio sync"
                )
            except Exception as e:
                logger.warning(f"⚠️ Sync Failed: {e}")

            # 3. Connect WebSocket Feed
            logger.debug("[HEART] Connecting WebSocket...")
            await self.feed.connect()
            self.feed.enable_trade_feed(True, self._on_trade_received)
            self.feed.on_price_update(self._on_price_update)

            # Start Event Processor
            self._safe_create_task(self._process_analysis_queue(), "EVENT_PROCESSOR")

            # 4. Warm Start: Subscribe to Active Positions
            active_pairs = list(self.positions.positions.keys())
            if active_pairs:
                logger.debug(
                    f"[HEART] Subscribing to {len(active_pairs)} active positions"
                )
                self._safe_create_task(
                    self.feed.subscribe_progressive(active_pairs), "FEED_POSITIONS"
                )

            # 5. Pre-warm Market Feed
            logger.debug("[HEART] Pre-warming market feed...")
            # On peut récupérer une liste statique ou laisser le scanner le faire au premier run
            # Le mieux est de laisser le feed s'initialiser, mais on peut forcer un fetch_tickers rapide pour extraire les paires
            try:
                tickers = await self.exchange.fetch_tickers()
                # Filtrer les paires EUR et prendre le top 144 par volume
                top_pairs = [
                    pair
                    for pair, data in sorted(
                        tickers.items(),
                        key=lambda x: x[1]["quoteVolume"]
                        if "quoteVolume" in x[1]
                        else 0,
                        reverse=True,
                    )
                    if "/EUR" in pair and "USD" not in pair
                ][:144]  # F12

                self._safe_create_task(
                    self.feed.subscribe_progressive(top_pairs), "FEED_WARMUP"
                )
            except Exception:
                # FALLBACK ROBUSTE : Si le fetch dynamique échoue (ex: Assets endpoint bloqué), on utilise une liste statique
                # Cela permet de garantir que le WebSocket démarre même si l'API REST tousse.
                logger.info("ℹ️ Warmup Fallback")
                fallback_pairs = [
                    "BTC/EUR",
                    "ETH/EUR",
                    "SOL/EUR",
                    "XRP/EUR",
                    "ADA/EUR",
                    "DOGE/EUR",
                    "DOT/EUR",
                ]
                self._safe_create_task(
                    self.feed.subscribe_progressive(fallback_pairs),
                    "FEED_WARMUP_FALLBACK",
                )

            # 3. Schedule Reports
            self._schedule_reports()

            # 4. Send Startup Notification
            await self._send_startup_notification()

            # 5. SOTA: Initial Optimization Run (Don't wait for F55 cycles)
            if self.config.mode == "ia":
                self._safe_create_task(self._run_initial_optimization(), "INITIAL_OPT")

            # Main Loop
            await self._run_loop()

        except asyncio.CancelledError:
            logger.info("🫀 Shutdown")
        except Exception as e:
            logger.error(f"🫀 Fatal: {e}")
            self.running = False
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the trading engine."""
        self.running = False

        # Flush buffer (with timeout to prevent hang)
        try:
            await asyncio.wait_for(self._flush_trade_buffer(), timeout=5.0)
        except Exception as e:
            logger.warning(f"🫀 Flush Timeout: {e}")

        # Components Close (Safe)
        try:
            await self.exchange.close()
        except Exception:
            pass

        try:
            await self.feed.close()
        except Exception:
            pass

        if self.history:
            try:
                self.history.close()
            except Exception:
                pass

        # Unregister from API
        try:
            from jobs.trader.api import clear_trader_instance

            clear_trader_instance()
        except Exception:
            pass

        logger.info("🫀 Stopped")

    def pause(self) -> None:
        """Pause trading (still monitors positions)."""
        self.paused = True
        self.config.paused = True
        self.config.save()
        logger.info("🫀 Paused")

    def resume(self) -> None:
        """Resume trading."""
        self.paused = False
        self.config.paused = False
        self.config.save()
        logger.info("🫀 Resumed")

    def reload_config(self, new_config: TraderConfig) -> None:
        """Hot-reload configuration."""
        self.config = new_config
        self.paused = self.config.paused
        # SOTA v5.9: Sync brain config to ensure level changes take effect
        if hasattr(self, "brain") and self.brain:
            self.brain.config = new_config
            self.brain._config_cache.clear()  # Force re-read of dynamic configs
            logger.debug(f"🧠 Brain config synced: level={new_config.level}")
        # Re-schedule reports in case interval changed
        self._schedule_reports()
        logger.info("🫀 Config Hot-Reloaded")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    async def _calculate_organic_interval(self) -> float:
        """
        🫀 PHI-BEAT: Calcule le prochain battement de cœur.
        Formule : Base * φ^(1 - Stress)
        """
        # A. Récupération du Stress Marché (0.0 à 1.0)
        market_stress = 0.5
        if hasattr(self, "pulse") and self.pulse:
            # 50 = Calme. Écart type vers 0 ou 100 = Stress.
            deviation = abs(self.pulse.score - 50) * 2
            market_stress = deviation / 100.0

        # B. Énergie Circadienne (Trinity est-elle fatiguée ?)
        # Si énergie basse (nuit), on ralentit sauf si stress majeur
        energy = circadian.get_current_energy()

        # C. Calcul de l'intervalle de base
        # F34 (34s) est le standard Phi. F5 (5s) pour le mode Mitraillette.
        base = F34
        if self.config.mode == "mitraillette":
            base = 5.0

        # D. Dilatation Temporelle (La magie de Phi)
        # Si Stress = 1.0 (Panique) -> Facteur 0 -> Intervalle = Base
        # Si Stress = 0.0 (Zen) -> Facteur Phi -> Intervalle = Base * 2.618
        dilation_factor = PHI * (1.0 - market_stress)

        # Modulation finale : Si Trinity a beaucoup d'énergie, elle accélère un peu
        organic_interval = base * (1.0 + dilation_factor)
        if energy > 0.8:  # Pleine forme
            organic_interval *= 0.8  # +20% vitesse

        # Limite dure : Jamais moins de 1s
        return max(1.0, organic_interval)

    async def _run_loop(self) -> None:
        """Boucle Principale : Rythme Organique (Phi-Beat)."""
        logger.success("🫀 Phi-Beat Active")

        while self.running:
            start_time = datetime.now()

            try:
                # 1. SYSTOLE (Contraction / Travail)
                await self._work_cycle()
                self.cycle_count += 1

                # Maintenance
                schedule.run_pending()
                if self.cycle_count % 13 == 0:
                    self._persist_cycle_count()

            except Exception as e:
                logger.error(f"🫀 Arrhythmia: {e}")

            # 2. DIASTOLE (Relaxation / Attente Dynamique)
            # On calcule le temps de repos nécessaire MAINTENANT
            organic_wait = await self._calculate_organic_interval()

            # Compensation du temps de calcul (pour rester précis)
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = max(0.1, organic_wait - elapsed)

            # On dort (c'est ici que le rythme change à chaque cycle)
            await asyncio.sleep(sleep_time)

    async def _work_cycle(self) -> None:
        """Single work cycle with SOTA Orchestration."""
        now = datetime.now()

        # 0. Check Night Cycle (Dreaming) @ 03:00
        if now.hour == 3 and now.minute < 5:
            # Check if we should run (simplified idempotency)
            if now.minute == 0:
                try:
                    logger.info("🌙 Night Cycle")
                    stats = self.positions.get_today_stats()
                    trades = await self.api.fetch_trade_history(days=1)

                    # 1. Run Reflection
                    await self.night_cycle.run_night_procedure(stats, trades)

                    # 2. Run Global Optimization (AI)
                    # We use a broad list of pairs (e.g. from history or active config)
                    scan_list = getattr(self.scanner, "last_scan_result", [])
                    if len(scan_list) > 10:
                        pairs = [c[0] for c in scan_list]
                        await self.optimizer.run_global_optimization(pairs)

                    # 3. Send Morning Report (Dual-channel)
                    report = self.night_cycle.prepare_morning_report()
                    if report and getattr(self.config, "notify_reports", True):
                        await self._notify(report)  # Standard 362: Full content
                        logger.success("📤 Morning Sent")

                except Exception as e:
                    logger.error(f"🌙 Nightmare: {e}")

        # 1. Circuit Breaker & Auto-Recovery
        eur_balance = await self.exchange.fetch_balance("EUR")
        if not eur_balance:
            eur_balance = await self.exchange.fetch_balance("ZEUR")

        total_bal = eur_balance.get("total", 0) if eur_balance else 0
        current_capital = self._calculate_total_capital(total_bal)

        # Initial capital management (simple for now, could be persisted)
        if not hasattr(self, "_initial_capital_set"):
            self._initial_capital = current_capital
            self._initial_capital_set = True

        if getattr(self.config, "circuit_breaker_enabled", True):
            halt, reason = self.positions.check_circuit_breaker(
                current_capital, initial_capital=self._initial_capital
            )
        else:
            halt, reason = False, "DISABLED"

        if halt:
            logger.warning(f"🚨 Breaker: {reason}")

            # SOTA: Send notification ONCE when breaker activates (not every cycle)
            if not getattr(self, "_breaker_notified", False):
                self._breaker_notified = True
                if getattr(self.config, "notify_circuit_breaker", True):
                    try:
                        await self._notify(
                            f"🚨 <b>CIRCUIT BREAKER ACTIVÉ</b>\n"
                            f"Trading suspendu: {reason}\n"
                            f"<i>Récupération auto si BTC > -3%</i>",
                            title="🚨 TRADING STOPPÉ",
                        )
                    except Exception as e:
                        logger.debug(f"Breaker notification failed: {e}")

            # AUTO-RECOVERY Check
            # If we are halted, we check if BTC has stabilized/recovered
            btc_change = await self._get_btc_24h_change()
            if btc_change > -0.03:  # Recovered above -3%
                logger.success("🔄 Breaker Recovery")
                self.positions.reset_circuit_breaker()
                self._breaker_notified = False  # Reset for next activation
                halt = False
            else:
                # Still crashing, ensure we don't buy, but we MUST manage exits
                pass

        # 2. Update portfolio peak (for daily PnL tracking in Brain)
        self.brain.update_portfolio_peak(current_capital)

        # 3. Manage existing positions (ALWAYS run, even if halted)
        await self._manage_positions()

        # 4. Optimizer Cycle (SOTA: F55 ~ every 30min with 34s cycle)
        # Dynamic Mode Switching (ONLY if in IA Mode)
        if (
            self.cycle_count > 0
            and self.cycle_count % 55 == 0
            and self.config.mode == "ia"
        ):
            try:
                # SOTA: Use scan pairs (broader market view) OR active positions as fallback
                scan_pairs = getattr(self.scanner, "last_scan_result", [])
                optimization_pairs = (
                    [c[0] for c in scan_pairs[:50]]  # Top 50 from scan
                    if scan_pairs
                    else list(self.positions.positions.keys())  # Fallback
                )
                if optimization_pairs:
                    recommendation = await self.optimizer.run_global_optimization(
                        optimization_pairs
                    )

                    # 🚦 OPTIMIZER FEEDBACK LOOP (JULES FIX)
                    # We check if optimizer suggests a switch (status="switched")
                    should_switch = recommendation.get("status") == "switched"
                    new_mode = recommendation.get("mode")

                    if should_switch and new_mode:
                        # Double confirm with AI (Gatekeeper)
                        confirmed = await ask_for_strategy_switch(
                            self.config.mode,
                            new_mode,
                            f"Optimizer recommends switch (Improvement: {recommendation.get('improvement', 0):.2f}%)",
                        )

                        if confirmed:
                            old_mode = self.config.mode
                            self.config.mode = new_mode
                            self.config.save()

                            logger.success(f"🧠 Mutation: {old_mode}→{new_mode}")

                            # Notify
                            if getattr(self.config, "notify_mutations", True):
                                await self._notify(
                                    f"🧠 <b>MUTATION STRATÉGIQUE</b>\n"
                                    f"Passage du mode {old_mode.upper()} vers <b>{new_mode.upper()}</b>\n"
                                    f"<i>Optimisation global validée par l'IA.</i>",
                                )

            except Exception as e:
                logger.warning(f"🧠 Optimizer Fail: {e}")

        # 5. Scan & Trade (Only if active and not halted)
        if not self.paused and not halt:
            await self._scan_and_trade()

        # 6. Cagnotte Processing (Buy sacred BTC with gains)
        # Check every cycle (it has internal safeguards)
        await self._process_cagnotte()

        # 7. Cagnotte Staking (Every hour)
        if now.hour != self._last_staked_hour:
            try:
                btc_bal = await self.exchange.fetch_balance(
                    "BTC"
                ) or await self.exchange.fetch_balance("XBT")
                if btc_bal and btc_bal.get("free", 0) > 0.0001:
                    logger.info(f"🐷 Staking {btc_bal['free']:.6f} BTC")
                    await self.api.auto_stake_btc(btc_bal["free"])
                self._last_staked_hour = now.hour
            except Exception as e:
                logger.warning(f"🐷 Stake Fail: {e}")

    async def _manage_positions(self) -> None:
        """Check and manage all open positions (PARALLEL)."""
        # Launch all checks in parallel (SOTA: minimize slippage)
        tasks = [
            self._manage_single_position(pos)
            for pos in self.positions.get_open_positions()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _manage_single_position(self, pos) -> None:
        """Manage a single position (isolated logic)."""
        # 🛑 REDUNDANT SACRED GUARD 🛑
        # Ensure we NEVER process/sell sacred assets like BTC
        is_sacred = False
        for sacred in FORBIDDEN_SELL_ASSETS:
            if sacred in pos.pair:
                is_sacred = True
                break
        if is_sacred:
            return

        try:
            ticker = await self.exchange.fetch_ticker(pos.pair)
            current_price = ticker["last"]

            # Update position price
            self.positions.update_position(pos.pair, current_price)

            # Fetch min_cost for Dust Guard (Fail-Safe)
            min_cost = 5.0
            try:
                limits = await self.exchange.get_limits(pos.pair)
                min_cost = limits.get("min_cost", 5.0)
            except Exception:
                pass  # Default to 5.0 without crashing the cycle

            # Check exit conditions
            # SOTA v5.8: Pass exit mode from config
            strategy = self.config.get_strategy()
            exit_res = self.positions.check_exits(
                pos.pair,
                current_price,
                min_cost=min_cost,
                use_golden_ratchet=getattr(self.config, "use_golden_ratchet", True),
                tp1_pct=strategy.tp1 if hasattr(strategy, "tp1") else None,
                tp2_pct=strategy.tp2 if hasattr(strategy, "tp2") else None,
            )
            if exit_res:
                should_exit, ratio, reason = exit_res
                if should_exit:
                    amount = pos.quantity * ratio

                    # FORCE SELL for Dust Escape or Stop Loss
                    # Use market order if panic, otherwise smart
                    if "DUST" in reason or "STOP" in reason:
                        res = await self.exchange.execute_order(
                            pair=pos.pair, side="sell", amount=amount
                        )
                    else:
                        res = await self.exchange.execute_smart(
                            pair=pos.pair, side="sell", amount=amount
                        )

                    if res.success:
                        pnl_pct, pnl_eur = self.positions.close_position(
                            pos.pair, res.filled_price or current_price, reason
                        )
                        self.brain.update_daily_pnl(pnl_eur)
                        self.scanner.record_sell(pos.pair)
                        logger.info(
                            f"📤 Sold {pos.pair} {pnl_pct * 100:+.1f}% [{reason}]"
                        )

                        # 🎮 GAMIFICATION
                        # await self.gamification.process_trade(
                        #    pos.pair, "SELL", current_price, amount, pnl=pnl_eur
                        # )

                        # NOTIFICATION
                        from jobs.trader.reporting.templates import (
                            format_trade_notification,
                        )

                        try:
                            if getattr(self.config, "notify_sells", True):
                                msg = format_trade_notification(
                                    pos.pair,
                                    "sell",
                                    res.filled_price or current_price,
                                    res.filled_amount or amount,
                                    pnl_eur,
                                )
                                # Dual-channel: Phone Widget + Android FCM
                                await self._notify(msg)
                        except Exception as e:
                            logger.error(f"Failed to send sell notification: {e}")
                    else:
                        logger.error(f"📤 Sell Fail {pos.pair}: {res.message}")
        except Exception as e:
            logger.error(f"🫀 Position Error {pos.pair}: {e}")

    async def _scan_and_trade(self) -> None:
        """Scan market and open new positions (One Shot - No DCA)."""
        # Get candidates - EXCLUDE existing positions (One Shot)
        existing_pairs = self.positions.positions
        candidates = await self.scanner.scan(
            self.exchange,
            existing_positions=existing_pairs,
            limit=SCAN_TOP_X,  # Full Market Breadth (377)
            feed=self.feed,
        )

        # 🛡️ SACRED GUARD: Exclude BTC from standard trading (Cagnotte only)
        # We filter out any pair containing BTC or XBT to prevent accidental acquisition.
        # Bitcoin is reserved for the 'Cagnotte' mechanism (accumulated gains).
        candidates = [c for c in candidates if "BTC" not in c[0] and "XBT" not in c[0]]

        # 📦 Store scan result for optimizer access
        self.scanner.last_scan_result = candidates

        # ⚛️ QUANTUM PULSE: Measure Global Coherence (Tsunami Detector)
        if getattr(self.config, "quantum_enabled", True) and len(candidates) > 10:
            # Extract % change from candidates (candidates is list of (pair, data))
            # We need the 24h change or 1h change. Scanner returns list of (pair, ticker_data)
            # data is usually the ticker dict from Exchange.
            # Ticker format: {'symbol': 'XX', 'percentage': 1.2, ...}

            try:
                # Build snapshot vector (using ticker 'percentage' which is 24h change)
                # Ideally we want 1h change, but 24h is a proxy for "Today's Trend" alignment
                # SOTA: Scanner returns (pair, data). data['percentage'] is float.
                snapshot = [c[1].get("percentage", 0.0) for c in candidates if c[1]]

                q_res = quantum.calculate_coherence(snapshot)

                if q_res["state"] == "QUANTUM_ALIGNMENT":
                    logger.warning(
                        f"⚛️ TSUNAMI ALERT: Coherence {q_res['score']:.2f} ({q_res['direction']})"
                    )
                    # SOTA v5.9: Quantum Sniper Override - boost opportunities during tsunami
                    # Temporarily lower confidence threshold for next scan cycle
                    self._quantum_sniper_active = True
                    self._quantum_sniper_direction = q_res[
                        "direction"
                    ]  # BULLISH/BEARISH
                elif q_res["state"] == "RESONANCE":
                    logger.info(f"🌊 Resonance Building: {q_res['score']:.2f}")
                else:
                    # Reset sniper override when no quantum alignment
                    self._quantum_sniper_active = False

            except Exception as e:
                logger.debug(f"⚛️ Quantum Glitch: {e}")

        # Ensure we subscribe to candidates for future updates
        candidate_pairs = [c[0] for c in candidates]
        if candidate_pairs:
            self._safe_create_task(
                self.feed.subscribe_progressive(candidate_pairs), "FEED_UPDATE"
            )

        if not candidates:
            return

        # 0. Initialize Deep History (Chronos) - Opportunistic Background F13
        # Feed the Lake - Ensure only one init runs at a time
        if self.cycle_count % 13 == 0 and not getattr(
            self, "_history_init_running", False
        ):
            pairs_list = [c[0] for c in candidates]

            async def _safe_init_history(pairs):
                self._history_init_running = True
                try:
                    await initialize_deep_history(self.exchange, pairs[:34])  # F9
                except Exception:
                    logger.warning("🕐 Chronos Init Fail")
                finally:
                    self._history_init_running = False

            self._safe_create_task(_safe_init_history(pairs_list), "DEEP_HISTORY_INIT")

        strategy = self.config.get_strategy()

        # Pre-check: Max positions (Fail fast)
        if len(self.positions.positions) >= strategy.max_positions:
            return

        # 🧠 GOLDEN MEMORY AUTO-EXEC (Fast-Path)
        # SOTA 2026: If a pattern matches 89%+ (F89), execute immediately without full analysis
        if getattr(self.config, "golden_memory_autoexec", False):
            # Get current market context for pattern comparison
            btc_24h = await self._get_btc_24h_change()
            current_hour = datetime.now().hour

            for pair, ticker_data in candidates[:F34]:  # Check top F34 candidates only
                if pair in self.positions.positions:
                    continue  # Already have position

                # Build minimal indicator context for similarity check
                current_indicators = {
                    "rsi": ticker_data.get("rsi", 50),  # From scan cache if available
                    "btc_24h": btc_24h * 100,
                    "hour": current_hour,
                    "macd_strong": ticker_data.get("macd_strong", False),
                    "is_uptrend": ticker_data.get("is_uptrend", False),
                    "in_fib_zone": ticker_data.get("in_fib_zone", False),
                }

                # Check for auto-exec pattern match
                should_exec, similarity, reason = self.golden_memory.check_autoexec(
                    pair, current_indicators
                )

                if should_exec:
                    logger.success(
                        f"🧠 [GOLDEN MEMORY] Fast-path: {pair} @ {similarity * 100:.0f}%"
                    )

                    # Fetch current price for synthetic signal
                    try:
                        ticker = await self.exchange.fetch_ticker(pair)
                        price = ticker["last"]

                        # Create synthetic buy signal
                        synthetic_signal = Signal.buy(
                            pair=pair,
                            price=price,
                            reason=reason or f"Golden Memory {similarity * 100:.0f}%",
                            confidence=similarity * 100,  # Convert to %
                            stop_loss=price
                            * (1 + strategy.stop_loss),  # Use strategy SL
                            take_profit=price * (1 + strategy.tp1),
                            indicators=current_indicators,
                        )

                        # Execute immediately
                        if await self._execute_buy(synthetic_signal):
                            return  # One Shot - exit after first auto-exec

                    except Exception as e:
                        logger.warning(f"🧠 [GOLDEN MEMORY] Fast-path failed: {e}")

        # 🚀 SOTA PARALLEL ANALYSIS (PATROL MODE)
        # 🚀 SOTA TURBO: UNLEASHED (User Request)
        # Low CPU usage detected -> Scanning ALL candidates in parallel every cycle
        # scan_depth = len(candidates) (Implicit)

        # target_slice = candidates  # FULL BREADTH
        target_candidates = [c[0] for c in candidates]

        # Log simple status
        logger.info(f"👮 Patrol: {len(target_candidates)}p")

        # 1. Launch Parallel Tasks
        tasks = [self._analyze(pair) for pair in target_candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Filter & Sort Signals
        valid_signals = []
        for res in results:
            if isinstance(res, Signal) and res.is_buy:
                valid_signals.append(res)
            elif isinstance(res, Exception):
                logger.debug(f"Analysis failed (ignored): {res}")

        # Sort by confidence (Highest first)
        valid_signals.sort(key=lambda s: s.confidence, reverse=True)

        # 3. Execution (Loop through best signals until one passes checks)
        current_pairs = list(self.positions.positions.keys())

        for best_signal in valid_signals:
            pair = best_signal.pair

            # Safety: Double check existing
            if pair in self.positions.positions:
                continue

            # Safety: Correlation Check
            is_safe, warnings = await self.portfolio.check_correlation(
                pair, current_pairs
            )
            if not is_safe:
                logger.info(f"🛡️ Skip {pair} Corr")
                continue

            # INJECTED: Pulse (Sentiment) Update
            # (We do it once here if we have a valid buy candidate)
            await self.pulse.update(force=False)

            # Execute
            if await self._execute_buy(best_signal):
                break  # One Shot (One trade per cycle max)

        # 4. Auto-blacklist pairs that failed OHLCV fetch (1 week)
        self.scanner.blacklist_no_ohlcv_pairs(self.exchange)

    async def _analyze(self, pair: str) -> Signal:
        """Analyze a pair and generate full hybrid signal (Math → Signal → Validate → AI)."""
        # CORRECTION SOTA: Passer de 500 à F18 (2584) pour nourrir le Deep Context de l'IA
        df = await self.exchange.fetch_candles(pair, timeframe="15m", limit=F18)

        # SOTA v5.0: MTF H4 Context (Lazy Fetch)
        # We fetch H4 context to filter false signals. Limit 500 for EMA-200 convergence.
        df_h4 = await self.exchange.fetch_candles(pair, timeframe="4h", limit=500)

        # 🌊 Feed the Lake (Opportunistic Archiving)
        self._safe_create_task(
            self.history.store_from_df(pair, "15m", df), "HISTORY_ARCHIVE"
        )

        # Get context for hybrid decision
        eur_balance = await self.exchange.fetch_balance(
            "EUR"
        ) or await self.exchange.fetch_balance("ZEUR")
        cash = eur_balance.get("free", 0) if eur_balance else 0
        positions = {
            p.pair: {"cost": p.entry_price * p.quantity}
            for p in self.positions.get_open_positions()
        }
        btc_24h = await self._get_btc_24h_change()

        # CRITICAL: Use decide() for full pipeline (Math → Signal → Validate → AI)
        return await self.brain.decide(
            pair=pair,
            candles=df,
            cash=cash,
            positions=positions,
            btc_24h=btc_24h * 100,  # Convert to % for Brain
            mode=self.config.mode,
            candles_h4=df_h4,
        )

    async def _execute_buy(self, signal: Signal) -> bool:
        """Execute a buy signal."""
        trade_size = await self._calculate_trade_size()

        can, reason = await self.exchange.can_trade(
            signal.pair, trade_size / signal.price, signal.price
        )
        if not can:
            logger.debug(f"📥 [HEART] Skip {signal.pair}: {reason}")
            return False

        # 👻 GHOST MODE: Suppress Exchange Stop Loss if enabled
        sl_price_for_order = signal.stop_loss
        if getattr(self.config, "ghost_mode_enabled", True):
            sl_price_for_order = None
            logger.debug(f"👻 Ghost Mode: Hidden Stop Loss @ {signal.stop_loss}")

        result = await self.exchange.execute_smart(
            pair=signal.pair,
            side="buy",
            cost=trade_size,
            stop_loss_price=sl_price_for_order,
            post_only=(self.config.mode == "mitraillette"),
        )

        if result.success:
            self.positions.open_position(
                pair=signal.pair,
                entry_price=result.filled_price,
                quantity=result.filled_amount,
                stop_loss=signal.stop_loss,
                take_profits=[],  # NO PARTIALS - RATIO 1.0 ALWAYS
                context=signal.indicators or {},
            )
            logger.success(f"📥 Bought {signal.pair}")

            # 🎮 GAMIFICATION
            await self.gamification.process_trade(  # type: ignore[misc]
                signal.pair, "BUY", result.filled_price, result.filled_amount, pnl=0
            )

            # NOTIFICATION (SOTA 2026 - Rich Templates)
            from jobs.trader.reporting.templates import format_trade_notification

            # Derive TP (signal or default 5% for display)
            tp_price = signal.take_profit
            if not tp_price or tp_price <= 0:
                tp_price = result.filled_price * 1.05  # type: ignore[operator]  # Default display

            try:
                if getattr(self.config, "notify_buys", True):
                    # Legacy plain text (notification)
                    msg = format_trade_notification(
                        pair=signal.pair,
                        side="buy",
                        price=result.filled_price,
                        amount=result.filled_amount,
                        stop_loss=signal.stop_loss,
                        take_profit=tp_price,
                    )
                    # Rich HTML (Phone Widget)
                    trade_data = TradeData(
                        pair=signal.pair,
                        side=TradeSide.BUY,
                        price=result.filled_price,
                        amount=result.filled_amount,
                        cost=result.filled_price * result.filled_amount,  # type: ignore[operator]
                        stop_loss=signal.stop_loss,
                        take_profit=tp_price,
                    )
                    rich = render_rich_trade(trade_data)

                    # Dual-channel: Phone Widget + Android with actions
                    await self._notify(
                        msg,
                        actions=[
                            {"id": "view", "label": "Détails", "type": "primary"},
                        ],
                        body=rich["html"],
                        title=f"📥 ACHAT {signal.pair.split('/')[0]}",
                    )
            except Exception as e:
                logger.error(f"Failed to send buy notification: {e}")

            return True

        logger.warning(f"📥 Buy Fail {signal.pair}")
        return False

    async def _calculate_trade_size(self) -> float:
        """Calculate dynamic trade size based on regime."""
        strategy = self.config.get_strategy()

        btc_24h = await self._get_btc_24h_change()
        regime = self.brain.detect_regime(btc_24h * 100)

        from jobs.trader.config import REGIME_MULTIPLIERS

        regime_mult = REGIME_MULTIPLIERS.get(regime, 1.0)
        eur_balance = await self.exchange.fetch_balance("EUR")
        if not eur_balance:
            eur_balance = await self.exchange.fetch_balance("ZEUR")

        free_eur = eur_balance.get("free", 0) if eur_balance else 0

        free_eur = eur_balance.get("free", 0) if eur_balance else 0

        # SOTA v5.0: Fractional Kelly Criterion (0.5)
        # 1. Get stats
        try:
            # SOTA Fix: Use calculate_real_pnl to get accurate PnL stats
            stats = await self.api.calculate_real_pnl(days=7)

            win_rate = stats["win_rate"] / 100.0
            avg_win = stats["avg_win"]
            avg_loss = abs(stats["avg_loss"])  # Treat as positive magnitude

            # Kelly Formula: f = p/a - q/b
            # Where b = AvgWin/AvgLoss (Payoff Ratio)
            # Alternate form: f = p - (1-p)/b

            payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0

            if payoff_ratio > 0 and win_rate > 0.5:
                kelly_pct = win_rate - ((1 - win_rate) / payoff_ratio)
                fractional_kelly = kelly_pct * 0.5  # Half-Kelly for safety

                # Cap at 20% of Capital for safety
                fractional_kelly = min(fractional_kelly, 0.20)
                fractional_kelly = max(fractional_kelly, 0.01)  # Min 1%

                # Update base size
                kelly_size = free_eur * fractional_kelly
                logger.debug(
                    f"🧠 [KELLY] WR={win_rate:.2f} B={payoff_ratio:.2f} -> Size={kelly_size:.1f}€"
                )
                return (
                    min(strategy.max_trade, max(strategy.min_trade, kelly_size))
                    * regime_mult
                )

        except Exception as e:
            logger.debug(f"🧠 [KELLY] Calculation failed, using fallback: {e}")

        # Fallback: Flat 10%
        base_trade_size = min(
            strategy.max_trade, max(strategy.min_trade, free_eur * 0.1)
        )
        return base_trade_size * regime_mult

    async def _process_cagnotte(self) -> None:
        """
        Process the Sacred Cagnotte.
        If we have enough accumulated gains (e.g. 5€), BUY BTC immediately.
        """
        try:
            # Check threshold (e.g. 5.0€)
            if self.positions.cagnotte >= CAGNOTTE_BTC_THRESHOLD:
                amount_eur = CAGNOTTE_BTC_THRESHOLD
                logger.info("🐷 Cagnotte Threshold")

                # 1. Execute Market Buy (Sacred)
                # We use execute_order for direct market buy
                res = await self.exchange.execute_order(
                    pair=BTC_SACRED_PAIR,
                    side="buy",
                    amount=None,
                    cost=amount_eur,  # Buy by cost (5€ worth)
                )

                if res.success:
                    # 2. Deduct from Cagnotte
                    if self.positions.spend_cagnotte(amount_eur):
                        fill_amt = res.filled_amount or 0.0
                        logger.success(f"🐷 Sacred Buy {fill_amt:.6f} BTC")

                        # 3. Notify (SOTA 2026 - Rich Templates)
                        # Legacy plain text (notification)
                        fill_px = res.filled_price or 0.0
                        plain_msg = (
                            f"🐷 ACQUISITION SACRÉE\n"
                            f"Cagnotte atteinte: {amount_eur:.2f}€\n"
                            f"Acheté: {fill_amt:.6f} BTC\n"
                            f"Prix: {fill_px:.2f}€"
                        )
                        # Rich HTML (Phone Widget)
                        # SOTA: Sanitize inputs to avoid NoneType formatting errors
                        safe_btc_amount = (
                            res.filled_amount if res.filled_amount is not None else 0.0
                        )
                        safe_btc_price = (
                            res.filled_price if res.filled_price is not None else 0.0
                        )

                        rich = render_sacred_acquisition(
                            amount_eur=amount_eur,
                            btc_amount=safe_btc_amount,
                            btc_price=safe_btc_price,
                        )
                        await self._notify(
                            plain_msg,
                            body=rich["html"],
                            title="₿ ACQUISITION SACRÉE",
                        )
                    else:
                        # Should not happen if check passed, but safety first
                        logger.error("🐷 Cagnotte Spend Fail")
                else:
                    logger.warning("🐷 Buy Fail")

        except Exception as e:
            logger.error(f"🐷 Cagnotte Error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    async def _connect_with_retry(
        self, connect_fn, name: str, max_retries: int = 5
    ) -> bool:
        """Connect with Fibonacci exponential backoff."""
        delays = [1, 1, 2, 3, 5, 8, 13]  # PHI: Fibonacci delays
        for attempt in range(max_retries):
            try:
                await connect_fn()
                return True
            except Exception:
                delay = delays[min(attempt, len(delays) - 1)]
                logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(delay)
        return False

    def _safe_create_task(self, coro, name: str):
        """Create task with error logging (no silent failures)."""

        async def wrapped():
            try:
                await coro
            except Exception:
                logger.error(f"⚠️ Task {name} Fail")

        asyncio.create_task(wrapped())

    def _persist_cycle_count(self):
        """Persist cycle count to state.json for restart recovery."""
        try:
            state = load_json(STATE_FILE, default={})
            state["_cycle_count"] = self.cycle_count
            save_json(STATE_FILE, state)
        except Exception:
            pass  # Non-critical

    def _restore_cycle_count(self):
        """Restore cycle count from state.json."""
        try:
            state = load_json(STATE_FILE, default={})
            self.cycle_count = state.get("_cycle_count", 0)
            if self.cycle_count > 0:
                logger.info(f"🔄 Cycle Restored #{self.cycle_count}")
        except Exception:
            self.cycle_count = 0

    async def _run_initial_optimization(self) -> None:
        """Run optimization shortly after startup to set initial strategy."""
        try:
            from jobs.trader.data.history import is_deep_history_ready

            # Wait for Chronos deep history to be ready (max 10 min)
            max_wait = 600  # 10 minutes
            wait_interval = 15
            waited = 0

            while not is_deep_history_ready() and waited < max_wait:
                logger.debug(f"🧠 [OPT] Waiting for Chronos... ({waited}s/{max_wait}s)")
                await asyncio.sleep(wait_interval)
                waited += wait_interval

            if not is_deep_history_ready():
                logger.warning(
                    "🧠 [OPT] Chronos not ready after 10min, skipping optimization"
                )
                return

            # Wait for first scan cycle to complete (Phi-Beat ~55-90s typical)
            # We poll every 15s up to 3 times before giving up
            max_attempts = 4
            for attempt in range(max_attempts):
                await asyncio.sleep(30 if attempt == 0 else 15)

                scan_pairs = getattr(self.scanner, "last_scan_result", [])
                if scan_pairs:
                    break

                if attempt < max_attempts - 1:
                    logger.debug(
                        f"🧠 [OPT] Waiting for scan data... ({attempt + 1}/{max_attempts})"
                    )

            if not scan_pairs:
                logger.info(
                    "🧠 [OPT] No scan data after retries, skipping initial optimization"
                )
                return

            optimization_pairs = [c[0] for c in scan_pairs[:55]]  # F10 = 55
            logger.info(
                f"🧠 [OPT] Running initial optimization on {len(optimization_pairs)} pairs"
            )

            recommendation = await self.optimizer.run_global_optimization(
                optimization_pairs
            )

            if recommendation.get("status") == "switched":
                new_mode = recommendation.get("mode")
                logger.success(f"🧠 [OPT] Initial strategy set: {new_mode}")
        except Exception as e:
            logger.warning(f"🧠 [OPT] Initial optimization failed: {e}")

    async def _on_trade_received(self, trade: Dict) -> None:
        """
        Callback for new trades from WebSocket.
        Buffer and flush when ready (fire-and-forget).
        """
        async with self._buffer_lock:
            self._trade_buffer.append(trade)
            buffer_size = len(self._trade_buffer)

        # F12 = 144 (approx limit)
        if buffer_size >= 144:
            self._safe_create_task(self._flush_trade_buffer(), "TRADE_FLUSH")

    # ═══════════════════════════════════════════════════════════════════════════
    # SOTA: EVENT-DRIVEN DISPATCHER
    # ═══════════════════════════════════════════════════════════════════════════

    async def _on_price_update(self, pair: str, price: float) -> None:
        """
        Callback triggered by WebSocket on every price update.
        Filters noise and pushes to analysis queue.
        """
        last_price = self._last_analysis_price.get(pair, 0.0)

        # 1. First time saw? Analyze.
        if last_price == 0:
            self._last_analysis_price[pair] = price
            self._analysis_queue.put_nowait(pair)
            return

        # 2. Calculate variation
        variation = abs(price - last_price) / last_price

        # 3. Dynamic Thresholding (SOTA)
        # Mitraillette: 0.1% | Sniper: 0.25%
        # If big move, we queue immediately
        threshold = (
            self.MIN_VARIATION
            if self.config.mode == "mitraillette"
            else (self.MIN_VARIATION * 2.5)
        )

        if variation >= threshold:
            self._last_analysis_price[pair] = price
            # De-duplicate: If pair already in queue (conceptual), queue ignores?
            # Queue size implies pending work. If full, we skip (load shedding)
            if self._analysis_queue.qsize() < 100:
                self._analysis_queue.put_nowait(pair)

    async def _process_analysis_queue(self) -> None:
        """
        Infinite consumer loop for analysis queue.
        Event-Driven equivalent of the old Cron scan.
        """
        logger.info("🚀 Event Dispatcher On")

        while self.running:
            try:
                # Wait for work (Efficiency)
                pair = await self._analysis_queue.get()

                # Analyze immediately
                try:
                    signal = await self._analyze(pair)

                    if signal and signal.is_buy:
                        # Direct Execution path
                        await self._execute_buy(signal)

                except Exception:
                    logger.warning(f"⚠️ Analysis Fail {pair}")

                finally:
                    self._analysis_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("⚠️ Dispatcher Error")
                await asyncio.sleep(1.0)

    async def _flush_trade_buffer(self) -> None:
        """Flush trade buffer to DuckDB."""
        async with self._buffer_lock:
            if not self._trade_buffer:
                return

            # Swap buffer
            batch = self._trade_buffer[:]
            self._trade_buffer = []

        try:
            count = await self.history.store_trade_batch(batch)
            if count > 0:
                pass  # Silent success (too spammy)
        except Exception as e:
            logger.error(f"🫀 Flush Fail: {e}")

    async def _get_btc_24h_change(self) -> float:
        """Get BTC 24h change for context."""
        try:
            ticker = await self.exchange.fetch_ticker("BTC/EUR")
            if ticker and "percentage" in ticker:
                return ticker["percentage"] / 100.0  # Decimal
            return 0.0
        except Exception:
            return 0.0

    def _calculate_total_capital(self, cash_total: float) -> float:
        """Calculate total estimated capital (Cash + Positions Value)."""
        pos_value = sum(
            p.quantity * p.current_price for p in self.positions.get_open_positions()
        )
        return cash_total + pos_value

    # ═══════════════════════════════════════════════════════════════════════════
    # SCHEDULING & REPORTING
    # ═══════════════════════════════════════════════════════════════════════════

    def _schedule_reports(self):
        """Schedule periodic reports using schedule library."""
        # Clear existing jobs (Hot Reload)
        schedule.clear()

        # Status report every X minutes (Default F89)
        interval = getattr(self.config, "report_interval", F89)
        schedule.every(interval).minutes.do(self._trigger_status_report)
        logger.info(f"📅 Report Interval: {interval}m")

        # SOTA v5.4: UI Data Refresh (Every 5m/F5) - Keeps cache fresh without spam
        schedule.every(5).minutes.do(self._trigger_ui_refresh)

        # Night cycle at 03:00 (backup via schedule, main trigger in _work_cycle)
        schedule.every().day.at("03:00").do(self._trigger_night_cycle)

        # Phantom Order Protection (Every hour)
        schedule.every(60).minutes.do(self._trigger_order_maintenance)

        logger.info("📅 Schedule Ready")

    def _trigger_status_report(self):
        """Trigger async status report from scheduler."""
        if getattr(self.config, "notify_reports", True):
            self._safe_create_task(self._send_status_report(), "STATUS_REPORT")

    def _trigger_ui_refresh(self):
        """Trigger background cache refresh for UI."""
        self._safe_create_task(self._refresh_cache(), "UI_REFRESH")

    def _trigger_night_cycle(self):
        """Trigger async night cycle from scheduler."""
        self._safe_create_task(self._run_night_cycle(), "NIGHT_CYCLE")

    def _trigger_order_maintenance(self):
        """Trigger stale order cancellation."""
        self._safe_create_task(
            cancel_stale_orders(self.exchange, max_age_minutes=60), "ORDER_CLEANUP"
        )

    async def _run_night_cycle(self):
        """Execute night cycle procedure."""
        try:
            logger.info("🌙 Night Cycle...")
            stats = self.positions.get_today_stats()
            trades = await self.api.fetch_trade_history(days=1)
            await self.night_cycle.run_night_procedure(stats, trades)
            report = self.night_cycle.prepare_morning_report()
            if report and getattr(self.config, "notify_reports", True):
                await self._notify(report)  # Standard 362: Full content
        except Exception as e:
            logger.error(f"🌙 Night Error: {e}")

    async def _refresh_cache(self) -> Dict:
        """
        Refresh _cached_report for Web API (SINGLE PRODUCER).
        Runs frequently to keep UI alive (unlike hourly reports).
        """
        logger.info("♻️ Cache Refresh")
        # Analytics imported here but used elsewhere - suppress import for now

        try:
            logger.info("♻️ Building Context")
            # 1. Fetch Context (Base)
            # 1. Fetch Context (Base) WITH Live Price Update
            open_positions = self.positions.get_open_positions()
            if open_positions:
                try:
                    pairs = [p.pair for p in open_positions]
                    logger.info(f"♻️ Live Tickers: {len(pairs)} pairs")
                    # SOTA v6.0: Bulk Fetch Tickers for Real-Time Precision
                    tickers = await self.exchange.fetch_tickers(pairs)
                    for pair, ticker in tickers.items():
                        price = ticker.get("last", 0.0)
                        if price > 0:
                            # Update memory directly
                            self.positions.update_position(pair, price)
                except Exception as e:
                    logger.warning(f"⚠️ Live Ticker Fail: {e}")

            context = await self._build_context()
            logger.info("♻️ Fetching Balances")

            # 2. Financial Context (Capital Actif vs Sacred Reserve)
            real_total_capital = context.get("total_capital", 0.0)

            # Sacred Reserve (BTC) - ROBUST FETCH
            all_balances = await self.exchange.fetch_all_balances()
            btc_data = all_balances.get("BTC") or all_balances.get("BTC_TOTAL") or {}

            btc_total = btc_data.get("total", 0.0)
            btc_value = btc_data.get("value_eur", 0.0)

            if btc_total > 0 and btc_value == 0:
                btc_ticker = await self.exchange.fetch_ticker("BTC/EUR")
                price = btc_ticker.get("last", 0.0)
                btc_value = btc_total * price

            # Allow fetching Earn allocations
            btc_earn = 0.0
            try:
                allocations = await self.api.get_earn_allocations()
                for alloc in allocations:
                    # SOTA v5.1: Robust Asset matching (Handle XBT, BTC, .S, .M suffixes)
                    asset = alloc.get("asset", "").upper()

                    # Normalize XBT/Z...
                    if asset.startswith("XBT"):
                        asset = "BTC" + asset[3:]
                    elif (
                        len(asset) == 4 and asset.startswith("X") and "BTC" not in asset
                    ):
                        pass  # e.g. XDG -> DOGE handle if needed, but here we care about BTC

                    # Check for BTC presence
                    if "BTC" in asset or "XBT" in asset:
                        btc_earn += float(alloc.get("total", 0.0))

            except Exception as e:
                logger.warning(f"⚠️ Earn Fetch Fail: {e}")

            # 3. Fetch Stats (History)
            try:
                stats_24h = await self.api.calculate_real_pnl(days=1)
                stats_30d = await self.api.calculate_real_pnl(days=30)

                win_rate = stats_30d.get("win_rate", 0.0)
                wins = stats_30d.get("wins", 0)
                losses = stats_30d.get("losses", 0)
                pnl_daily = stats_24h.get("total_pnl", 0.0)
                pnl_global = stats_30d.get("total_pnl", 0.0)

            except Exception:
                logger.warning("⚠️ History Fetch Warn")
                wins, losses, win_rate, pnl_daily, pnl_global = 0, 0, 0.0, 0.0, 0.0

            # 4. Fetch Raw History (For UI)
            trades_history = []
            try:
                # SOTA v5.12: Pass closed positions for orphan PnL calculation
                closed_dicts = [p.to_dict() for p in self.positions.closed_today]
                trades_history = await self.api.fetch_enriched_history(
                    days=7, lookback=60, closed_positions=closed_dicts
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"⚠️ Context Fail: {e}")
            wins, losses, win_rate, pnl_daily, pnl_global = 0, 0, 0.0, 0.0, 0.0
            real_total_capital, btc_value, btc_total, btc_earn = 0.0, 0.0, 0.0, 0.0
            trades_history = []
            context = await self._build_context()

        try:
            # Regime & Sentiment
            btc_24h = await self._get_btc_24h_change()
            regime = self.brain.detect_regime(btc_24h * 100)
            sentiment = (
                self.pulse.score if hasattr(self, "pulse") and self.pulse else 50
            )

            mode = "🤖 IA" if self.config.ai_enabled else "👤 MANUEL"
            submode = self.config.mode.upper() if self.config.mode else "STANDARD"
            total_wealth = real_total_capital + btc_value

            pos_val = 0.0
            if "positions" in context and isinstance(context["positions"], dict):
                pos_val = sum(
                    p.get("quantity", 0) * p.get("current_price", 0)
                    for p in context["positions"].values()
                )

            context.update(
                {
                    "regime": regime,
                    "btc_24h": btc_24h * 100,
                    "sentiment": sentiment,
                    "submode": submode,
                    "mode": mode,
                    "positions_value": pos_val,
                    "positions_list": [
                        {
                            "pair": k,
                            "value": v.get("quantity", 0) * v.get("current_price", 0),
                            "pnl_pct": v.get("pnl_pct", 0),
                        }
                        for k, v in context.get("positions", {}).items()
                    ],
                    "capital_actif": real_total_capital,
                    "total_capital": total_wealth,
                    "btc_total": btc_total,
                    "btc_earn": btc_earn,
                    "btc_value": btc_value,
                    "wins": wins,
                    "losses": losses,
                    "win_rate_session": win_rate,
                    "pnl_daily": pnl_daily,
                    "pnl_session": pnl_global,
                    "trades_history": trades_history,
                    "cagnotte": context.get("cagnotte", 0.0),
                    "sync_status": "READY",
                }
            )

            # SOTA 2026: Cache for Web API
            self._cached_report = context.copy()

            # Persist for Hot Start
            try:
                cache_file = MEMORIES_DIR / "trader" / "trader_cache.json"
                atomic_save_json(cache_file, self._cached_report)
            except Exception:
                pass

            return context

        except Exception as e:
            logger.error(f"📤 Cache Fail: {e}")
            return {}

    def _load_hot_start_cache(self):
        """Load persistent cache for instant UI availability."""
        try:
            cache_file = MEMORIES_DIR / "trader" / "trader_cache.json"
            if cache_file.exists():
                data = load_json(cache_file)
                if data:
                    self._cached_report = data
                    # Mark as cached/stale for UI
                    self._cached_report["sync_status"] = "CACHED"
                    logger.info("🔥 Hot Start: Cache Loaded")
        except Exception as e:
            logger.warning(f"🔥 Hot Start Fail: {e}")

    async def _gather_and_send_rich_report(self):
        """
        Shared logic: Gather full context and send format_rich_report.
        SOTA v4.1: Uses Kraken Ground Truth (Daily Stats + Exact Accounting).
        """
        from jobs.trader.reporting.periodic import format_rich_report

        try:
            # Refresh cache first
            context = await self._refresh_cache()

            if not context:
                logger.warning("⚠️ No Context")
                return

            report_html = format_rich_report(context)
            if getattr(self.config, "notify_reports", True):
                # SOTA 2026: Explicit title/body separation (Standard 362.18)
                from datetime import datetime

                time_str = datetime.now().strftime("%H:%M")
                regime = context.get("regime", "NEUTRE")
                pnl = context.get("pnl_session", 0)
                regime_icon = {"BULL": "🟢", "BEAR": "🔴"}.get(regime, "🟡")

                title = f"📊 RAPPORT {time_str} {regime_icon} {regime}"
                # Plain text summary for push notification
                plain_summary = f"Capital: {context.get('total_capital', 0):.2f}€ | PnL: {pnl:+.2f}€"

                # SOTA 2026: Deduplication - Replace old reports instead of accumulating
                await self._notify(
                    message=plain_summary,
                    title=title,
                    body=report_html,  # Rich HTML for Phone Widget
                    dedup_key="TRADER_PERIODIC_REPORT",  # Standard 362.103
                )
            logger.info("📤 Report Sent")

        except Exception as e:
            logger.error(f"📤 Report Fail: {e}")

    async def _send_status_report(self):
        """Send periodic status report via Phone Widget + Android."""
        await self._gather_and_send_rich_report()

    async def _build_context(self) -> Dict:
        """Build complete context for reporting."""
        eur_balance = await self.exchange.fetch_balance("EUR")
        if not eur_balance:
            eur_balance = await self.exchange.fetch_balance("ZEUR")

        cash = eur_balance.get("free", 0) if eur_balance else 0
        total_capital = self._calculate_total_capital(
            eur_balance.get("total", 0) if eur_balance else 0
        )

        today = {}
        try:
            today = self.positions.get_today_stats()
        except Exception:
            pass

        return {
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "cycle_count": self.cycle_count,
            "cash": cash,
            "total_capital": total_capital,
            "positions": {
                p.pair: p.to_dict() for p in self.positions.get_open_positions()
            },
            "today": today,
            "circuit_breaker": self.positions.circuit_breaker_active,
            "mode": self.config.mode,
        }

    async def _send_startup_notification(self):
        """Send startup notification (Rich Report)."""
        # User requested the exact same rich report at startup
        logger.info("📤 Startup Report")
        await self._gather_and_send_rich_report()


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY & ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


def create_trading_heart(config: TraderConfig = None) -> TradingHeart:
    """Factory function to create TradingHeart."""
    return TradingHeart(config)


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON EXPORT (FOR LOADER)
# ═══════════════════════════════════════════════════════════════════════════

trader = create_trading_heart()


async def run() -> None:
    """Entry point for the trader."""
    await trader.start()


if __name__ == "__main__":
    asyncio.run(run())
