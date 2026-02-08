"""
SOCIAL/MESSAGING/NOTIFICATION_TEMPLATES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: RICH NOTIFICATION TEMPLATES (SOTA 2026)
PURPOSE: Modern HTML/CSS templates for Phone Widget notifications.
         Supports dual-output: Rich HTML for Phone, Plain text for fallback.
STANDARD: 362 (Dual-Channel Notifications)
══════════════════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


# ════════════════════════════════════════════════════════════════════════════
# ENUMS & TYPES
# ════════════════════════════════════════════════════════════════════════════


class TradeSide(Enum):
    BUY = "buy"
    SELL = "sell"


class TraderMode(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class NerveLevel(Enum):
    URGENT = "urgent"
    PAIN = "pain"
    PLEASURE = "pleasure"
    NEUTRAL = "neutral"


# ════════════════════════════════════════════════════════════════════════════
# CSS VARIABLES (INLINE STYLES)
# ════════════════════════════════════════════════════════════════════════════


COLORS = {
    "buy": "#00ff88",
    "sell": "#ff4477",
    "btc": "#f7931a",
    "profit": "#00ff88",
    "loss": "#ff4477",
    "neutral": "#888888",
    "conservative": "#3b82f6",
    "balanced": "#a855f7",
    "aggressive": "#ef4444",
    "glass_bg": "rgba(255, 255, 255, 0.05)",
    "glass_border": "rgba(255, 255, 255, 0.1)",
    "text_primary": "#ffffff",
    "text_secondary": "rgba(255, 255, 255, 0.7)",
    "text_muted": "rgba(255, 255, 255, 0.5)",
}

STYLES = {
    "card": f"""
        background: {COLORS["glass_bg"]};
        border: 1px solid {COLORS["glass_border"]};
        border-radius: 12px;
        padding: 16px;
        backdrop-filter: blur(10px);
    """,
    "badge": """
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    """,
    "value_large": """
        font-size: 24px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    """,
    "value_mono": """
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
    """,
    "label": f"""
        font-size: 11px;
        color: {COLORS["text_muted"]};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    """,
    "row": """
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 8px 0;
    """,
    "progress_track": f"""
        height: 6px;
        background: {COLORS["glass_border"]};
        border-radius: 3px;
        overflow: hidden;
        margin: 8px 0;
    """,
}


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATE FUNCTIONS: TRADER
# ════════════════════════════════════════════════════════════════════════════


@dataclass
class TradeData:
    """Data for a trade notification."""

    pair: str
    side: TradeSide
    price: float
    amount: float
    cost: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: Optional[str] = None


def render_trade_notification(trade: TradeData) -> Dict[str, str]:
    """
    Render a trade notification in both rich HTML and plain text.

    Returns:
        {"html": str, "plain": str}
    """
    asset = trade.pair.split("/")[0] if "/" in trade.pair else trade.pair
    is_buy = trade.side == TradeSide.BUY

    # Colors
    side_color = COLORS["buy"] if is_buy else COLORS["sell"]
    side_label = "ACHAT" if is_buy else "VENTE"
    side_icon = "📥" if is_buy else "📤"

    # HTML Version
    html_parts = [
        f'<div style="{STYLES["card"].strip()}">',
        # Header with badge
        f'<div style="{STYLES["row"].strip()}">',
        f'<span style="{STYLES["badge"].strip()} background: {side_color}20; color: {side_color}; border: 1px solid {side_color}40;">{side_label}</span>',
        f'<span style="font-size: 20px;">{asset}</span>',
        "</div>",
        # Price
        '<div style="margin: 16px 0; text-align: center;">',
        f'<div style="{STYLES["label"].strip()}">Prix</div>',
        f'<div style="{STYLES["value_large"].strip()} color: {COLORS["text_primary"]};">{trade.price:.4f}€</div>',
        "</div>",
    ]

    # Cost/Value
    html_parts.append(f'<div style="{STYLES["row"].strip()}">')
    html_parts.append(
        f'<span style="{STYLES["label"].strip()}">{"Coût" if is_buy else "Valeur"}</span>'
    )
    html_parts.append(
        f'<span style="{STYLES["value_mono"].strip()}">{trade.cost:.2f}€</span>'
    )
    html_parts.append("</div>")

    # PnL for sells
    if not is_buy and trade.pnl is not None:
        pnl_color = COLORS["profit"] if trade.pnl >= 0 else COLORS["loss"]
        pnl_sign = "+" if trade.pnl >= 0 else ""
        html_parts.append(f'<div style="{STYLES["row"].strip()}">')
        html_parts.append(f'<span style="{STYLES["label"].strip()}">P/L</span>')
        html_parts.append(
            f'<span style="{STYLES["value_mono"].strip()} color: {pnl_color}; font-weight: 700;">'
            f"{pnl_sign}{trade.pnl:.2f}€"
        )
        if trade.pnl_pct is not None:
            html_parts.append(f" ({pnl_sign}{trade.pnl_pct:.1f}%)")
        html_parts.append("</span>")
        html_parts.append("</div>")

    # SL/TP for buys
    if is_buy:
        if trade.stop_loss:
            sl_pct = abs(trade.price - trade.stop_loss) / trade.price * 100
            html_parts.append(f'<div style="{STYLES["row"].strip()}">')
            html_parts.append(
                f'<span style="{STYLES["label"].strip()}">🛡️ Stop Loss</span>'
            )
            html_parts.append(
                f'<span style="{STYLES["value_mono"].strip()} color: {COLORS["loss"]};">'
                f"{trade.stop_loss:.4f}€ (-{sl_pct:.1f}%)</span>"
            )
            html_parts.append("</div>")

        if trade.take_profit:
            tp_pct = abs(trade.take_profit - trade.price) / trade.price * 100
            html_parts.append(f'<div style="{STYLES["row"].strip()}">')
            html_parts.append(
                f'<span style="{STYLES["label"].strip()}">🎯 Take Profit</span>'
            )
            html_parts.append(
                f'<span style="{STYLES["value_mono"].strip()} color: {COLORS["profit"]};">'
                f"{trade.take_profit:.4f}€ (+{tp_pct:.1f}%)</span>"
            )
            html_parts.append("</div>")

    # Reason for sells
    if not is_buy and trade.reason:
        html_parts.append(
            f'<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid {COLORS["glass_border"]}; '
            f'font-size: 12px; color: {COLORS["text_secondary"]};">'
            f"{trade.reason}</div>"
        )

    html_parts.append("</div>")

    # Plain text version (notification compatible)
    plain_parts = [f"{side_icon} {side_label} {asset}"]
    plain_parts.append("─" * 16)
    plain_parts.append(f"💵 Prix: {trade.price:.4f}€")
    plain_parts.append(f"💶 {'Coût' if is_buy else 'Valeur'}: {trade.cost:.2f}€")

    if not is_buy and trade.pnl is not None:
        pnl_icon = "📈" if trade.pnl >= 0 else "📉"
        plain_parts.append(f"{pnl_icon} P/L: {trade.pnl:+.2f}€")

    if is_buy and trade.stop_loss:
        plain_parts.append(f"🛡️ SL: {trade.stop_loss:.4f}€")
    if is_buy and trade.take_profit:
        plain_parts.append(f"🎯 TP: {trade.take_profit:.4f}€")

    if not is_buy and trade.reason:
        plain_parts.append(f"\n{trade.reason}")

    return {"html": "".join(html_parts), "plain": "\n".join(plain_parts)}


def render_mutation_notification(
    old_mode: TraderMode, new_mode: TraderMode, reason: str = ""
) -> Dict[str, str]:
    """
    Render a strategic mutation notification.

    Returns:
        {"html": str, "plain": str}
    """
    old_color = COLORS.get(old_mode.value, COLORS["neutral"])
    new_color = COLORS.get(new_mode.value, COLORS["neutral"])

    html = f"""
    <div style="{STYLES["card"].strip()}">
        <div style="text-align: center; margin-bottom: 16px;">
            <span style="font-size: 28px;">🧬</span>
            <div style="font-size: 14px; font-weight: 700; margin-top: 8px; letter-spacing: 0.1em;">
                MUTATION STRATÉGIQUE
            </div>
        </div>
        <div style="{STYLES["row"].strip()} gap: 12px; justify-content: center;">
            <span style="{STYLES["badge"].strip()} background: {old_color}20; color: {old_color}; border: 1px solid {old_color}40;">
                {old_mode.value.upper()}
            </span>
            <span style="font-size: 18px; color: {COLORS["text_muted"]};">→</span>
            <span style="{STYLES["badge"].strip()} background: {new_color}20; color: {new_color}; border: 1px solid {new_color}40;">
                {new_mode.value.upper()}
            </span>
        </div>
        <div style="margin-top: 16px; font-size: 12px; color: {COLORS["text_secondary"]}; text-align: center;">
            Optimisation validée par l'IA
        </div>
    </div>
    """

    plain = (
        f"🧬 MUTATION STRATÉGIQUE\n"
        f"Mode: {old_mode.value.upper()} → {new_mode.value.upper()}\n"
        f"Optimisation validée par l'IA."
    )

    return {"html": html.strip(), "plain": plain}


def render_sacred_acquisition(
    amount_eur: float, btc_amount: float, btc_price: float
) -> Dict[str, str]:
    """
    Render a sacred BTC acquisition notification.

    Returns:
        {"html": str, "plain": str}
    """
    html = f"""
    <div style="{STYLES["card"].strip()} border-color: {COLORS["btc"]}40;">
        <div style="text-align: center;">
            <div style="font-size: 36px; margin-bottom: 8px;">₿</div>
            <div style="font-size: 14px; font-weight: 700; color: {COLORS["btc"]}; letter-spacing: 0.1em;">
                ACQUISITION SACRÉE
            </div>
        </div>
        <div style="margin: 20px 0; text-align: center;">
            <div style="{STYLES["label"].strip()}">Cagnotte atteinte</div>
            <div style="{STYLES["value_large"].strip()} color: {COLORS["profit"]};">{amount_eur:.2f}€</div>
        </div>
        <div style="{STYLES["row"].strip()}">
            <span style="{STYLES["label"].strip()}">Acheté</span>
            <span style="{STYLES["value_mono"].strip()} color: {COLORS["btc"]}; font-weight: 700;">
                {btc_amount:.6f} BTC
            </span>
        </div>
        <div style="{STYLES["row"].strip()}">
            <span style="{STYLES["label"].strip()}">Prix</span>
            <span style="{STYLES["value_mono"].strip()}">{btc_price:.2f}€</span>
        </div>
    </div>
    """

    plain = (
        f"🐷 ACQUISITION SACRÉE\n"
        f"Cagnotte atteinte: {amount_eur:.2f}€\n"
        f"Acheté: {btc_amount:.6f} BTC\n"
        f"Prix: {btc_price:.2f}€"
    )

    return {"html": html.strip(), "plain": plain}


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATE FUNCTIONS: SCHEDULER (LIFECYCLE)
# ════════════════════════════════════════════════════════════════════════════


def render_lifecycle_event(
    event_type: str, energy: Optional[int] = None, message: str = ""
) -> Dict[str, str]:
    """
    Render a lifecycle event (boot, morning, noon, night).

    Args:
        event_type: "boot", "morning", "noon", "night"
        energy: Optional energy level (0-100)
        message: Optional custom message

    Returns:
        {"html": str, "plain": str}
    """
    themes = {
        "boot": {"icon": "🚀", "label": "SYSTÈME EN LIGNE", "color": "#00ff88"},
        "morning": {"icon": "☀️", "label": "BONJOUR", "color": "#ffcc00"},
        "noon": {"icon": "🌤️", "label": "POINT MIDI", "color": "#ff9500"},
        "night": {"icon": "🌙", "label": "BONNE NUIT", "color": "#8855ff"},
    }

    theme = themes.get(event_type, themes["boot"])

    energy_bar = ""
    if energy is not None:
        bar_color = COLORS["profit"] if energy > 50 else COLORS["loss"]
        energy_bar = f"""
        <div style="margin-top: 16px;">
            <div style="{STYLES["label"].strip()}">Énergie</div>
            <div style="{STYLES["progress_track"].strip()}">
                <div style="width: {energy}%; height: 100%; background: {bar_color}; border-radius: 3px;"></div>
            </div>
            <div style="text-align: right; {STYLES["value_mono"].strip()}">{energy}%</div>
        </div>
        """

    html = f"""
    <div style="{STYLES["card"].strip()} border-color: {theme["color"]}40;">
        <div style="text-align: center;">
            <div style="font-size: 32px; margin-bottom: 8px;">{theme["icon"]}</div>
            <div style="font-size: 14px; font-weight: 700; color: {theme["color"]}; letter-spacing: 0.1em;">
                {theme["label"]}
            </div>
            {f'<div style="margin-top: 12px; font-size: 13px; color: {COLORS["text_secondary"]};">{message}</div>' if message else ""}
        </div>
        {energy_bar}
    </div>
    """

    plain_parts = [f"{theme['icon']} {theme['label']}"]
    if message:
        plain_parts.append(message)
    if energy is not None:
        plain_parts.append(f"Énergie: {energy}%")

    return {"html": html.strip(), "plain": "\n".join(plain_parts)}


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATE FUNCTIONS: NERVE (URGENT SIGNALS)
# ════════════════════════════════════════════════════════════════════════════


def render_nerve_signal(
    level: NerveLevel, message: str, signal_type: str = ""
) -> Dict[str, str]:
    """
    Render a nerve signal notification.

    Args:
        level: Signal urgency level
        message: Signal message
        signal_type: Optional signal type identifier

    Returns:
        {"html": str, "plain": str}
    """
    level_themes = {
        NerveLevel.URGENT: {"color": "#ff0055", "icon": "🚨", "pulse": True},
        NerveLevel.PAIN: {"color": "#ff4444", "icon": "⚠️", "pulse": False},
        NerveLevel.PLEASURE: {"color": "#00ff88", "icon": "✨", "pulse": False},
        NerveLevel.NEUTRAL: {"color": "#888888", "icon": "📡", "pulse": False},
    }

    theme = level_themes.get(level, level_themes[NerveLevel.NEUTRAL])

    # Pulsing animation for urgent
    pulse_style = ""
    if theme["pulse"]:
        pulse_style = (
            f"box-shadow: 0 0 0 0 {theme['color']}40; animation: pulse 1.5s infinite;"
        )

    html = f"""
    <div style="{STYLES["card"].strip()} border-color: {theme["color"]}; {pulse_style}">
        <div style="{STYLES["row"].strip()}">
            <span style="font-size: 20px;">{theme["icon"]}</span>
            <span style="{STYLES["badge"].strip()} background: {theme["color"]}20; color: {theme["color"]}; border: 1px solid {theme["color"]};">
                {level.value.upper()}
            </span>
        </div>
        <div style="margin-top: 12px; font-size: 14px; line-height: 1.5;">
            {message}
        </div>
        {f'<div style="margin-top: 8px; font-size: 11px; color: {COLORS["text_muted"]};">{signal_type}</div>' if signal_type else ""}
    </div>
    """

    plain = f"{theme['icon']} [{level.value.upper()}] {message}"
    if signal_type:
        plain += f"\nType: {signal_type}"

    return {"html": html.strip(), "plain": plain}


# ════════════════════════════════════════════════════════════════════════════
# TEMPLATE FUNCTIONS: INFLUENCER (PROPOSALS)
# ════════════════════════════════════════════════════════════════════════════


def render_proposal(module: str, content_preview: str, item_id: str) -> Dict[str, str]:
    """
    Render an influencer proposal notification.

    Args:
        module: Module name (e.g., "Twitter", "TikTok")
        content_preview: Preview of the proposed content
        item_id: Item identifier for actions

    Returns:
        {"html": str, "plain": str}
    """
    html = f"""
    <div style="{STYLES["card"].strip()}">
        <div style="{STYLES["row"].strip()}">
            <span style="font-size: 16px; font-weight: 700;">📝 Proposition</span>
            <span style="{STYLES["badge"].strip()} background: rgba(168, 85, 247, 0.2); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.4);">
                {module}
            </span>
        </div>
        <div style="margin: 16px 0; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 13px; line-height: 1.5; color: {COLORS["text_secondary"]};">
            {content_preview}
        </div>
        <div style="font-size: 11px; color: {COLORS["text_muted"]};">
            ID: {item_id}
        </div>
    </div>
    """

    plain = f"📝 Proposition [{module}]\n\n{content_preview}\n\nID: {item_id}"

    return {"html": html.strip(), "plain": plain}
