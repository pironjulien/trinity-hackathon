"""
SOCIAL/MESSAGING/I18N.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: INTERNATIONALISATION (FR/EN) 🌍
PURPOSE: Centralizes all Messaging messages with multilingual support.
         Language is configurable via config.json.
══════════════════════════════════════════════════════════════════════════════
"""

from loguru import logger

# ════════════════════════════════════════════════════════════════════════════
# TRANSLATIONS DICTIONARY
# PHI: Organized by functional domain for clarity
# ════════════════════════════════════════════════════════════════════════════

TRANSLATIONS = {
    "fr": {
        # ════════════════════════════════════════════════════════════════════
        # LIFECYCLE MESSAGES
        # ════════════════════════════════════════════════════════════════════
        "sleep_mode": "💤 Trinity s'endort... À bientôt !",
        "wakeup": "☀️ Bonjour. Systèmes pleinement actifs.",
        "night_mode": "🌙 Bonne nuit. Mode veille activé.",
        "noon_check": "☀️ Point midi. Énergie: {energy}. Cycles alignés.",
        # ════════════════════════════════════════════════════════════════════
        # SCHEDULER
        # ════════════════════════════════════════════════════════════════════
        "scheduler.job_report": "📋 **Rapport Job**\n{report}",
        "scheduler.evolution_error": "🌅 Erreur Evolution: {error}",
        "scheduler.evolution_critical": "🌅 Erreur Critique Evolution: {error}",
        "scheduler.night_dream": "🌙 Bonne nuit. Mode veille activé.\n\n💭 _{dream}_",
        "scheduler.periodic_report": "📊 {report}",
        # ════════════════════════════════════════════════════════════════════
        # BOOT SEQUENCE
        # ════════════════════════════════════════════════════════════════════
        "boot.pere_less_1h": "il y a moins d'1h",
        "boot.pere_hours": "il y a {hours}h",
        "boot.pere_days": "il y a {days} jour(s)",
        "boot.pere_recently": "récemment",
        "boot.pere_unknown": "inconnu",
        "boot.temporal": "Dernière conversation avec Père: {pere_ago} | Uptime serveur: {uptime}",
        "boot.no_jobs": "Aucun job actif",
        "boot.active_jobs": "Jobs actifs: {jobs}",
        "boot.dream_consolidated": "Consolidé {count} mémoires",
        "boot.dream_silent": "Rêve silencieux...",
        # ════════════════════════════════════════════════════════════════════
        # TRADER TEMPLATES
        # ════════════════════════════════════════════════════════════════════
        "trader.buy": "ACHAT",
        "trader.sell": "VENTE",
        "trader.price": "Prix",
        "trader.cost": "Coût",
        "trader.cash": "Cash",
        "trader.sl": "SL",
        "trader.tp": "TP",
        "trader.pnl": "P/L",
        "trader.portfolio": "Portfolio",
        "trader.exposure": "Exp.",
        "trader.performance": "Performance",
        "trader.session": "Session",
        "trader.today": "Aujourd'hui",
        "trader.stats": "Stats",
        "trader.win_rate": "Taux de réussite",
        "trader.score": "Score",
        "trader.positions": "Positions",
        "trader.more": "de plus...",
        "trader.sacred_acquisition": "ACQUISITION SACRÉE",
        "trader.cagnotte_reached": "Cagnotte atteinte {amount}€.",
        "trader.bought_btc": "Acheté",
        "trader.reason.stop_loss": "🛑 Stop Loss atteint",
        "trader.reason.take_profit": "🎯 Take Profit atteint",
        "trader.reason.golden_ratchet": "🥇 Golden Ratchet (trailing stop)",
        "trader.reason.stagnant": "⏰ Position stagnante",
        "trader.reason.dust": "🧹 Position dust (trop petite)",
        "trader.reason.circuit_breaker": "🚨 Circuit breaker activé",
        "trader.reason.manual": "👤 Vente manuelle",
    },
    "en": {
        # ════════════════════════════════════════════════════════════════════
        # LIFECYCLE MESSAGES
        # ════════════════════════════════════════════════════════════════════
        "sleep_mode": "💤 Trinity going to sleep... See you soon!",
        "wakeup": "☀️ Good Morning. Systems fully active.",
        "night_mode": "🌙 Good Night. Standby Mode.",
        "noon_check": "☀️ Noon Check. Energy: {energy}. Cycles aligned.",
        # ════════════════════════════════════════════════════════════════════
        # SCHEDULER
        # ════════════════════════════════════════════════════════════════════
        "scheduler.job_report": "📋 **Job Report**\n{report}",
        "scheduler.evolution_error": "🌅 Evolution Error: {error}",
        "scheduler.evolution_critical": "🌅 Critical Evolution Error: {error}",
        "scheduler.night_dream": "🌙 Good Night. Standby Mode.\n\n💭 _{dream}_",
        "scheduler.periodic_report": "📊 {report}",
        # ════════════════════════════════════════════════════════════════════
        # BOOT SEQUENCE
        # ════════════════════════════════════════════════════════════════════
        "boot.pere_less_1h": "less than 1h ago",
        "boot.pere_hours": "{hours}h ago",
        "boot.pere_days": "{days} day(s) ago",
        "boot.pere_recently": "recently",
        "boot.pere_unknown": "unknown",
        "boot.temporal": "Last conversation with Father: {pere_ago} | Server uptime: {uptime}",
        "boot.no_jobs": "No active jobs",
        "boot.active_jobs": "Active jobs: {jobs}",
        "boot.dream_consolidated": "Consolidated {count} memories",
        "boot.dream_silent": "Silent dream...",
        # ════════════════════════════════════════════════════════════════════
        # TRADER TEMPLATES
        # ════════════════════════════════════════════════════════════════════
        "trader.buy": "BUY",
        "trader.sell": "SELL",
        "trader.price": "Price",
        "trader.cost": "Cost",
        "trader.cash": "Cash",
        "trader.sl": "SL",
        "trader.tp": "TP",
        "trader.pnl": "P/L",
        "trader.portfolio": "Portfolio",
        "trader.exposure": "Exp.",
        "trader.performance": "Performance",
        "trader.session": "Session",
        "trader.today": "Today",
        "trader.stats": "Stats",
        "trader.win_rate": "Win Rate",
        "trader.score": "Score",
        "trader.positions": "Positions",
        "trader.more": "more...",
        "trader.sacred_acquisition": "SACRED ACQUISITION",
        "trader.cagnotte_reached": "Cagnotte reached {amount}€.",
        "trader.bought_btc": "Bought",
        "trader.reason.stop_loss": "🛑 Stop Loss triggered",
        "trader.reason.take_profit": "🎯 Take Profit reached",
        "trader.reason.golden_ratchet": "🥇 Golden Ratchet (trailing stop)",
        "trader.reason.stagnant": "⏰ Stagnant position",
        "trader.reason.dust": "🧹 Dust position (too small)",
        "trader.reason.circuit_breaker": "🚨 Circuit breaker activated",
        "trader.reason.manual": "👤 Manual sale",
    },
}


# ════════════════════════════════════════════════════════════════════════════
# LANGUAGE MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════


def _get_language() -> str:
    """Get current language from config.json. Defaults to 'en'."""
    try:
        from corpus.soma.cells import load_json
        from corpus.dna.genome import MEMORIES_DIR

        config = load_json(MEMORIES_DIR / "trinity" / "config.json", default={})
        return config.get("language", "en")  # SOTA 2026: EN by default
    except Exception as e:
        logger.debug(f"🌍 [I18N] Config load failed, defaulting to EN: {e}")
        return "en"


def t(key: str, **kwargs) -> str:
    """
    Get translated string for key.

    Args:
        key: Translation key (e.g., "sleep_mode", "wakeup")
        **kwargs: Format arguments (e.g., energy="85%", error="timeout")

    Returns:
        Translated string with placeholders replaced

    Example:
        t("noon_check", energy="85%")  → "☀️ Point midi. Énergie: 85%. Cycles alignés."
    """
    lang = _get_language()

    # Try current language first
    translations = TRANSLATIONS.get(lang, {})
    text = translations.get(key)

    # Fallback to English
    if text is None:
        text = TRANSLATIONS.get("en", {}).get(key)

    # Fallback to key itself
    if text is None:
        logger.warning(f"🌍 [I18N] Missing translation: {key}")
        return key

    # Apply format arguments
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"🌍 [I18N] Missing format arg for {key}: {e}")

    return text


def get_language() -> str:
    """Get current language code."""
    return _get_language()


def get_available_languages() -> list:
    """Get list of available language codes."""
    return list(TRANSLATIONS.keys())
