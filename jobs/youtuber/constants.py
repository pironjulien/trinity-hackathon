"""
JOBS/YOUTUBER/CONSTANTS.PY
Single Source of Truth pour les constantes partagées.
"""
import os
from corpus.dna.genome import MEMORIES_DIR

BANNERS = {
    "fr": ("TRINITY", "L'IA qui pense librement"),
    "en": ("TRINITY", "The free-thinking AI"),
}

# Configuration OAuth
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

SECRETS_DIR = MEMORIES_DIR / "youtuber" / "data"

# Multi-channel config - utilise les tokens existants dans .env
CHANNELS = {
    "en": {
        "name": "Trinity AI",
        "token_env": "YOUTUBE_TOKEN_EN",  # Chaîne principale EN
        "token_file": "token_en.json",
    },
    "fr": {
        "name": "Trinity IA",
        "token_env": "YOUTUBE_TOKEN_FR",  # Chaîne FR
        "token_file": "token_fr.json",
    },
}
