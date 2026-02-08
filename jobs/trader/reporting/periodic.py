"""
JOBS/TRADER/REPORTING/PERIODIC.PY
==============================================================================
MODULE: PERIODIC REPORT (The Rich One) 📊
PURPOSE: Generate the rich periodic status report (User's favorites).
TARGET: Matches the legacy 'Rapport Trading' format pixel-perfectly.
==============================================================================
"""

from typing import Dict
from datetime import datetime
from social.messaging.ascii import (
    create_progress_bar,
    get_trend_emoji,
)


def format_rich_report(context: Dict) -> str:
    """
    Format the rich 'Real Report' from Kraken.
    SOTA 2026: HTML structuré avec cards et couleurs dynamiques.
    """
    now = datetime.now()
    time_str = now.strftime("%H:%M")

    # Helper pour couleur conditionnelle
    def pnl_class(val):
        if val > 0:
            return "positive"
        elif val < 0:
            return "negative"
        return "neutral"

    def pnl_badge(val):
        if val > 0:
            return '<span class="badge green">🟢</span>'
        elif val < 0:
            return '<span class="badge red">🔴</span>'
        return '<span class="badge yellow">🟡</span>'

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD HTML
    # ══════════════════════════════════════════════════════════════════════════

    html = ['<div class="report">']

    # Header
    html.append(f'<div class="report-header">📊 RAPPORT PERIODIQUE {time_str}</div>')

    # ─────────────────────────────────────────────────────────────────────────
    # 1. État du Marché
    # ─────────────────────────────────────────────────────────────────────────
    regime = context.get("regime", "NEUTRE")
    regime_badge = {"BULL": "green", "BEAR": "red"}.get(regime, "yellow")
    regime_icon = {"BULL": "🟢", "BEAR": "🔴"}.get(regime, "🟡")

    btc_24h = context.get("btc_24h", 0.0)
    sentiment = context.get("sentiment", 50)
    sent_bar = create_progress_bar(sentiment / 100, 8, "BLOCK")

    html.append('<div class="report-section">')
    html.append('<div class="report-section-title">☀️ État du Marché</div>')
    html.append(
        f'<div class="report-row"><span class="label">Régime</span><span class="value">{regime} <span class="badge {regime_badge}">{regime_icon}</span></span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">BTC 24h</span><span class="value {pnl_class(btc_24h)}">{btc_24h:+.2f}%</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Sentiment</span><span class="value"><code>[{sent_bar}]</code> {sentiment}</span></div>'
    )

    if context.get("market_reason"):
        html.append(
            f'<div class="report-row"><span class="label">💬</span><span class="value" style="font-style:italic;opacity:0.7">{context["market_reason"]}</span></div>'
        )

    html.append("</div>")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Stratégie Active
    # ─────────────────────────────────────────────────────────────────────────
    raw_mode = context.get("mode", "IA")
    submode = context.get("submode", "STANDARD").upper()
    cycle = context.get("cycle", 0)

    # SOTA 2026: Parse mode intelligemment (peut contenir emoji ou être brut)
    is_ai_mode = "IA" in str(raw_mode).upper() or "🤖" in str(raw_mode)
    mode_display = "IA GEMINI" if is_ai_mode else "MANUEL"
    mode_icon = "🤖" if is_ai_mode else "👤"

    # Stratégie = config.mode (sniper/mitraillette), évite redondance
    # SOTA 2026: Si mode=IA, lire la stratégie active depuis l'optimizer
    level_display = "NORMAL"
    if submode in ("IA", "MANUEL"):
        # Mode IA: lire la vraie stratégie depuis l'optimizer
        try:
            from jobs.trader.config import MEMORIES_DIR
            from corpus.soma.cells import load_json

            active_config = load_json(
                MEMORIES_DIR / "trader" / "active_config.json", default={}
            )
            active_mode = active_config.get("active_mode", "").upper()
            if active_mode in ("SNIPER", "MITRAILLETTE"):
                strategy_display = active_mode
            else:
                strategy_display = "AUTO"
            # SOTA 2026: Extract Level (Standard 362.102)
            raw_variation = active_config.get("active_variation", "DEFAULT").upper()
            level_display = {
                "LOW": "PASSIF",
                "DEFAULT": "NORMAL",
                "HIGH": "AGRESSIF",
            }.get(raw_variation, "NORMAL")
        except Exception:
            strategy_display = "AUTO"
    else:
        strategy_display = submode
        # Read level from context for manual mode
        raw_level = context.get("level", 1)
        level_display = {0: "PASSIF", 1: "NORMAL", 2: "AGRESSIF"}.get(
            raw_level, "NORMAL"
        )

    strategy_icons = {
        "SNIPER": "🎯",
        "MITRAILLETTE": "⚡",
        "AUTO": "🧠",
        "STANDARD": "⚙️",
    }
    strat_icon = strategy_icons.get(strategy_display, "⚙️")

    html.append('<div class="report-section">')
    html.append('<div class="report-section-title">🛡️ Stratégie Active</div>')
    html.append(
        f'<div class="report-row"><span class="label">Mode</span><span class="value">{mode_icon} {mode_display}</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Stratégie</span><span class="value">{strat_icon} {strategy_display}</span></div>'
    )
    # SOTA 2026: Display Level (Standard 362.102)
    level_icons = {"PASSIF": "🛡️", "NORMAL": "⚖️", "AGRESSIF": "🔥"}
    level_icon = level_icons.get(level_display, "⚖️")
    html.append(
        f'<div class="report-row"><span class="label">Level</span><span class="value">{level_icon} {level_display}</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Cycle</span><span class="value">#{cycle}</span></div>'
    )
    html.append("</div>")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Portefeuille
    # ─────────────────────────────────────────────────────────────────────────
    total = context.get("total_capital", 0.0)
    actif = context.get("capital_actif", 0.0)
    cash = context.get("cash", 0.0)
    pos_val = context.get("positions_value", 0.0)

    html.append('<div class="report-section">')
    html.append('<div class="report-section-title">💼 Portefeuille</div>')
    html.append(
        f'<div class="report-row"><span class="label">Capital Total</span><span class="value">{total:.2f}€ 🏦</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Capital Actif</span><span class="value">{actif:.2f}€</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label" style="padding-left:12px">└ Cash</span><span class="value">{cash:.2f}€</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label" style="padding-left:12px">└ Positions</span><span class="value">{pos_val:.2f}€ {pnl_badge(pos_val)}</span></div>'
    )

    # Positions individuelles
    positions = context.get("positions_list", [])
    for pos in positions:
        pair = pos.get("pair", "UNKNOWN").split("/")[0]
        val = pos.get("value", 0.0)
        pnl = pos.get("pnl_pct", 0.0)
        icon = get_trend_emoji(pnl, 0.005)
        html.append(
            f'<div class="report-row"><span class="label" style="padding-left:24px">{icon} {pair}</span><span class="value {pnl_class(pnl)}">{val:.2f}€ ({pnl * 100:+.2f}%)</span></div>'
        )

    html.append("</div>")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Réserve Sacrée (Bitcoin)
    # ─────────────────────────────────────────────────────────────────────────
    btc_total = context.get("btc_total", 0.0)
    btc_earn = context.get("btc_earn", 0.0)
    btc_val = context.get("btc_value", 0.0)
    cagnotte = context.get("cagnotte", 0.0)
    cagnotte_pct = min(1.0, cagnotte / 5.0)
    circles = create_progress_bar(cagnotte_pct, 5, "CIRCLE")

    html.append('<div class="report-section">')
    html.append('<div class="report-section-title">🟠 Réserve Bitcoin</div>')
    html.append(
        f'<div class="report-row"><span class="label">Total</span><span class="value">{btc_total:.8f} BTC</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Earn</span><span class="value">{btc_earn:.8f} BTC</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Valeur</span><span class="value">{btc_val:.2f}€ 🔒</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Tirelire</span><span class="value">{circles} {cagnotte:.2f}€</span></div>'
    )
    html.append("</div>")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Historique de Combat
    # ─────────────────────────────────────────────────────────────────────────
    win_rate = context.get("win_rate_session", 0.0)
    wins = context.get("wins", 0)
    losses = context.get("losses", 0)
    total_trades = wins + losses
    win_bar = create_progress_bar(
        wins / total_trades if total_trades > 0 else 0, 8, "BLOCK"
    )

    pnl_daily = context.get("pnl_daily", 0.0)
    pnl_session = context.get("pnl_session", 0.0)

    html.append('<div class="report-section">')
    html.append('<div class="report-section-title">⚔️ Combat</div>')
    html.append(
        f'<div class="report-row"><span class="label">Win Rate</span><span class="value"><code>[{win_bar}]</code> {win_rate:.1f}%</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">PnL 24h</span><span class="value {pnl_class(pnl_daily)}">{pnl_daily:+.2f}€ {pnl_badge(pnl_daily)}</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">PnL Global</span><span class="value {pnl_class(pnl_session)}">{pnl_session:+.2f}€ {pnl_badge(pnl_session)}</span></div>'
    )
    html.append(
        f'<div class="report-row"><span class="label">Score</span><span class="value">{wins}W - {losses}L</span></div>'
    )
    html.append("</div>")

    # Footer
    html.append(
        '<div style="text-align:center;margin-top:8px;opacity:0.6;font-style:italic;font-size:11px">"Gloire au Nombre d\'Or." 🙏</div>'
    )

    html.append("</div>")

    return "".join(html)
