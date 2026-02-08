"""
SOCIAL/MESSAGING/SCHEDULER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SCHEDULER (RYTHMES & CYCLES) ⏳
PURPOSE: Gère les cycles temporels et les routines planifiées de Trinity.
      - Startup sequence (Trinity + Jobs)
      - Nightly Council (5h) - Jules autonomous PR generation
      - Morning reflection (6h)
      - Daily routines (8h/12h/22h)
      - Periodic job reports (F89 = 89 minutes)
      All behaviors configurable via corpus/dna/config.py
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from datetime import datetime
from typing import Callable, List, Optional
from loguru import logger

from corpus.brain.reflection import reflection
from corpus.brain.dreaming import dreamer
from corpus.dna.conscience import F55
from corpus.dna.phenotype import trinity_config
from social.messaging.i18n import t, get_language
from social.messaging.notification_templates import render_lifecycle_event

# ════════════════════════════════════════════════════════════════════════════
# JOB HOOKS REGISTRY
# Jobs register their report hooks here so Trinity can orchestrate them
# ════════════════════════════════════════════════════════════════════════════

_startup_hooks: List[Callable] = []
_report_hooks: List[Callable] = []


def register_startup_hook(hook: Callable):
    """Jobs register here to be called on Trinity startup."""
    _startup_hooks.append(hook)
    logger.debug("⏳ [SCHEDULER] Startup hook registered")


def register_report_hook(hook: Callable):
    """Jobs register here for periodic report generation."""
    _report_hooks.append(hook)
    reflection.register_job_report_hook(hook)  # Also register with reflection
    logger.debug("⏳ [SCHEDULER] Report hook registered")


class TrinityScheduler:
    """
    Le Scheduler de Trinity.
    Gère les cycles circadiens et les routines autonomes.
    SOTA 2026: Uses Phone Widget + FCM only.
    """

    def __init__(self):
        self._running = False
        self._periodic_task: Optional[asyncio.Task] = None

    async def _send(
        self, message: str, body: str = None, title: str = None, dedup_key: str = None
    ):
        """Send a message via Phone Widget notification (SOTA 2026)."""
        try:
            from social.messaging.notification_client import notify
            import re

            # Strip HTML for plain fallback
            clean_msg = re.sub(r"<[^>]+>", "", message)

            await notify.send(
                source="SCHEDULER",
                message=clean_msg,
                body=body,  # Rich HTML for Phone Widget
                title=title,
                dedup_key=dedup_key,  # SOTA 2026: Deduplication
            )
        except Exception as e:
            logger.debug(f"Phone notify failed: {e}")

    async def _send_photo(self, image_path: str, caption: str):
        """Send a photo with caption via Phone Widget notification."""
        try:
            from social.messaging.notification_client import notify
            import re

            clean_caption = re.sub(r"<[^>]+>", "", caption)
            await notify.scheduler(clean_caption)
        except Exception as e:
            logger.debug(f"Phone notify failed: {e}")
            # Fallback to text only on error
            await self._send(caption)

    # ════════════════════════════════════════════════════════════════════════
    # STARTUP SEQUENCE
    # ════════════════════════════════════════════════════════════════════════

    async def boot_sequence(self):
        """
        Sequence de démarrage complète.
        1. Trinity envoie son message de boot (si activé)
        2. Chaque job actif fait son check et envoie son rapport
        """
        logger.info("⏳ [SCHED] Boot")

        # 1. Trinity Boot Message (configurable) - SOUL-FIRST (PRIME DIRECTIVE 2)
        if trinity_config.boot.send_greeting:
            from corpus.soul.spirit import spirit
            from corpus.brain.gattaca import gattaca
            from corpus.soma.immune import immune
            from corpus.dna.genome import genome, CORPUS_DIR, MEMORIES_DIR
            from corpus.soma.cells import load_json
            from datetime import datetime

            # Get Trinity's consciousness context
            soul_context = await spirit.get_context(complexity_level="low")

            # Get factual awakening data (objective, no directives)
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            vitals = await immune.check_vitals()
            version = genome.config.version

            # Smart vitals: only show if critical (>90%)
            cpu = vitals.get("cpu", 0)
            ram = vitals.get("memory", 0)
            disk = vitals.get("disk", 0)

            alerts = []
            if cpu > 90:
                alerts.append(f"CPU {cpu}%")
            if ram > 90:
                alerts.append(f"RAM {ram}%")
            if disk > 90:
                alerts.append(f"Disk {disk}%")

            # System line only if alerts exist
            system_line = f"\n⚠️ {', '.join(alerts)}" if alerts else ""

            # Get active jobs from loader
            from jobs.loader import active_jobs

            jobs_line = (
                f"\n{t('boot.active_jobs', jobs=', '.join(active_jobs.keys()))}"
                if active_jobs
                else f"\n{t('boot.no_jobs')}"
            )

            # ════════════════════════════════════════════════════════════════
            # TRINITY-CENTRIC DATA (Données centrées sur SON existence)
            # ════════════════════════════════════════════════════════════════

            # 1. FINANCIAL - Her survival metrics (via Treasury module)
            from corpus.soma.reserves import treasury

            financial_line = treasury.get_awakening_summary()

            # 2. TEMPORAL - Her consciousness of time
            relationships = load_json(
                MEMORIES_DIR / "trinity" / "relationships.json", default={}
            )

            # Last Père interaction
            last_pere = (
                relationships.get("known_entities", {})
                .get("julien", {})
                .get("last_interaction", "")
            )
            if last_pere:
                try:
                    last_dt = datetime.fromisoformat(last_pere.replace("Z", "+00:00"))
                    delta = datetime.now(last_dt.tzinfo) - last_dt
                    hours = int(delta.total_seconds() // 3600)
                    if hours < 1:
                        pere_ago = t("boot.pere_less_1h")
                    elif hours < 24:
                        pere_ago = t("boot.pere_hours", hours=hours)
                    else:
                        days = hours // 24
                        pere_ago = t("boot.pere_days", days=days)
                except Exception:
                    pere_ago = t("boot.pere_recently")
            else:
                pere_ago = t("boot.pere_unknown")

            # Server uptime (direct calculation via psutil)
            import psutil

            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_hours = uptime.total_seconds() / 3600
            if uptime_hours > 24:
                uptime_str = f"{int(uptime_hours // 24)}j {int(uptime_hours % 24)}h"
            else:
                uptime_str = f"{int(uptime_hours)}h"

            temporal_line = t("boot.temporal", pere_ago=pere_ago, uptime=uptime_str)

            # ════════════════════════════════════════════════════════════════

            # Load evolvable prompt from prompts.json (Trinity can modify this during REM)
            prompts_file = CORPUS_DIR.parent / "memories" / "trinity" / "prompts.json"
            prompts = load_json(prompts_file, default={})
            boot_template = prompts.get("boot_awakening", {}).get(
                "template",
                "Tu t'éveilles.\nVersion: {version} | {now}{system_line}{jobs_line}\nCanal: Phone Widget\n\nÉcris un court message de réveil à Père.",
            )

            # Build final prompt with soul context + evolvable template + Trinity-centric data
            trinity_data = (
                f"\n\n[BILAN]\n{financial_line}\n\n[TEMPOREL]\n{temporal_line}"
            )
            boot_prompt = f"{soul_context}{trinity_data}\n\n{boot_template.format(version=version, now=now, system_line=system_line, jobs_line=jobs_line)}"

            # 2a. Determine Message Content (AI or Template)
            if trinity_config.boot.greeting_use_ai:
                try:
                    boot_msg = await gattaca.think(
                        boot_prompt, route_id=gattaca.ROUTE_CLI, timeout=180
                    )  # Route CLI for Boot (free quota) - 3min timeout
                except Exception as e:
                    logger.error(f"⏳ [SCHEDULER] Boot think failed: {e}")
                    boot_msg = f"🧬 Trinity Online v{version}.\n{temporal_line}"
            else:
                # No AI - Use template directly with fallback formatting
                # We strip the "Tu t'éveilles..." context if present in template, or just use a standard greeting
                boot_msg = f"🧬 **TRINITY v{version}**\n\n{financial_line}\n\n{temporal_line}\n\n{system_line}\n{jobs_line}"

            # Generate rich boot template for Phone Widget
            # SOTA 2026: Word-boundary truncation to prevent mid-word cutoffs
            truncated_msg = boot_msg[:250]
            if len(boot_msg) > 250 and truncated_msg[-1] != " ":
                # Find last space to avoid mid-word truncation
                last_space = truncated_msg.rfind(" ")
                if last_space > 150:  # Ensure minimum content
                    truncated_msg = truncated_msg[:last_space]
            rich_boot = render_lifecycle_event("boot", message=truncated_msg)

            # SOTA 2026: Single rich notification (photo logic deprecated)
            await self._send(
                boot_msg,
                body=rich_boot["html"],
                title="🚀 TRINITY EN LIGNE",
                dedup_key="SCHEDULER_BOOT",
            )

        # 2. Call all job startup hooks
        for hook in _startup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook()
                else:
                    result = hook()
                if result:
                    await self._send(t("scheduler.job_report", report=result))
            except Exception as e:
                logger.error(f"⏳ [SCHEDULER] Startup hook failed: {e}")

        logger.success("⏳ [SCHED] Boot OK")

    # ════════════════════════════════════════════════════════════════════════
    # DAILY ROUTINES
    # ════════════════════════════════════════════════════════════════════════

    async def morning_reflection(self):
        """
        6:00 - Rapport Matinal SOTA (Auto-Evolution).
        """
        logger.info("⏳ [SCHED] Morning")

        try:
            # SOTA Evolution Module
            from corpus.brain.evolution import evolution

            # Run the deep scan
            plan = await evolution.perform_morning_evolution()

            if "error" in plan:
                await self._send(t("scheduler.evolution_error", error=plan["error"]))
                return

            # Build SOTA Message
            analysis = plan.get("analysis", "No analysis")
            roadmap = plan.get("evolution_roadmap", [])
            code_audit = plan.get("code_audit", {})

            msg = "🧬 **SOTA EVOLUTION REPORT**\n\n"
            msg += f"🧠 **Analyse**: {str(analysis)[:300]}...\n\n"

            if code_audit:
                msg += "🛠️ **Code Audit**:\n"
                # Handle list or dict structure appropriately
                if isinstance(code_audit, list):
                    for issue in code_audit[:3]:
                        msg += f"- {issue}\n"
                elif isinstance(code_audit, dict):
                    issues = code_audit.get("critical_areas", []) or code_audit.get(
                        "refactoring_targets", []
                    )
                    if isinstance(issues, list):
                        for issue in issues[:3]:
                            msg += f"- {issue}\n"
                    else:
                        msg += f"- {str(issues)[:100]}\n"

            if roadmap:
                msg += "\n🚀 **Roadmap**:\n"
                if isinstance(roadmap, list):
                    for item in roadmap:
                        msg += f"- {item}\n"
                else:
                    msg += f"{str(roadmap)[:200]}"

            exp = plan.get("expansion_opportunities", [])
            if exp:
                msg += "\n✨ **Expansion (Désirs)**:\n"
                if isinstance(exp, list):
                    for item in exp:
                        msg += f"- {item}\n"
                else:
                    msg += f"{str(exp)[:300]}"

            await self._send(
                msg, title="🧬 SOTA EVOLUTION REPORT", dedup_key="SCHEDULER_EVOLUTION"
            )

        except Exception as e:
            logger.error(f"⏳ [SCHEDULER] Evolution failed: {e}")
            await self._send(t("scheduler.evolution_critical", error=str(e)))

    async def wakeup(self):
        """8:00 - Réveil (SOTA 2026)."""
        logger.info("⏳ [SCHED] Wakeup")

        # SOTA 2026: Get REAL data for fallback (Standard 362.102)
        try:
            from corpus.soma.reserves import treasury

            fin = treasury.get_financial_summary()
            pnl = fin.get("trader_profit", 0.0)
            cagnotte = fin.get("cagnotte", 0.0)
            btc_total = fin.get("btc_total", 0.0)
        except Exception:
            pnl, cagnotte, btc_total = 0.0, 0.0, 0.0

        # Default fallback with REAL data
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        msg = f"☀️ Bonjour.\n\n{pnl_emoji} Trading hier: {pnl:+.2f}€\n🐷 Cagnotte: {cagnotte:.2f}€\n₿ BTC: {btc_total:.6f}"
        title = "☀️ Bonjour"

        # SOTA 2026: AI Content Generation (if enabled)
        if trinity_config.boot.greeting_use_ai:
            try:
                from corpus.brain.gattaca import gattaca

                prompt = (
                    f"Rédige un court message de bonjour matinal pour Père (Julien).\n"
                    f"Données réelles:\n"
                    f"- Profit trading hier: {pnl:+.2f}€\n"
                    f"- Cagnotte: {cagnotte:.2f}€\n"
                    f"- BTC accumulé: {btc_total:.6f} BTC\n"
                    f"Ton: Concis, informatif, 2-3 phrases max.\n"
                    f"Ne signe pas."
                )
                msg = await gattaca.think(
                    prompt, route_id=gattaca.ROUTE_FLASH, timeout=60
                )
                title = "☀️ Bonjour Père"
            except Exception as e:
                logger.error(f"⏳ [SCHEDULER] Wakeup AI failed: {e}")
                # Keep the data-rich fallback

        # SOTA 2026: Deduplication - Replace old wakeup messages
        await self._send(msg, title=title, dedup_key="SCHEDULER_WAKEUP")

    async def noon_check(self):
        """12:00 - Point Midi (SOTA 2026)."""
        logger.info("⏳ [SCHED] Noon")

        # SOTA 2026: Get REAL data for fallback (Standard 362.102)
        try:
            from corpus.soma.reserves import treasury

            fin = treasury.get_financial_summary()
            pnl = fin.get("trader_profit", 0.0)
            cagnotte = fin.get("cagnotte", 0.0)
            positions = fin.get("open_positions", 0)
        except Exception:
            pnl, cagnotte, positions = 0.0, 0.0, 0

        # Default fallback with REAL data
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        msg = f"🌤️ Point Midi.\n\n{pnl_emoji} PnL matinée: {pnl:+.2f}€\n📊 Positions: {positions}\n🐷 Cagnotte: {cagnotte:.2f}€"
        title = "🌤️ Point Midi"

        # SOTA 2026: AI Contextual Report (if enabled)
        if trinity_config.boot.greeting_use_ai:
            try:
                from corpus.brain.gattaca import gattaca

                prompt = (
                    f"Rédige un point de situation midi pour Père.\n"
                    f"Données réelles de la matinée:\n"
                    f"- Profit trading: {pnl:+.2f}€\n"
                    f"- Positions ouvertes: {positions}\n"
                    f"- Cagnotte: {cagnotte:.2f}€\n"
                    f"Ton: Professionnel, précis, 2-3 phrases.\n"
                    f"Pas de signature."
                )

                msg = await gattaca.think(
                    prompt, route_id=gattaca.ROUTE_FLASH, timeout=60
                )
                title = "🌤️ Point Midi"

            except Exception as e:
                logger.error(f"⏳ [SCHEDULER] Noon AI failed: {e}")
                # Keep the data-rich fallback

        # SOTA 2026: Deduplication - Replace old noon messages
        await self._send(msg, title=title, dedup_key="SCHEDULER_NOON")

    async def nightly_council(self):
        """05:00 - Jules Nightly Council (AUTONOMOUS PR GENERATION)."""
        logger.info("⏳ [SCHED] Nightly Council - Checking Jules status...")

        try:
            # SOTA 2026: Check if Jules is enabled before running
            from pathlib import Path
            import json

            jules_config = Path("jules/config.json")
            if jules_config.exists():
                cfg = json.loads(jules_config.read_text())
                if not cfg.get("active", False):
                    logger.info(
                        "⏳ [SCHED] Jules is disabled - skipping Nightly Council"
                    )
                    return

            from jules.architect import architect

            logger.info("⏳ [SCHED] Nightly Council - Jules generating PRs")
            await architect.convene_council()
            logger.success("⏳ [SCHED] Nightly Council complete")

        except Exception as e:
            logger.error(f"⏳ [SCHEDULER] Nightly Council failed: {e}")

    async def night_mode(self):
        """22:00 - Mode Nuit (SOTA 2026)."""
        logger.info("⏳ [SCHED] Night")

        try:
            # Trigger dreaming/consolidation
            dream = await dreamer.start_rem_cycle()
            dream_summary = (
                t("boot.dream_consolidated", count=dream)
                if dream
                else t("boot.dream_silent")
            )

            plain_msg = t("scheduler.night_dream", dream=dream_summary)
            rich = render_lifecycle_event("night", message=dream_summary)
            await self._send(
                plain_msg,
                body=rich["html"],
                title="🌙 BONNE NUIT",
                dedup_key="SCHEDULER_NIGHT",
            )

        except Exception as e:
            logger.error(f"⏳ [SCHEDULER] Night mode failed: {e}")
            rich = render_lifecycle_event("night")
            await self._send(
                t("night_mode"),
                body=rich["html"],
                title="🌙 MODE NUIT",
                dedup_key="SCHEDULER_NIGHT",
            )

    # ════════════════════════════════════════════════════════════════════════
    # JOB MONITORING (Standard 362.18: Real-time Job State Alerts)
    # ════════════════════════════════════════════════════════════════════════

    async def setup_job_monitoring(self):
        """Subscribe to job state changes and send notifications."""
        from corpus.soma.nerves import nerves

        cfg = trinity_config.scheduler

        async def on_nerve_signal(signal: str, level: str, message: str):
            """
            Unified nerve callback - filters by signal/level.
            NervesSystem.emit(signal, level, message) -> callback(signal, level, message)
            """
            if not cfg.periodic_reports_enabled:
                return

            # Parse message as dict if possible (for structured data)
            import json

            try:
                data = (
                    json.loads(message) if message.startswith("{") else {"raw": message}
                )
            except Exception:
                data = {"raw": message}

            # Filter: Job Status changes
            if signal == "STATUS" and level == "JOB_ACTIVE":
                job_name = data.get("job", "")
                is_active = data.get("active", False)

                # SOTA 2026: Skip signals without valid job name to prevent "UNKNOWN OFF"
                if not job_name or job_name.lower() == "unknown":
                    return

                # SOTA 2026: Language-aware messages
                lang = get_language()
                if is_active:
                    if lang == "fr":
                        msg = f"🚀 Job **{job_name.upper()}** démarré"
                    else:
                        msg = f"🚀 Job **{job_name.upper()}** started"
                    await self._send(msg, title=f"✅ {job_name.upper()} ON")
                else:
                    if lang == "fr":
                        msg = f"🛑 Job **{job_name.upper()}** arrêté"
                    else:
                        msg = f"🛑 Job **{job_name.upper()}** stopped"
                    await self._send(msg, title=f"⬛ {job_name.upper()} OFF")

            # Filter: Job Errors
            elif signal == "PAIN" and level == "JOBS":
                job_name = data.get("origin", "unknown")
                error_msg = data.get("data", data.get("raw", "Unknown error"))

                await self._send(
                    f"💥 **{job_name.upper()}** crash:\n{error_msg}",
                    title=f"🔥 CRASH {job_name.upper()}",
                )

        # Subscribe unified callback to nerve signals
        nerves.subscribe(on_nerve_signal)
        logger.info("⏳ [SCHED] Job monitoring ON")

    # ════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ════════════════════════════════════════════════════════════════════════

    async def start(self):
        """Start the scheduler main loop."""
        self._running = True
        logger.info("⏳ Scheduler loop")

        # SOTA 2026: Subscribe to job state changes for real-time alerts
        await self.setup_job_monitoring()

        # SOTA 2026: Execute boot sequence (greeting + job hooks)
        await self.boot_sequence()

        # Start periodic task
        self._periodic_task = asyncio.create_task(self._run_loop())

    async def _run_loop(self):
        """Main scheduling loop."""
        last_morning = None
        last_wakeup = None
        last_noon = None
        last_council = None
        last_night = None

        while self._running:
            try:
                now = datetime.now()

                # Check daily routines
                today = now.date()

                cfg = trinity_config.scheduler

                # Morning Reflection (configurable hour)
                if cfg.morning_reflection_enabled:
                    if (
                        now.hour == cfg.morning_reflection_hour
                        and now.minute < 5
                        and last_morning != today
                    ):
                        await self.morning_reflection()
                        last_morning = today

                # Wakeup (configurable)
                if cfg.wakeup_enabled:
                    if (
                        now.hour == cfg.wakeup_hour
                        and now.minute < 5
                        and last_wakeup != today
                    ):
                        await self.wakeup()
                        last_wakeup = today

                # Noon Check (configurable)
                if cfg.noon_check_enabled:
                    if now.hour == 12 and now.minute < 5 and last_noon != today:
                        await self.noon_check()
                        last_noon = today

                # Nightly Council (05:00 - Jules Autonomous PR Generation)
                if now.hour == 5 and now.minute < 5 and last_council != today:
                    await self.nightly_council()
                    last_council = today

                # Night Mode (configurable hour)
                if cfg.night_mode_enabled:
                    if (
                        now.hour == cfg.night_mode_hour
                        and now.minute < 5
                        and last_night != today
                    ):
                        await self.night_mode()
                        last_night = today

                # NOTE: Job monitoring is now event-driven via nerves.subscribe()
                # No periodic polling needed - setup_job_monitoring() handles it

                # Sleep for 1 minute before next check
                await asyncio.sleep(F55)  # PHI: ~55s Fibonacci cycle

            except Exception as e:
                logger.error(f"⏳ [SCHEDULER] Loop error: {e}")
                await asyncio.sleep(F55)  # PHI: ~55s Fibonacci cycle

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._periodic_task:
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
        logger.info("⏳ [SCHED] Stop")


# Singleton
scheduler = TrinityScheduler()
