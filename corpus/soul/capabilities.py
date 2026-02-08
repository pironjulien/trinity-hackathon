"""
CORPUS/SOUL/CAPABILITIES.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CAPABILITIES REGISTRY 🎯
PURPOSE: Registre centralisé de toutes les actions disponibles.
      Trinity et les Jobs enregistrent leurs capacités ici.
      Utilisé par le dispatcher pour le routing intelligent.
══════════════════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from loguru import logger


@dataclass
class Capability:
    """Une capacité/action que Trinity peut exécuter."""

    name: str  # Nom unique (ex: "trader.positions")
    description: str  # Description pour l'IA
    handler: Callable  # Fonction à appeler
    category: str = "trinity"  # Catégorie (trinity, trader, creator...)
    requires_args: bool = False  # Nécessite des arguments ?
    arg_description: str = ""  # Description des arguments
    examples: List[str] = field(default_factory=list)  # Exemples de déclencheurs


class CapabilitiesRegistry:
    """
    Registre central des capacités de Trinity.
    Les jobs s'enregistrent ici au démarrage.
    """

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._register_core_capabilities()

    def _register_core_capabilities(self):
        """Enregistre les capacités de base de Trinity."""
        # Ces handlers seront connectés au démarrage
        pass  # Les vrais handlers sont ajoutés via register()

    def register(self, capability: Capability):
        """Enregistre une nouvelle capacité."""
        self._capabilities[capability.name] = capability
        logger.debug(f"🎯 [CAPABILITIES] Registered: {capability.name}")

    def register_action(
        self,
        name: str,
        description: str,
        handler: Callable,
        category: str = "trinity",
        requires_args: bool = False,
        arg_description: str = "",
        examples: Optional[List[str]] = None,
    ):
        """Helper pour enregistrer une action simplement."""
        cap = Capability(
            name=name,
            description=description,
            handler=handler,
            category=category,
            requires_args=requires_args,
            arg_description=arg_description,
            examples=examples or [],
        )
        self.register(cap)

    def get(self, name: str) -> Optional[Capability]:
        """Récupère une capacité par son nom."""
        return self._capabilities.get(name)

    def get_all(self) -> List[Capability]:
        """Retourne toutes les capacités."""
        return list(self._capabilities.values())

    def get_by_category(self, category: str) -> List[Capability]:
        """Retourne les capacités d'une catégorie."""
        return [c for c in self._capabilities.values() if c.category == category]

    def get_categories(self) -> List[str]:
        """Retourne toutes les catégories."""
        return list(set(c.category for c in self._capabilities.values()))

    async def execute(self, name: str, **kwargs) -> Any:
        """Exécute une capacité par son nom."""
        cap = self.get(name)
        if not cap:
            return {"error": f"Capacité inconnue: {name}"}

        try:
            import asyncio

            if asyncio.iscoroutinefunction(cap.handler):
                return await cap.handler(**kwargs)
            else:
                return cap.handler(**kwargs)
        except Exception as e:
            logger.error(f"🎯 [CAPABILITIES] Execute error {name}: {e}")
            return {"error": str(e)}

    def format_for_prompt(self) -> str:
        """
        Formate toutes les capacités pour injection dans le prompt IA.
        Format compact pour Route 11 (classifier rapide).
        """
        lines = ["[ACTIONS DISPONIBLES]"]

        for category in sorted(self.get_categories()):
            caps = self.get_by_category(category)
            lines.append(f"\n## {category.upper()}")

            for cap in caps:
                args = f" <{cap.arg_description}>" if cap.requires_args else ""
                lines.append(f"- {cap.name}{args}: {cap.description}")
                if cap.examples:
                    lines.append(f"  Exemples: {', '.join(cap.examples[:2])}")

        return "\n".join(lines)

    def format_names_only(self) -> str:
        """Format ultra-compact: juste les noms des actions."""
        return ", ".join(sorted(self._capabilities.keys()))


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

capabilities = CapabilitiesRegistry()


# ════════════════════════════════════════════════════════════════════════════
# DECORATOR HELPER
# ════════════════════════════════════════════════════════════════════════════


def action(
    name: str,
    description: str,
    category: str = "trinity",
    requires_args: bool = False,
    arg_description: str = "",
    examples: Optional[List[str]] = None,
):
    """
    Décorateur pour enregistrer une fonction comme capacité.

    Usage:
        @action("status", "Affiche le statut de Trinity")
        async def get_status():
            return {...}
    """

    def decorator(func):
        capabilities.register_action(
            name=name,
            description=description,
            handler=func,
            category=category,
            requires_args=requires_args,
            arg_description=arg_description,
            examples=examples or [],
        )
        return func

    return decorator
