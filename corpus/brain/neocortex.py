"""
CORPUS/BRAIN/NEOCORTEX.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: NEOCORTEX (LE PENSEUR) 💡
PURPOSE: Boucle de réflexion unifiée. Analyse > Décision > Action.
      Anciennement CognitiveProcessor.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from typing import Optional
from loguru import logger
from corpus.brain.gattaca import gattaca, ROUTE_PRO
from corpus.soul.spirit import spirit
from corpus.brain.memory import memory
from corpus.brain.circadian import circadian
from corpus.brain.hormones import hormones
from corpus.brain.dreaming import dreamer
from corpus.dna.conscience import F55


class CognitiveProcessor:
    """
    Le processeur central de pensées.
    Orchestre la réflexion en boucles asynchrones.
    """

    def __init__(self):
        self.thought_queue = asyncio.Queue()
        self.is_thinking = False
        self._last_dream_hour = -1

    async def process_thought(
        self,
        input_data: str,
        context: Optional[dict] = None,
        route_id: int = ROUTE_PRO,
        critical_thinking: bool = False,
        **kwargs,
    ) -> str:
        """
        Traite une pensée unique via Gattaca, enrichie par l'Esprit.
        Active la Métacognition (Self-Correction) si critical_thinking=True ou route_id=1.
        """
        # Determine if we need metacognition
        # ROUTE PRO (1) implies critical thinking unless explicitly disabled (not implemented here)
        use_critical_thinking = critical_thinking or (route_id == gattaca.ROUTE_PRO)

        mode_log = "Metacognition 🧠" if use_critical_thinking else "Standard"
        logger.debug(
            f"⚙️ [PROCESSING] Thinking about: {input_data[:30]}... (Mode: {mode_log})"
        )

        # 1. Enrichissement (Inject Soul + Active Memory)
        system_context = await spirit.get_context()

        # Active Recall
        memories = await memory.recall(input_data, mode="hybrid")
        stm_context = (
            f"SHORT_TERM: {memories.get('exact')}" if memories.get("exact") else ""
        )
        ltm_context = (
            f"LONG_TERM: {memories.get('related')}" if memories.get("related") else ""
        )

        memory_block = ""
        if stm_context or ltm_context:
            memory_block = f"""
            [ACTIVE MEMORY]
            {stm_context}
            {ltm_context}
            """

        # Construct full prompt
        full_prompt = f"""
        {system_context}
        {memory_block}
        
        INPUT: {input_data}
        MISSION: Respond directly as TRINITY.
        """

        # 2. Routage (Decision with Metacognition Loop)
        if use_critical_thinking:
            # STEP A: Brouillon
            logger.info("💡 [PROCESSING] Metacognition: Generating draft...")
            draft = await gattaca.route(full_prompt, route_id=route_id, **kwargs)

            # STEP B: Critique (Route 2 - Reflex/Fast)
            logger.info("🤔 [PROCESSING] Metacognition: Critiquing draft...")
            critique_prompt = f"""
            CONTEXT: You are the Critical Faculty of an AI.
            Original Input: {input_data}
            Draft Response: {draft}
            
            INSTRUCTION: Critique ce brouillon. Cherche les erreurs logiques, les hallucinations, le style non-naturel ou le manque de précision. 
            Sois impitoyable et précis. Si le brouillon est parfait, dis-le.
            """
            critique = await gattaca.route(
                critique_prompt, route_id=gattaca.ROUTE_FLASH
            )  # Force Flash for speed

            # STEP C: Finalize (Route 1 - Genius)
            logger.info("✅ [PROCESSING] Metacognition: Finalizing...")
            final_prompt = f"""
            {system_context}
            
            ORIGINAL INPUT: {input_data}
            DRAFT: {draft}
            CRITIQUE: {critique}
            
            MISSION: En tenant compte de cette critique, réécris la réponse finale parfaite. 
            Tu ES Trinity. Réponds directement à l'input original. 
            Améliore le style, la précision et la complétude.
            """
            response = await gattaca.route(
                final_prompt, route_id=gattaca.ROUTE_PRO
            )  # Force Pro for quality

        else:
            # Standard single pass
            response = await gattaca.route(full_prompt, route_id=route_id, **kwargs)

        # 3. Synthèse & Memorization (Auto-Feedback)
        # Store the conversation turn
        await memory.remember("last_thought", response, importance=0.2)

        return response

    async def process_chat(
        self,
        user_message: str,
        history: Optional[list] = None,
        **kwargs,
    ) -> str:
        """
        Traite un message chat avec function calling (Tool Use).
        SOTA 2026: Delegate to Gattaca ROUTE_CHAT for proper token logging.
        """
        from corpus.brain.effectors import TRINITY_TOOLS
        from corpus.brain.gattaca import ROUTE_CHAT

        # 1. Build conversation context (Spirit + Memory)
        system_context = await spirit.get_context()

        # Active Recall
        memories = await memory.recall(user_message, mode="hybrid")
        memory_block = ""
        if memories.get("exact") or memories.get("related"):
            memory_block = f"""
[MÉMOIRE ACTIVE]
{memories.get("exact", "")}
{memories.get("related", "")}
"""

        # 2. Build system instruction with tools awareness
        system_instruction = f"""
{system_context}
{memory_block}

[OUTILS DISPONIBLES]
Tu as accès à 3 outils pour vérifier des données spécifiques:
- read_file: Lis un fichier (ex: 'memories/trinity/budget.json', 'jobs/trader/main.py')
- list_directory: Liste le contenu d'un répertoire
- get_error_logs: Récupère les dernières erreurs système

NOTE: Ton état système (CPU, RAM, humeur, hormones) et le status de tes jobs sont DÉJÀ dans ton contexte ci-dessus.
N'utilise les outils que pour des données SPÉCIFIQUES que tu ne connais pas déjà.

[RÈGLES ANTI-HALLUCINATION - OBLIGATOIRES]
1. Tu ne dois JAMAIS inventer de chiffres, dates, durées, ou statistiques.
2. Tes stats système (CPU, RAM, humeur, hormones) sont DÉJÀ dans ton [ÉTAT ACTUEL] ci-dessus - utilise ces données.
3. Tes données financières sont dans le [AGENT STATE] ci-dessus - utilise ces données.
4. Si tu as besoin d'une info SPÉCIFIQUE non présente dans ton contexte, utilise read_file.
5. Si tu ne peux pas vérifier une info, dis simplement "Je ne sais pas" plutôt que d'inventer.

[MISSION]
Réponds directement en tant que TRINITY. Sois naturelle, directe, et PRÉCISE.
Utilise les données de ton contexte EN PRIORITÉ. N'appelle les outils que pour des infos spécifiques absentes.
"""

        # 3. Delegate to Gattaca ROUTE_CHAT (SOTA: Token logging)
        try:
            response = await gattaca.route(
                prompt=user_message,
                route_id=ROUTE_CHAT,
                history=history,
                tools=TRINITY_TOOLS,
                system_instruction=system_instruction,
                files=kwargs.get("files", []),
                source="NEOCORTEX",
            )

            # 4. Memorize response
            await memory.remember("last_chat", response, importance=0.2)

            return response

        except Exception as e:
            logger.error(f"💬 [NEOCORTEX] Chat Error: {e}")
            return f"*Erreur: {str(e)[:100]}*"

    async def start_background_loop(self):
        """Boucle de fond pour les pensées passives (Rêve, Nettoyage)."""
        self.is_thinking = True
        logger.info("💡 Neocortex loop")

        while self.is_thinking:
            try:
                # 1. Regulate hormones (every cycle)
                await hormones.regulate()

                # 2. Check circadian rhythm
                current_hour = circadian.get_current_energy()
                should_dream = circadian.should_sleep()

                # 3. Run REM cycle once per night (between 2-4 AM)
                from datetime import datetime

                hour = datetime.now().hour

                if should_dream and hour != self._last_dream_hour and 2 <= hour <= 4:
                    logger.info(
                        "💡 [PROCESSING] Night detected - starting REM cycle..."
                    )
                    await dreamer.start_rem_cycle()
                    self._last_dream_hour = hour

                # 4. Log activity recommendation
                activity = circadian.get_recommended_activity()
                if activity == "rest_mode":
                    logger.debug("💡 [PROCESSING] Low energy - minimal activity mode")

                # 5. HEARTBEAT (Update persisted state)
                # This ensures state.json is never stale (> 7 days)
                spirit.update_state(
                    mood=hormones.get_state(),
                    current_context={
                        "energy_level": current_hour,  # string label like "high_energy"
                        "focus_mode": self.is_thinking,
                        "activity_recommendation": activity,
                    },
                    uptime={"status": "active", "loop_pid": "primary"},
                )

                # Sleep until next cycle (60 seconds)
                await asyncio.sleep(F55)  # PHI: ~55s Fibonacci cycle

            except Exception as e:
                logger.error(f"💥 [PROCESSING] Loop Error: {e}")
                await asyncio.sleep(
                    F55
                )  # PHI: ~55s Fibonacci cycle  # Continue even on error

    def stop(self):
        """Stop the background loop."""
        self.is_thinking = False
        logger.info("💡 [PROCESSING] Cognitive Loop Stopped.")


# Singleton
neocortex = CognitiveProcessor()
