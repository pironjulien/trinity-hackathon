"""
JOBS/TRADER/INTELLIGENCE/QUANTUM.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: QUANTUM RESONANCE PULSE (QRP) ⚛️
PURPOSE: Detect Market-Wide Coherence (The "Tsunami" Effect).
MATH: Vector Alignment of 127 Pairs.
══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from jobs.trader.config import PHI


class QuantumPulse:
    def __init__(self):
        self.coherence_score = 0.0  # 0.0 (Chaos) to 1.0 (Laser)
        self.market_vector = 0.0  # Direction (+1.0 Bull / -1.0 Bear)
        self.last_resonance = 0.0
        self.history = []  # Rolling window for resonance

    def calculate_coherence(self, market_snapshot: list) -> dict:
        """
        Calcule la cohérence globale du marché.

        Args:
            market_snapshot: Liste de variations [%_change_1m, %_change_5m, ...]
                             pour TOUTES les paires actives (127+).
        """
        if not market_snapshot or len(market_snapshot) < 10:
            return {"score": 0.0, "state": "INSUFFICIENT_DATA"}

        # Convert to numpy array for speed
        vectors = np.array(market_snapshot)

        # 1. Magnitude Initiale (Somme absolue des mouvements)
        # Si tout le monde dort (0% change), la cohérence est nulle
        energy = np.sum(np.abs(vectors))
        if energy < 0.1:  # Too quiet
            self.coherence_score = 0.0
            return {"score": 0.0, "state": "DEAD_CALM"}

        # 2. Vector Sum (Directionnelle)
        # Si tout le monde monte : Sum est grande positive
        # Si moitié monte / moitié descend : Sum est proche de 0
        vector_sum = np.sum(vectors)

        # 3. Coherence Ratio (Q-Factor)
        # |Sum| / Energy.
        # 1.0 = Tous alignés parfaitement. 0.0 = Chaos parfait.
        raw_coherence = abs(vector_sum) / energy

        # 4. Amplify (Sigmoid-like activation around 0.5)
        # On veut réagir fort quand ça dépasse 0.6
        q_score = raw_coherence ** (1 / PHI)  # Racine PHI-ième pour lisser

        self.coherence_score = q_score
        self.market_vector = vector_sum

        # Determine State
        state = "CHAOS"
        if q_score > 0.8:
            state = "QUANTUM_ALIGNMENT"  # ⚛️ IMPACT IMMINENT
        elif q_score > 0.6:
            state = "RESONANCE"  # 🌊 Wave building
        elif q_score < 0.3:
            state = "DECOHERENCE"  # 🌫️ Fog

        return {
            "score": float(q_score),
            "raw_coherence": float(raw_coherence),
            "energy": float(energy),
            "state": state,
            "direction": "BULL" if vector_sum > 0 else "BEAR",
        }


# Singleton
quantum = QuantumPulse()
