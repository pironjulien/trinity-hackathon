"""
CORPUS/BRAIN/AXON.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: AXON (NEURAL ROUTER) 🚀
PURPOSE: Route intelligemment les messages vers le bon modèle/action.
      1. Route 11 (Spark) classifie le message
      2. ACTION → Exécute directement
      3. INFO → Route 2 (Fast response)
      4. COMPLEX → Route 1 (Genius thinking)
══════════════════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass
from typing import Dict, Any
from loguru import logger

from corpus.brain.gattaca import gattaca, ROUTE_PRO
from corpus.soul.capabilities import capabilities
from corpus.brain.circadian import circadian

# Route 3 = Flash (classifier rapide)
ROUTE_SPARK = 3


# ════════════════════════════════════════════════════════════════════════════
# CLASSIFICATION RESULT
# ════════════════════════════════════════════════════════════════════════════


@dataclass
class ClassificationResult:
    """Résultat de la classification du message."""

    type: str  # ACTION, INFO, COMPLEX
    action: str = ""  # Nom de l'action si type == ACTION
    args: str = ""  # Arguments extraits
    confidence: float = 1.0


# ════════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ════════════════════════════════════════════════════════════════════════════


class IntelligentDispatcher:
    """
    Dispatcher intelligent multi-modèle.
    Utilise Route 11 (Spark) pour classifier, puis route vers le bon modèle.
    """

    CLASSIFIER_PROMPT = """Tu es un classifier de messages. Analyse le message et réponds UNIQUEMENT avec UN des formats suivants:

- ACTION:nom_action si c'est une commande/action à exécuter
- ACTION:nom_action:arguments si l'action nécessite des arguments
- INFO si c'est une question simple ou demande d'information
- COMPLEX si ça demande réflexion approfondie, analyse, ou créativité

{capabilities}

MESSAGE: {message}

RÉPONSE (un seul mot/format):"""

    def __init__(self):
        self._stats = {"action": 0, "info": 0, "complex": 0, "errors": 0}

    async def classify(self, message: str) -> ClassificationResult:
        """
        Classifie un message via Route 3 (Flash - rapide et pas cher).
        """
        try:
            # Build prompt with capabilities
            caps_text = capabilities.format_for_prompt()
            prompt = self.CLASSIFIER_PROMPT.format(
                capabilities=caps_text, message=message
            )

            # Call Route 11 (Spark) - ultra fast
            response = await gattaca.route(
                prompt=prompt,
                route_id=ROUTE_SPARK,  # Route 3
            )

            if not response:
                return ClassificationResult(type="INFO")

            # Parse response
            result = self._parse_classification(response.strip())
            logger.debug(
                f"🚀 [DISPATCHER] Classified as: {result.type} | {result.action}"
            )

            return result

        except Exception as e:
            logger.error(f"🚀 [DISPATCHER] Classification error: {e}")
            self._stats["errors"] += 1
            return ClassificationResult(type="INFO")

    def _parse_classification(self, response: str) -> ClassificationResult:
        """Parse la réponse du classifier."""
        response = response.upper().strip()

        if response.startswith("ACTION:"):
            parts = response.split(":")
            action = parts[1].lower() if len(parts) > 1 else ""
            args = parts[2] if len(parts) > 2 else ""
            return ClassificationResult(type="ACTION", action=action, args=args)

        elif response == "COMPLEX":
            return ClassificationResult(type="COMPLEX")

        else:  # Default to INFO
            return ClassificationResult(type="INFO")

    async def dispatch(
        self, message: str, context: str = "", system_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Dispatche un message vers le bon traitement.

        Returns:
            {
                "response": str,        # Réponse textuelle
                "type": str,            # ACTION/INFO/COMPLEX
                "action_result": Any,   # Résultat de l'action si applicable
                "route_used": int       # Route Gattaca utilisée
            }
        """
        # 1. Classify with Route 11
        classification = await self.classify(message)

        # 🧠 BIO-CLOCK GUARD
        # Refuse heavy work if exhausted (< 20% Energy)
        # Exception: INFO handling is cheap enough (Route 2)
        if classification.type in ["COMPLEX", "ACTION"]:
            energy = circadian.get_current_energy()
            if energy < 0.2:
                logger.warning(
                    f"💤 [DISPATCHER] Bio-blocked complex task (Energy {energy:.2f})"
                )
                return {
                    "response": "😴 Je suis trop fatiguée (Énergie < 20%). Je passe en mode veille. Repose-moi la question demain.",
                    "type": "INFO",
                    "action_result": None,
                    "route_used": 0,
                }

        # 2. Route based on type
        if classification.type == "ACTION":
            return await self._handle_action(classification, message)

        elif classification.type == "COMPLEX":
            return await self._handle_complex(message, context, system_prompt)

        else:  # INFO
            return await self._handle_info(message, context, system_prompt)

    async def _handle_action(
        self, classification: ClassificationResult, original_message: str
    ) -> Dict[str, Any]:
        """Execute une action directement."""
        self._stats["action"] += 1

        # Check if action exists
        cap = capabilities.get(classification.action)
        if not cap:
            # Action inconnue, fallback to INFO
            logger.warning(f"🚀 [DISPATCHER] Unknown action: {classification.action}")
            return await self._handle_info(original_message, "", "")

        # Execute action
        try:
            result = await capabilities.execute(
                classification.action, args=classification.args
            )

            # Format response
            if isinstance(result, dict) and "error" in result:
                return {
                    "response": f"Erreur: {result['error']}",
                    "type": "ACTION",
                    "action_result": result,
                    "route_used": 11,
                }

            return {
                "response": str(result) if result else "Action exécutée.",
                "type": "ACTION",
                "action_result": result,
                "route_used": ROUTE_SPARK,
            }

        except Exception as e:
            logger.error(f"🚀 [DISPATCHER] Action execution error: {e}")
            return {
                "response": f"Erreur d'exécution: {e}",
                "type": "ACTION",
                "action_result": None,
                "route_used": 11,
            }

    async def _handle_info(
        self,
        message: str,
        context: str,  # Ignored legacy arg
        system_prompt: str,  # Ignored legacy arg
    ) -> Dict[str, Any]:
        """Traite une demande d'information simple via Route 3."""
        self._stats["info"] += 1

        # SMART CONTEXT: LOW (Fast)
        from corpus.soul.spirit import spirit

        smart_context = await spirit.get_context(complexity_level="low")
        full_prompt = f"{smart_context}\n\nUser: {message}"

        from corpus.brain.gattaca import gattaca

        response = await gattaca.route(
            prompt=full_prompt,
            route_id=gattaca.ROUTE_FLASH,  # Route 3 - Fast
        )

        return {
            "response": response or "Je n'ai pas de réponse.",
            "type": "INFO",
            "action_result": None,
            "route_used": gattaca.ROUTE_FLASH,
        }

    async def _handle_complex(
        self,
        message: str,
        context: str,  # Ignored legacy arg
        system_prompt: str,  # Ignored legacy arg
    ) -> Dict[str, Any]:
        """Traite une demande complexe via Route 2 (Pro)."""
        self._stats["complex"] += 1

        # SMART CONTEXT: HIGH (Deep)
        from corpus.soul.spirit import spirit

        smart_context = await spirit.get_context(complexity_level="high")
        full_prompt = f"{smart_context}\n\nUser: {message}"

        response = await gattaca.route(
            prompt=full_prompt,
            route_id=ROUTE_PRO,  # Route 2 - Deep thinking
        )

        return {
            "response": response or "Je n'ai pas de réponse.",
            "type": "COMPLEX",
            "action_result": None,
            "route_used": ROUTE_PRO,
        }

    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques de routing."""
        return self._stats.copy()


# ════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ════════════════════════════════════════════════════════════════════════════

dispatcher = IntelligentDispatcher()
