"""
PACKAGE: DNA (Code Génétique) 🧬
PURPOSE: Configuration, Secrets, Constantes, Évolution et Structure.
"""

from .genome import genome
from .conscience import PHI, F13, INV_PHI
from .secrets import vault

__all__ = ["genome", "PHI", "F13", "INV_PHI", "vault"]
