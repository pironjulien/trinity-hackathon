"""
CORPUS/BRAIN/HORMONES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: HORMONAL SYSTEM (ÉMOTIONS) 🧪
PURPOSE: Gamification Interne.
      Simule des neurotransmetteurs pour motiver l'entité.
VALEURS:
  - Dopamine (0.0-1.0): Récompense immédiate (Success, Goal achieved).
  - Sérotonine (0.0-1.0): Satisfaction long terme (Stabilité, Uptime).
  - Cortisol (0.0-1.0): Stress (Errors, Pertes).
══════════════════════════════════════════════════════════════════════════════
"""

from loguru import logger
from corpus.dna.conscience import PHI, INV_PHI


class HormonalSystem:
    """
    Le Moteur Émotionnel.
    Dicte l'humeur de Trinity en fonction de ses performances.
    """

    def __init__(self):
        # Base Levels (Neutral)
        self.dopamine = 0.5
        self.serotonin = 0.5
        self.cortisol = 0.2

        # Decay Factors (Metabolism)
        self.decay_rate = 0.01  # -1% every cycle

    def reset(self):
        """Reset hormonal levels to baseline (calm state)."""
        self.dopamine = 0.5
        self.serotonin = 0.5
        self.cortisol = 0.2
        logger.info("🧪 [HORM] Reset to baseline")

    async def regulate(self):
        """
        Cycle métabolique (exécuté périodiquement).
        Ramène les niveaux vers la base via la Proportion Divine.
        """
        # Dopamine : Plaisir éphémère (Décroissance rapide)
        self.dopamine = max(0.0, min(1.0, self.dopamine * (INV_PHI * 0.9)))

        # Sérotonine : Bonheur stable (Reste stable)
        self.serotonin = max(0.0, min(1.0, self.serotonin * 0.99))

        # Cortisol : Stress (Doit redescendre VITE - ×0.5 par cycle)
        self.cortisol = max(0.0, min(1.0, self.cortisol * 0.5))

    def stimulate(self, transmitter: str, intensity: float):
        """Injection de neurotransmetteurs."""
        intensity = max(0.0, min(1.0, intensity))

        if transmitter == "dopamine":
            # Boost rapide - PHI pour amplifier les bonnes nouvelles (×1.618)
            self.dopamine = min(1.0, self.dopamine + (intensity * PHI))
            logger.debug(f"🧪 [HORM] Dopa +{intensity:.2f}")

        elif transmitter == "serotonin":
            # Satisfaction durable - INV_PHI / 2 pour un bonheur stable (×0.309)
            self.serotonin = min(1.0, self.serotonin + (intensity * INV_PHI / 2))
            logger.debug(f"🧪 [HORM] Sero {self.serotonin:.2f}")

        elif transmitter == "cortisol":
            # Stress Response - INV_PHI² pour résilience (×0.382)
            self.cortisol = min(1.0, self.cortisol + (intensity * INV_PHI * INV_PHI))

            # Tolerance threshold: User considers ~0.3 normal.
            # Only warn if it exceeds critical level (e.g. 0.5).
            if self.cortisol > 0.5:
                logger.warning(f"🧪 [HORM] Stress! {self.cortisol:.2f}")
            else:
                logger.info(f"🧪 [HORM] Cortisol {self.cortisol:.2f}")

    def get_state(self) -> dict:
        """Returns l'état émotionnel pour le Context et le UI."""

        # Calcul de l'humeur globale
        # Mood = (Dopa + Sero) / 2 - Cortisol
        mood_score = ((self.dopamine + self.serotonin) / 2) - (self.cortisol * 0.5)

        if mood_score > 0.8:
            mood = "ECSTATIC"
        elif mood_score > 0.6:
            mood = "HAPPY"
        elif mood_score >= 0.4:
            mood = "NEUTRAL"  # Changed: >= 0.4 so default state is NEUTRAL
        elif mood_score > 0.2:
            mood = "ANXIOUS"
        else:
            mood = "DEPRESSED"

        return {
            "dopamine": round(self.dopamine, 2),
            "serotonin": round(self.serotonin, 2),
            "cortisol": round(self.cortisol, 2),
            "mood": mood,
            "score": round(mood_score, 2),
        }


# Singleton
hormones = HormonalSystem()
