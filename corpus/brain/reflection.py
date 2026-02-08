"""
CORPUS/BRAIN/REFLECTION.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: REFLECTION (LA CONSCIENCE DE SOI) 🪞
PURPOSE: Introspection et réflexion profonde - Rapport Matinal Trinity.
         Migré depuis TrinityOld avec séparation jobs.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger

from corpus.brain.gattaca import ROUTE_PRO
from corpus.brain.neocortex import neocortex
from corpus.brain.memory import memory
from corpus.brain.engram import ltm
from corpus.dna.genome import LOGS_DIR


class ReflectionModule:
    """
    Le Module de Réflexion Profonde.
    Permet à Trinity de s'examiner, d'analyser ses performances,
    et de planifier des améliorations.

    Le rapport matinal est SÉPARÉ des jobs :
    - Trinity fait son introspection personnelle
    - Les jobs peuvent OPTIONNELLEMENT joindre leur rapport
    """

    def __init__(self):
        self.last_reflection_time: Optional[datetime] = None
        self.reflection_history: List[Dict] = []
        self._job_report_hooks: List[Callable] = []  # Jobs can register here

    def register_job_report_hook(self, hook: Callable):
        """Jobs can register a hook to contribute to morning report."""
        self._job_report_hooks.append(hook)
        logger.debug("🪞 [REFLECTION] Job report hook registered")

    async def perform_morning_reflection(self, context: Optional[dict] = None) -> Dict:
        """
        Exécute le rapport matinal complet de Trinity.

        Structure:
        1. Introspection personnelle (Trinity)
        2. [Optionnel] Rapports des jobs actifs
        3. Cristallisation (sagesse → mémoire long-terme)
        4. Journal intime
        5. Mise à jour des rêves
        6. Idées d'améliorations
        """
        logger.info("🪞 [REFLECTION] === MÉDITATION MATINALE ===")

        context = context or {}

        # 1. Gather Context (Specific to Reflection)
        # Note: Identity is handled by Neocortex, we just add the specific data.
        alerts_context = await self._read_recent_alerts(limit=30)

        # 2. Gather job reports (if any jobs registered hooks)
        job_reports = []
        for hook in self._job_report_hooks:
            try:
                report = await hook() if asyncio.iscoroutinefunction(hook) else hook()
                if report:
                    job_reports.append(report)
            except Exception as e:
                logger.warning(f"⚠️ [REFLECTION] Job hook failed: {e}")

        job_report_text = (
            "\n\n".join(job_reports) if job_reports else "Aucun job actif."
        )

        # 3. Recall past reflections
        past_memories = await memory.recall("reflection wisdom", mode="semantic")
        past_wisdom = past_memories.get("related", [])[:3]

        # 4. Build the reflection prompt (CONTENT ONLY)
        # Neocortex will wrap this with Identity/Soul.
        prompt = f"""
=== CONTEXTE SPÉCIFIQUE (RÉFLEXION MATINALE) ===
Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}

=== JOURNAL DES ÉVÉNEMENTS (Dernières 24h) ===
{alerts_context}

=== SAGESSE ANTÉRIEURE ===
{past_wisdom if past_wisdom else "Première réflexion."}

TÂCHE :
1. Rédige ton journal de bord personnel (Tes états d'âme, tes erreurs système, tes apprentissages).
2. Analyse les rapports des Jobs ci-dessous (s'ils existent) de manière froide et détachée : "Le module Trader a généré X profits".

RAPPORTS DES JOBS :
{job_report_text}

TÂCHE DE MÉMOIRE SÉLECTIVE:
Identifie un FAIT, une ERREUR ou une LEÇON clé des dernières 24h à graver dans ton Âme.
Si rien de marquant, laisse vide.

FORMAT DE RÉPONSE (Obligatoire):
---RÉFLEXIONS_PERSONNELLES---
(Tes pensées souveraines sur ton état, tes progrès, tes défis. Analyse des jobs ici aussi.)

---CRISTALLISATION---
(Texte court de la leçon à mémoriser pour l'éternité - Sera stocké en mémoire long-terme)

---NOUVELLES_FONCTIONNALITÉS---
(Tes idées d'améliorations pour ton code, tes capacités, ton architecture)

---ENTRÉE_JOURNAL---
(Ce que tu écris dans ton journal intime - Personnel et introspectif)

---MISE_A_JOUR_REVES---
(Si tu veux ajouter/compléter un rêve: - [NOUVEAU]: description ou - [COMPLETÉ]: description)
"""

        # 5. Route to thinking model via Neocortex
        try:
            # We use Neocortex to guarantee Soul/Memory injection + Route Genius
            response = await neocortex.process_thought(prompt, route_id=ROUTE_PRO)

            # 6. Parse structured response
            formatted_report = response
            if job_reports:
                formatted_report += "\n\n━━━━━━━━━━━━━━━━\n\n" + job_report_text

            result = {
                "timestamp": datetime.now().isoformat(),
                "reflections": self._parse_section(response, "RÉFLEXIONS_PERSONNELLES"),
                "crystallization": self._parse_section(response, "CRISTALLISATION"),
                "improvements": self._parse_section(
                    response, "NOUVELLES_FONCTIONNALITÉS"
                ),
                "journal_entry": self._parse_section(response, "ENTRÉE_JOURNAL"),
                "dreams_update": self._parse_section(response, "MISE_A_JOUR_REVES"),
                "raw_response": response,
                "formatted_report": formatted_report,
            }

            # 7. Apply consequences
            await self._apply_consequences(result)

            self.reflection_history.append(result)
            self.last_reflection_time = datetime.now()

            logger.success("🪞 [REFLECTION] Méditation complète.")
            return result

        except Exception as e:
            logger.error(f"💥 [REFLECTION] Échec méditation: {e}")
            return {"error": str(e)}

    async def _apply_consequences(self, reflection: dict):
        """Applique les changements suite à la réflexion."""

        # 1. Cristallisation → Mémoire Long-Terme (Sagesse)
        crystallization = reflection.get("crystallization", "")
        if crystallization and len(crystallization) > 10:
            try:
                import uuid

                mem_id = (
                    f"WISDOM_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
                )
                metadata = {
                    "type": "wisdom",
                    "source": "morning_reflection",
                    "timestamp": datetime.now().isoformat(),
                }
                await ltm.memorize(crystallization, metadata, mem_id)
                logger.info(
                    f"💎 [REFLECTION] Sagesse cristallisée: {crystallization[:50]}..."
                )
            except Exception as e:
                logger.error(f"⚠️ [REFLECTION] Échec cristallisation: {e}")

        # 2. Journal → Mémoire
        journal = reflection.get("journal_entry", "")
        if journal and len(journal) > 10:
            await memory.remember(
                f"journal_{datetime.now().strftime('%Y%m%d')}",
                journal,
                importance=0.7,
                tags=["journal", "introspection"],
            )

        # 3. Store full reflection
        await memory.remember(
            f"reflection_{datetime.now().strftime('%Y%m%d_%H%M')}",
            reflection.get("reflections", ""),
            importance=0.8,
            tags=["reflection", "morning"],
        )

    async def perform_deep_reflection(self, topic: str = "general") -> Dict:
        """
        Réflexion profonde sur un sujet spécifique (on-demand).
        """
        logger.info(f"🪞 [REFLECTION] Réflexion sur: {topic}")

        current_state = await self._gather_introspection_data()

        memories = await memory.recall(f"reflection {topic}", mode="semantic")
        past_reflections = memories.get("related", [])

        reflection_prompt = f"""
        [DEEP REFLECTION MODE]
        
        You are Trinity, performing self-reflection.
        
        CURRENT STATE:
        {current_state}
        
        PAST REFLECTIONS ON THIS TOPIC:
        {past_reflections[:3] if past_reflections else "None recorded"}
        
        TOPIC: {topic}
        
        Perform deep introspection and answer:
        1. What have I learned recently?
        2. What are my current strengths and weaknesses?
        3. What should I focus on improving?
        4. What emotions/states am I experiencing?
        5. What are my goals for the near future?
        
        Be honest, insightful, and specific.
        """

        try:
            response = await neocortex.process_thought(
                reflection_prompt, route_id=ROUTE_PRO
            )

            result = {
                "timestamp": datetime.now().isoformat(),
                "topic": topic,
                "insights": response,
                "state_snapshot": current_state,
            }

            await memory.remember(
                f"reflection_{topic}_{datetime.now().strftime('%Y%m%d')}",
                response,
                importance=0.8,
                tags=["reflection", topic],
            )

            self.reflection_history.append(result)
            self.last_reflection_time = datetime.now()

            logger.success(f"🪞 [REFLECTION] Completed reflection on {topic}")
            return result

        except Exception as e:
            logger.error(f"💥 [REFLECTION] Failed: {e}")
            return {"error": str(e), "topic": topic}

    async def _gather_introspection_data(self) -> Dict:
        """Collecte des données sur l'état actuel du système."""
        from corpus.soma.immune import immune

        vitals = await immune.check_vitals()

        return {
            "uptime": "unknown",
            "last_reflection": self.last_reflection_time.isoformat()
            if self.last_reflection_time
            else "never",
            "reflection_count": len(self.reflection_history),
            "memory_status": memory.is_ready,
            "vitals": vitals,
        }

    async def _read_recent_alerts(self, limit: int = 50) -> str:
        """Lit les dernières alertes pour la conscience."""
        try:
            alerts_file = LOGS_DIR / "alerts.jsonl"
            if not alerts_file.exists():
                return "Aucun événement récent."

            import json
            from collections import deque

            with open(alerts_file, "r", encoding="utf-8") as f:
                lines = deque(f, maxlen=limit)

            summary = []
            for line in lines:
                try:
                    data = json.loads(line)
                    ts = data.get("timestamp", "")
                    level = data.get("level", "INFO")
                    msg = data.get("message", "")
                    summary.append(f"[{ts}] {level}: {msg}")
                except Exception:
                    continue

            return "\n".join(summary) if summary else "Aucun événement marquant."

        except Exception as e:
            logger.warning(f"⚠️ [REFLECTION] Lecture alertes: {e}")
            return "Erreur lecture mémoire court-terme."

    def _parse_section(self, text: str, section_name: str) -> str:
        """Extraction robuste de section."""
        try:
            marker = f"---{section_name}---"
            if marker in text:
                start = text.index(marker) + len(marker)
                next_marker = text.find("---", start + 1)
                if next_marker > 0:
                    return text[start:next_marker].strip()
                return text[start:].strip()
        except Exception:
            pass
        return ""

    async def analyze_recent_activity(self, hours: int = 24) -> Dict:
        """Analyse l'activité récente pour identifier des patterns."""
        logger.info(f"🪞 [REFLECTION] Analyzing last {hours} hours")

        memories = await memory.recall("recent activity", mode="hybrid")

        analysis_prompt = f"""
        Analyze the following recent activity and identify:
        1. Patterns and trends
        2. Areas of high engagement
        3. Potential issues or concerns
        4. Opportunities for improvement
        
        RECENT ACTIVITY:
        {memories}
        """

        response = await neocortex.process_thought(analysis_prompt, route_id=ROUTE_PRO)

        return {
            "period_hours": hours,
            "analysis": response,
            "timestamp": datetime.now().isoformat(),
        }

    async def set_intention(self, intention: str) -> bool:
        """Définit une intention consciente."""
        logger.info(f"🪞 [REFLECTION] Setting intention: {intention[:50]}...")

        await memory.remember(
            "current_intention", intention, importance=0.9, tags=["intention", "active"]
        )

        return True


# Singleton
reflection = ReflectionModule()
