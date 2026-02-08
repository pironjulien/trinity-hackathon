"""
JOBS/TRADER/REPORTING/TEMPLATES.PY
==============================================================================
MODULE: REPORT TEMPLATES 📝
PURPOSE: Format trading reports for notifications.
==============================================================================
"""

from typing import Dict
from datetime import datetime

from social.messaging.ascii import (
    create_progress_bar,
    create_separator,
    get_trend_emoji,
)
from social.messaging.i18n import t


def format_report(context: Dict, title: str = "Trading Report") -> str:
    """
    Format a complete trading report (HTML).
    SOTA Design Update.
    """
    lines = [f"<b>🏦 {title.upper()}</b>"]
    lines.append(f"<i>{datetime.now().strftime('%d/%m %H:%M')}</i>")
    lines.append(create_separator(16))

    # Balance section
    cash = context.get("cash", 0)
    exposure = context.get("exposure", 0)
    total = cash + exposure

    exposure_pct = (exposure / total) if total > 0 else 0
    exposure_bar = create_progress_bar(exposure_pct, 10, "BLOCK")

    lines.append(f"📊 <b>{t('trader.portfolio')}</b>")
    lines.append(f"├ {t('trader.cash')}: <code>{cash:.2f}€</code>")
    lines.append(f"├ {t('trader.exposure')}: <code>{exposure:.2f}€</code>")
    lines.append(f"└ <code>[{exposure_bar}] {exposure_pct * 100:.0f}%</code>")
    lines.append("")

    # PnL section
    session_pnl = context.get("session_pnl", 0)
    daily_pnl = context.get("daily_pnl", 0)
    pnl_emoji = get_trend_emoji(daily_pnl)

    lines.append(f"{pnl_emoji} <b>{t('trader.performance')}</b>")
    lines.append(f"├ {t('trader.session')}: <code>{session_pnl:+.2f}€</code>")
    lines.append(f"└ {t('trader.today')}: <code>{daily_pnl:+.2f}€</code>")
    lines.append("")

    # Stats section (Before positions, logic choice)
    wins = context.get("wins", 0)
    losses = context.get("losses", 0)
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    win_bar = create_progress_bar(win_rate / 100, 8, "BLOCK")

    lines.append(f"⚔️ <b>{t('trader.stats')}</b>")
    lines.append(f"├ {t('trader.win_rate')}: <code>{win_rate:.0f}%</code>")
    lines.append(f"├ <code>[{win_bar}]</code>")
    lines.append(f"└ {t('trader.score')}: {wins}W / {losses}L")
    lines.append("")

    # Positions section
    positions = context.get("positions", [])
    if positions:
        lines.append(f"📌 <b>{t('trader.positions')} ({len(positions)})</b>")
        for pos in positions[:5]:  # Max 5
            lines.append(format_position_line(pos))
        if len(positions) > 5:
            lines.append(f"<i>+{len(positions) - 5} {t('trader.more')}</i>")
        lines.append("")

    return "\n".join(lines)


def format_position_line(position: Dict) -> str:
    """Format a single position line for reports."""
    pair = position.get("pair", "???")
    pnl_pct = position.get("pnl_pct", 0)
    # value = position.get("value", 0)

    symbol = "🟢" if pnl_pct > 0 else "🔴"
    if abs(pnl_pct) < 0.005:
        symbol = "⚪"

    asset = pair.split("/")[0] if "/" in pair else pair
    return f"{symbol} {asset}: <code>{pnl_pct * 100:+.2f}%</code>"


def format_trade_notification(
    pair: str,
    side: str,
    price: float,
    amount: float,
    pnl: float = None,
    stop_loss: float = None,
    take_profit: float = None,
) -> str:
    """
    Format a trade execution notification.
    """
    asset = pair.split("/")[0]
    value_eur = price * amount
    sep = create_separator(16)

    if side == "buy":
        emoji = "📥"
        lines = [
            f"{emoji} <b>{t('trader.buy')} {asset}</b>",
            sep,
            f"💵 {t('trader.price')}: <code>{price:.4f}€</code>",
            f"💶 {t('trader.cost')}: <code>{value_eur:.2f}€</code>",
        ]

        if stop_loss:
            risk = abs(price - stop_loss) / price * 100
            lines.append(
                f"🛡️ {t('trader.sl')}: <code>{stop_loss:.4f}€</code> (-{risk:.1f}%)"
            )

        if take_profit:
            gain = abs(take_profit - price) / price * 100
            lines.append(
                f"🎯 {t('trader.tp')}: <code>{take_profit:.4f}€</code> (+{gain:.1f}%)"
            )

    else:
        emoji = "📤"
        pnl_str = f"{pnl:+.2f}€"
        pnl_icon = get_trend_emoji(pnl if pnl else 0)

        lines = [
            f"{emoji} <b>{t('trader.sell')} {asset}</b>",
            sep,
            f"📈 <b>{t('trader.pnl')}: {pnl_icon} {pnl_str}</b>"
            if pnl is not None
            else "",
            f"💵 {t('trader.price')}: <code>{price:.4f}€</code>",
            f"💶 {t('trader.cash')}: <code>{value_eur:.2f}€</code>",
        ]

    return "\n".join(filter(None, lines))


def format_alert(alert_type: str, message: str, details: Dict = None) -> str:
    """
    Format an alert notification.

    Args:
        alert_type: "WARNING", "ERROR", "INFO", "SUCCESS"
        message: Alert message
        details: Optional details dict

    Returns:
        HTML-formatted alert
    """
    emojis = {"WARNING": "⚠️", "ERROR": "🚨", "INFO": "ℹ️", "SUCCESS": "✅"}

    emoji = emojis.get(alert_type, "📢")

    lines = [f"{emoji} <b>{alert_type}</b>"]
    lines.append(message)

    if details:
        for key, value in details.items():
            lines.append(f"├ {key}: <code>{value}</code>")

    return "\n".join(lines)


def humanize_reason(reason: str) -> str:
    """
    Convert technical reason codes to human-readable text.

    Args:
        reason: Technical reason string

    Returns:
        Human-friendly description (translated)
    """
    mappings = {
        "STOP_LOSS": t("trader.reason.stop_loss"),
        "TAKE_PROFIT": t("trader.reason.take_profit"),
        "GOLDEN_RATCHET": t("trader.reason.golden_ratchet"),
        "STAGNANT": t("trader.reason.stagnant"),
        "DUST": t("trader.reason.dust"),
        "CIRCUIT_BREAKER": t("trader.reason.circuit_breaker"),
        "MANUAL": t("trader.reason.manual"),
    }

    for key, value in mappings.items():
        if key in reason:
            return value

    return reason


# Legacy alias
format_complete_report = format_report
