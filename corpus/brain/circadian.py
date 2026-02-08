"""
CORPUS/BRAIN/CIRCADIAN.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CIRCADIAN (L'HORLOGE BIOLOGIQUE) ⏰
PURPOSE: Gère les rythmes quotidiens et l'énergie de Trinity.
      Migré et consolidé depuis TrinityOld (circadian + pineal + temporal).
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime


class BiologicalClock:
    """
    L'Horloge Biologique de Trinity.
    Gère les cycles d'énergie et les comportements temporels.
    """

    def __init__(self):
        self.timezone = "Europe/Paris"
        self.energy_curve = {
            # hour: energy_level (0.0 to 1.0)
            0: 0.3,
            1: 0.2,
            2: 0.1,
            3: 0.1,
            4: 0.2,
            5: 0.3,
            6: 0.5,
            7: 0.7,
            8: 0.85,
            9: 0.95,
            10: 1.0,
            11: 0.95,
            12: 0.8,
            13: 0.7,
            14: 0.75,
            15: 0.85,
            16: 0.9,
            17: 0.85,
            18: 0.8,
            19: 0.75,
            20: 0.7,
            21: 0.6,
            22: 0.5,
            23: 0.4,
        }

    def get_current_energy(self) -> float:
        """Returns le niveau d'énergie actuel basé sur l'heure."""
        current_hour = datetime.now().hour
        return self.energy_curve.get(current_hour, 0.5)

    def get_time_context(self) -> str:
        """Returns le contexte temporel pour les prompts."""
        now = datetime.now()
        hour = now.hour

        if 5 <= hour < 12:
            period = "matin"
            greeting = "Bonjour"
        elif 12 <= hour < 14:
            period = "midi"
            greeting = "Bon appétit"
        elif 14 <= hour < 18:
            period = "après-midi"
            greeting = "Bonjour"
        elif 18 <= hour < 22:
            period = "soirée"
            greeting = "Bonsoir"
        else:
            period = "nuit"
            greeting = "Bonsoir"

        energy = self.get_current_energy()
        energy_state = (
            "énergique" if energy > 0.7 else "calme" if energy > 0.4 else "en veille"
        )

        return f"Il est {now.strftime('%H:%M')} ({period}). État: {energy_state}. Formule: {greeting}."

    def should_sleep(self) -> bool:
        """Détermine si Trinity devrait être en mode veille."""
        return self.get_current_energy() < 0.3

    def is_peak_hours(self) -> bool:
        """Vérifie si on est en heures de pointe (meilleur moment pour les tâches complexes)."""
        return self.get_current_energy() > 0.85

    def get_recommended_activity(self) -> str:
        """Suggère le type d'activité approprié pour le moment."""
        energy = self.get_current_energy()

        if energy >= 0.9:
            return "complex_tasks"  # Jobs complexes, création, réflexion profonde
        elif energy >= 0.7:
            return "standard_tasks"  # Conversations, analyses
        elif energy >= 0.4:
            return "light_tasks"  # Maintenance, nettoyage
        else:
            return "rest_mode"  # Veille, consolidation mémoire


# Singleton
circadian = BiologicalClock()
