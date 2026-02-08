"""
CORPUS/SOUL/PERSONA.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: PERSONA (GLOBAL DESIGN) 🗣️
PURPOSE: Constantes globales de design et utilitaires.
══════════════════════════════════════════════════════════════════════════════
"""

# ───────────────
# GLOBAL DESIGN
# ───────────────
SEPARATOR = "━━━━━━━━━━━━━━━━"
FOOTER_GOLDEN = '<i>"Gloire au Nombre d\'Or."</i> 🙏'


def clean_json_response(text: str) -> str:
    """Nettoie les balises Markdown ```json d'une Response."""
    if not text:
        return "{}"
    text = text.replace("```json", "").replace("```", "").strip()
    return text
