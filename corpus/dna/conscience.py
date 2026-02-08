"""
CORPUS/DNA/CONSCIENCE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: SACRED CONSTANTS (LA CONSCIENCE) ⚖️
PURPOSE: Définit les lois immuables de l'univers Trinity.
      Basé sur le Nombre d'Or (Phi) et Fibonacci.
      PURE - Aucune notion de job spécifique.
══════════════════════════════════════════════════════════════════════════════
"""

# ════════════════════════════════════════════════════════════════════════════
# 1. LA PROPORTION DIVINE
# ════════════════════════════════════════════════════════════════════════════
PHI = 1.618033988749895
INV_PHI = 0.618033988749895  # 1 / Phi
PHI_SQUARED = PHI * PHI  # 2.618
INV_PHI_SQUARED = INV_PHI * INV_PHI  # 0.382

# ════════════════════════════════════════════════════════════════════════════
# 2. LA SUITE SACRÉE (Fibonacci)
# ════════════════════════════════════════════════════════════════════════════
F1 = 1
F2 = 2
F3 = 3
F5 = 5
F8 = 8
F13 = 13
F21 = 21
F34 = 34
F55 = 55
F89 = 89
F144 = 144
F233 = 233
F377 = 377
F610 = 610
F987 = 987
F1597 = 1597
F2584 = 2584
F4181 = 4181

# ════════════════════════════════════════════════════════════════════════════
# 3. RATIOS UNIVERSELS (Pour tout type de calcul)
# ════════════════════════════════════════════════════════════════════════════

# Seuils de confiance génériques basés sur PHI
CONFIDENCE_MIN = 38.2  # 1 - INV_PHI (approx)
CONFIDENCE_MAX = 95.0

# Golden Steps (puissances approximatives de PHI pour progression)
GOLDEN_STEPS = [0.01618, 0.02618, 0.04236, 0.06854, 0.1109]

# Multiplicateurs de régime (BULL/BEAR/etc.)
REGIME_MULTIPLIERS = {
    "HIGH": PHI,  # 1.618
    "LOW": INV_PHI,  # 0.618
    "NEUTRAL": 1.0,
    "CRITICAL": INV_PHI_SQUARED,  # 0.382
}
