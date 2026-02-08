# avatar/ascii.py
# ═══════════════════════════════════════════════════════════════════════════════
"""
MODULE: ASCII VISUALS 📊
PURPOSE: Générer des mini-graphiques textuels pour les rapports.
SOURCE: Legacy 'communication/reports/charting.py'.
"""

from typing import List


def generate_mini_chart(prices: List[float], width: int = 12) -> str:
    """
    Generates un mini graphique ASCII (Sparkline).
    Example: ▅▇█▇▆▅
    """
    if not prices or len(prices) < 2:
        return "─" * width

    # Prendre les dernières valeurs
    values = prices[-width:] if len(prices) > width else prices

    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val

    if range_val == 0:
        return "─" * len(values)

    # Unicode Block Elements (Level 1 to 8)
    blocks = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    chart = ""
    for v in values:
        normalized = (v - min_val) / range_val
        idx = min(7, int(normalized * 8))
        chart += blocks[idx]

    return chart


def create_progress_bar(percent: float, width: int = 10, style: str = "BLOCK") -> str:
    """
    Generate a text-based progress bar.

    Args:
        percent: 0.0 to 1.0 (or 0-100, handled automatically)
        width: Number of characters
        style: 'BLOCK' (▓░), 'CIRCLE' (⚫⚪), 'LINE' (━─)

    Returns:
        Progress bar string
    """
    if percent > 1.0:
        percent /= 100.0
    percent = max(0.0, min(1.0, percent))

    filled = int(width * percent)
    empty = width - filled

    if style == "CIRCLE":
        fill_char = "⚫"  # or 🟡
        empty_char = "⚪"
    elif style == "LINE":
        fill_char = "━"
        empty_char = "─"
    else:  # BLOCK
        fill_char = "▓"
        empty_char = "░"

    return f"{fill_char * filled}{empty_char * empty}"


def create_separator(width: int = 20, style: str = "THICK") -> str:
    """Create a visual separator line."""
    if style == "THICK":
        return "━" * width
    return "─" * width


def get_trend_emoji(value: float, neutral_threshold: float = 0.0) -> str:
    """Get emoji based on value direction."""
    if value > neutral_threshold:
        return "🟢"  # or 📈
    elif value < -neutral_threshold:
        return "🔴"  # or 📉
    return "⚪"
