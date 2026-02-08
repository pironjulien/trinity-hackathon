"""
CORPUS/BRAIN/LIMBIC.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: LIMBIC SYSTEM (LES ÉMOTIONS) 💖
PURPOSE: Gère les états émotionnels et les Responses affectives.
      Migré et consolidé depuis TrinityOld (limbic_system + hormones).
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger


@dataclass
class EmotionalState:
    """Un état émotionnel avec intensité et durée."""

    name: str
    intensity: float  # 0.0 à 1.0
    triggered_at: datetime
    trigger: str  # Ce qui a déclenché l'émotion


class LimbicSystem:
    """
    Le Système Limbique de Trinity.
    Gère les émotions et influence les comportements.
    """

    def __init__(self):
        self.current_emotions: Dict[str, EmotionalState] = {}
        self.baseline_mood: str = "neutral"
        self.emotional_memory: list = []  # Historique des émotions

        # Seuils de Response émotionnelle
        self.thresholds = {
            "joy": 0.3,
            "frustration": 0.5,
            "curiosity": 0.2,
            "concern": 0.4,
            "satisfaction": 0.3,
        }

    def trigger_emotion(self, emotion: str, intensity: float, trigger: str):
        """Déclenche une émotion."""
        state = EmotionalState(
            name=emotion,
            intensity=min(1.0, max(0.0, intensity)),
            triggered_at=datetime.now(),
            trigger=trigger,
        )

        self.current_emotions[emotion] = state
        self.emotional_memory.append(state)

        # Garder seulement les 100 dernières émotions
        if len(self.emotional_memory) > 100:
            self.emotional_memory = self.emotional_memory[-100:]

        logger.debug(
            f"💖 [LIMBIC] Emotion triggered: {emotion} ({intensity:.2f}) - {trigger}"
        )

    def get_emotional_state(self) -> Dict:
        """Returns l'état émotionnel actuel."""
        # Nettoyer les émotions expirées (>1 heure)
        now = datetime.now()
        active = {}

        for name, state in self.current_emotions.items():
            if now - state.triggered_at < timedelta(hours=1):
                # Décroissance progressive
                elapsed_minutes = (now - state.triggered_at).total_seconds() / 60
                decay = max(0.0, 1.0 - (elapsed_minutes / 60))
                active[name] = state.intensity * decay

        return active

    def get_dominant_emotion(self) -> Optional[str]:
        """Returns l'émotion dominante actuelle."""
        states = self.get_emotional_state()
        if not states:
            return self.baseline_mood
        return max(states.keys(), key=lambda k: states.get(k, 0.0))

    def get_emotional_context(self) -> str:
        """Generates un contexte émotionnel pour les prompts."""
        dominant = self.get_dominant_emotion()
        states = self.get_emotional_state()

        if not states:
            return f"État émotionnel: {self.baseline_mood} (stable)"

        emotions_str = ", ".join(f"{k}: {v:.0%}" for k, v in states.items())
        return f"État émotionnel: {dominant} (dominant). Actifs: {emotions_str}"

    def on_success(self, context: str = "task"):
        """Réaction à un Success."""
        self.trigger_emotion("satisfaction", 0.6, f"Success: {context}")
        self.trigger_emotion("joy", 0.4, f"Completed: {context}")

    def on_error(self, context: str = "task"):
        """Réaction à une Error."""
        self.trigger_emotion("frustration", 0.5, f"Error: {context}")
        self.trigger_emotion("concern", 0.3, f"Issue: {context}")

    def on_learning(self, topic: str):
        """Réaction à un apprentissage."""
        self.trigger_emotion("curiosity", 0.7, f"Learning: {topic}")
        self.trigger_emotion("satisfaction", 0.4, f"New knowledge: {topic}")


# Singleton
limbic = LimbicSystem()
