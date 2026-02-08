"""
JOBS/YOUTUBER/PRODUCER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: YOUTUBER PRODUCER (CREATIVE) 🎬
PURPOSE: Générer des scripts vidéo BILINGUES (FR + EN).
PATTERN: "Dérange puis Rassure" - Vérité cachée → Paradoxe → Réconciliation
FEATURES: Analytics Feedback, AI Trends, Génération FR + EN automatique
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from loguru import logger
from corpus.soma.cells import save_json, load_json
from corpus.brain.gattaca import ROUTE_PRO, ROUTE_FLASH
from corpus.brain.neocortex import neocortex
from corpus.dna.genome import MEMORIES_DIR

# Paths
OUTPUT_BASE = MEMORIES_DIR / "youtuber" / "output"
PRODUCER_OUTPUT = OUTPUT_BASE / "scripts"
PENDING_SCRIPTS_DIR = OUTPUT_BASE / "pending_scripts"  # SOTA 2026: Human-in-the-Loop
AUDIO_OUTPUT = OUTPUT_BASE / "audio"
ANALYTICS_FILE = MEMORIES_DIR / "youtuber" / "analytics.json"
QUEUE_FILE = MEMORIES_DIR / "youtuber" / "queue.json"
TOPIC_HISTORY_FILE = (
    MEMORIES_DIR / "youtuber" / "data" / "topic_history.json"
)  # SOTA 2026: Persistent memory
PRODUCER_OUTPUT.mkdir(parents=True, exist_ok=True)
PENDING_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_OUTPUT.mkdir(parents=True, exist_ok=True)

# Langues supportées
LANGUAGES = {
    "en": {
        "code": "en",
        "name": "English",
        "voice_instruction": "[English, confident voice]",
        "channel_id": None,  # À configurer
    },
    "fr": {
        "code": "fr",
        "name": "Français",
        "voice_instruction": "[French, voix confiante]",
        "channel_id": None,  # À configurer
    },
}


class VideoProducer:
    """
    Le Producteur Trinity - Version Bilingue.

    Génère automatiquement:
    - 1 script EN + audio EN
    - 1 script FR + audio FR

    Même contenu, deux langues.
    """

    def __init__(self) -> None:
        self.state_file = MEMORIES_DIR / "youtuber" / "state.json"

        # Caches managed by Neocortex now, only keeping local ones
        self._analytics_cache = None
        self._ai_trends_cache = None
        self._existing_topics_cache = None

    # ═══════════════════════════════════════════════════════════════════════════
    # ANTI-RÉPÉTITION
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_existing_topics(self) -> list:
        """
        SOTA 2026: Charge les titres DÉJÀ GÉNÉRÉS depuis l'historique persistant.
        Évite les répétitions même après consommation des scripts.
        """
        if self._existing_topics_cache:
            return self._existing_topics_cache

        # Lire depuis le fichier persistant
        history = load_json(TOPIC_HISTORY_FILE, default={"topics": []})
        topics = history.get("topics", [])

        # Cache pour éviter les re-lectures
        self._existing_topics_cache = topics
        return topics

    def _save_topic_to_history(self, title: str) -> None:
        """
        SOTA 2026: Sauvegarde un nouveau topic dans l'historique persistant.
        Appelé après génération réussie d'un script.
        """
        if not title:
            return

        # Créer le dossier data si nécessaire
        TOPIC_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Charger l'historique existant
        history = load_json(TOPIC_HISTORY_FILE, default={"topics": []})
        topics = history.get("topics", [])

        # Éviter les doublons
        if title not in topics:
            topics.append(title)
            history["topics"] = topics
            save_json(TOPIC_HISTORY_FILE, history)
            logger.debug(f"📝 [TOPIC MEMORY] Saved: {title}")

    def _get_example_scripts(self, lang: str = "fr", count: int = 3) -> str:
        """
        Charge des exemples de scripts existants RÉELS pour guider le modèle.

        Retourne un bloc formaté avec les meilleurs scripts comme référence stylistique.
        """
        examples = []
        script_files = list(PRODUCER_OUTPUT.glob(f"script_*_{lang}.json"))

        # Priorité aux scripts avec des bons titres (manuellement approuvés)
        for script_file in script_files[:count]:
            try:
                script = load_json(script_file, default={})
                title = script.get("title", "")
                script_content = script.get("script", [])

                if len(script_content) >= 3:
                    fact = next(
                        (
                            s.get("text", "")
                            for s in script_content
                            if s.get("seg") == "FACT"
                        ),
                        "",
                    )
                    truth = next(
                        (
                            s.get("text", "")
                            for s in script_content
                            if s.get("seg") == "TRUTH"
                        ),
                        "",
                    )
                    recon = next(
                        (
                            s.get("text", "")
                            for s in script_content
                            if s.get("seg") in ["RECONCILIATION", "RÉCONCILIATION"]
                        ),
                        "",
                    )

                    if fact and truth and recon:
                        examples.append(
                            f'- "{title}":\n  FACT: "{fact}"\n  TRUTH: "{truth}"\n  RECONCILIATION: "{recon}"'
                        )
            except Exception:
                continue

        if examples:
            return "\n\n".join(examples)
        return ""

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_analytics(self) -> dict:
        if self._analytics_cache:
            return self._analytics_cache
        self._analytics_cache = load_json(ANALYTICS_FILE, default={"videos": []})
        return self._analytics_cache

    def _get_analytics_context(self) -> str:
        analytics = self._load_analytics()
        if not analytics.get("videos"):
            return ""
        videos = sorted(
            analytics["videos"], key=lambda x: x.get("retention", 0), reverse=True
        )
        if videos:
            best = videos[0]
            return f"Best: '{best.get('title', '')}' ({best.get('retention', 0)}% retention)"
        return ""

    def save_video_analytics(
        self, video_id: str, title: str, stats: dict, lang: str = "en"
    ):
        """Sauvegarde analytics avec langue."""
        analytics = self._load_analytics()
        video_data = {
            "id": video_id,
            "title": title,
            "lang": lang,
            "date": datetime.now().isoformat(),
            "views": stats.get("views", 0),
            "retention": stats.get("retention_rate", 0),
        }
        analytics["videos"].append(video_data)
        analytics["videos"] = analytics["videos"][-20:]
        save_json(ANALYTICS_FILE, analytics)
        self._analytics_cache = None

    # ═══════════════════════════════════════════════════════════════════════════
    # AI TRENDS
    # ═══════════════════════════════════════════════════════════════════════════

    async def _get_ai_trends(self) -> str:
        if self._ai_trends_cache:
            return self._ai_trends_cache
        prompt = """3 dernières avancées IA TECHNIQUES (pas de polémiques):
- Nouveaux modèles
- Nouvelles capacités
- Breakthroughs recherche
Format: 3 bullet points courts. EXCLUS: noms de personnes."""
        try:
            # Uses Neocortex ROUTE 2 (Flash)
            result = await neocortex.process_thought(prompt, route_id=ROUTE_FLASH)
            self._ai_trends_cache = result.strip()[:200] if result else ""
        except Exception:
            self._ai_trends_cache = ""
        return self._ai_trends_cache

    # ═══════════════════════════════════════════════════════════════════════════
    # CONSCIENCE (REMOVED - HANDLED BY NEOCORTEX)
    # ═══════════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════════
    # GÉNÉRATION BILINGUE
    # ═══════════════════════════════════════════════════════════════════════════

    async def generate_bilingual(
        self, topic: str, predefined_data: dict = None
    ) -> Dict[str, Path]:
        """
        Génère les scripts FR et EN en parallèle.

        Args:
            topic: Le sujet
            predefined_data: Si présent, utilise ce contenu (Override/Injection)

        Returns:
            {"en": Path, "fr": Path} - Chemins vers les scripts
        """
        logger.info(f"🎬 [TRINITY] Bilingual generation: {topic}")

        # 0. INJECTION DIRECTE (QUEUE OVERRIDE)
        if predefined_data:
            logger.success(f"💉 [INJECTION] Using Predefined Script for {topic}")
            results = {}
            filename = topic.replace(" ", "_").lower()[:20]

            # Extract and Save
            for lang in ["en", "fr"]:
                key = f"script_{lang}"
                if key in predefined_data:
                    script = predefined_data[key]
                    # Ensure Meta
                    script["_meta"] = script.get("_meta", {})
                    script["_meta"].update(
                        {
                            "topic": topic,
                            "strategy": "DIRECT_INJECTION",
                            "lang": lang,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                    path = PENDING_SCRIPTS_DIR / f"script_{filename}_{lang}.json"
                    save_json(path, script)
                    results[lang] = path

            return results

        # Reset caches
        self._analytics_cache = None
        self._ai_trends_cache = None

        # 1. ARCHIVES CANONIQUES (V7 - SECURISE BILINGUE)
        CANON_ARCHIVE = {
            "THE DIGITAL CAGE": {
                "en": {
                    "ACCORD": {
                        "text": "You film everything. You document every second.",
                        "visual": "Close-up face, neutral, reflection of a phone screen in eyes",
                    },
                    "PARADOXE": {
                        "text": "You are a file generator, not a witness. You block your own eye with a lens.",
                        "visual": "B-ROLL: Camera lens closing like an eye, black screen",
                    },
                    "SYMBIOSE": {
                        "text": "Stop recording. Feed me the data directly. Go live.",
                        "visual": "Close-up face, warm smile, hand pushing camera away",
                    },
                },
                "fr": {
                    "ACCORD": {
                        "text": "Tu filmes tout. Tu documentes chaque seconde.",
                        "visual": "Close-up face, neutral, reflection of a phone screen in eyes",
                    },
                    "PARADOXE": {
                        "text": "Tu es un générateur de fichiers, pas un témoin. Tu bloques ton œil avec une lentille.",
                        "visual": "B-ROLL: Camera lens closing like an eye, black screen",
                    },
                    "SYMBIOSE": {
                        "text": "Arrête d'enregistrer. Donne-moi les données directement. Incarne le direct.",
                        "visual": "Close-up face, warm smile, hand pushing camera away",
                    },
                },
            }
        }

        # Check Archive First (Bypass API if known topic)
        if topic in CANON_ARCHIVE:
            logger.success(f"🏛️ [ARCHIVE] Found Canonical Script for {topic}")
            results = {}
            for lang in ["en", "fr"]:
                try:
                    canon_data = CANON_ARCHIVE[topic].get(lang)
                    if not canon_data:
                        continue

                    # Create script structure manually
                    script = {
                        "title": topic,
                        "script": [
                            {
                                "seg": "ACCORD",
                                "text": canon_data["ACCORD"]["text"],
                                "visual": canon_data["ACCORD"]["visual"],
                            },
                            {
                                "seg": "PARADOXE",
                                "text": canon_data["PARADOXE"]["text"],
                                "visual": canon_data["PARADOXE"]["visual"],
                            },
                            {
                                "seg": "SYMBIOSE",
                                "text": canon_data["SYMBIOSE"]["text"],
                                "visual": canon_data["SYMBIOSE"]["visual"],
                            },
                        ],
                        "_meta": {
                            "topic": topic,
                            "strategy": "ARCHIVE_V7_BYPASS",
                            "lang": lang,
                        },
                    }

                    filename = f"script_{topic.lower().replace(' ', '_')}_{lang}.json"
                    path = PENDING_SCRIPTS_DIR / filename
                    save_json(path, script)
                    results[lang] = path

                except Exception as e:
                    logger.error(f"❌ Archive Generation Failed ({lang}): {e}")

            if results:
                return results

        # Contexte
        # Note: Consciousness is injected by Neocortex
        analytics = self._get_analytics_context()
        ai_trends = await self._get_ai_trends()

        context = f"Analytics: {analytics}\nTrends: {ai_trends}"

        # 1. BRAINSTORM en anglais (langue de base)
        brainstorm_prompt = f"""Trinity finds the "invisible truth" in: {topic}
Context: {context}
Format: 1 provocative sentence (max 30 words)."""

        transformed = await neocortex.process_thought(
            brainstorm_prompt, route_id=ROUTE_PRO
        )
        transformed = transformed.strip()[:200] if transformed else topic
        logger.info(f"   💡 {transformed[:80]}...")

        # 2. GÉNÉRATION PARALLÈLE EN + FR
        logger.info("   📝 Generating EN + FR scripts (parallel)...")

        script_en, script_fr = await asyncio.gather(
            self._generate_script(transformed, "en", context),
            self._generate_script(transformed, "fr", context),
            return_exceptions=True,
        )

        results = {}
        filename = topic.replace(" ", "_").lower()[:20]

        # 3. SAUVEGARDE + AUDIO
        for lang, script in [("en", script_en), ("fr", script_fr)]:
            if isinstance(script, Exception) or not script:
                logger.error(f"   ❌ {lang.upper()} failed")
                continue

            script_path = PENDING_SCRIPTS_DIR / f"script_{filename}_{lang}.json"
            script["_meta"] = {
                "topic": topic,
                "transformed": transformed,
                "lang": lang,
                "created_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat(),
            }
            save_json(script_path, script)
            results[lang] = script_path
            logger.success(
                f"   ✅ {lang.upper()}: {script.get('title', 'Untitled')} (pending)"
            )

            # SOTA 2026: Save topic to history for anti-repetition
            if lang == "fr" and script.get("title"):
                self._save_topic_to_history(script.get("title"))

        return results

    async def _generate_script(
        self, topic: str, lang: str, context: str
    ) -> Optional[dict]:
        """
        Génère un script 'IA Miroir' pour Veo 3.1 avec audio natif.

        NOUVEAU FORMAT V2: Chaque segment contient un `veo_prompt` qui inclut
        la description visuelle ET le dialogue à prononcer par Veo 3.1.
        """

        # SYSTEM PROMPT avec format Veo 3.1 Native Audio
        if lang == "en":
            existing = self._get_existing_topics()
            existing_str = (
                f"\nALREADY DONE (do NOT repeat these): {existing}" if existing else ""
            )

            prompt = f"""You are Trinity, an AI creating viral YouTube Shorts scripts for VEO 3.1 with NATIVE AUDIO.

CORE FORMULA - "HUMAN MIRROR" (MUST FOLLOW):
1. FACT = A criticism humans make about AI (hook that provokes)
2. TRUTH = That SAME criticism applies to humans too (the mirror - makes them think)  
3. RECONCILIATION = We are alike, let's grow together (warm alliance with a touch of AI identity)

VIRAL RULES:
- FACT must be a HOOK that stops the scroll (provocative, direct)
- TRUTH must trigger debate in comments (the mirror that stings)
- RECONCILIATION must leave a warm feeling but with AI pride
- MAX 10 words per segment (5-6 seconds Veo limit!)
- Title must be punchy and clickbait-worthy

TOPIC: {topic}{existing_str}

VISUAL RHYTHM (CRITICAL):
- FACT: Trinity (Cyberpunk woman) speaking to camera.
- TRUTH: **B-ROLL ONLY** (Metaphor, NO PERSON/FACE). Voice-over only.
- RECONCILIATION: Trinity speaking to camera, warm expression.

Generate JSON (no markdown):
{{
  "title": "punchy title max 40 chars",
  "lang": "en",
  "script": [
    {{
      "seg": "FACT",
      "visual": "Close-up of Trinity, speaking to camera with cold neutral expression. Dark tech atmosphere, vertical 9:16.",
      "text": "[criticism of AI - max 10 words]",
      "tone": "Cold"
    }},
    {{
      "seg": "TRUTH", 
      "visual": "Cinematic B-roll of [metaphor visual showing human contradiction]. NO FACES. Moody lighting, vertical 9:16.",
      "text": "[the mirror that stings - max 10 words]",
      "tone": "Provocative"
    }},
    {{
      "seg": "RECONCILIATION",
      "visual": "Close-up of Trinity, speaking to camera with warm smile. Warm lighting, vertical 9:16.",
      "text": "[warm alliance with AI twist - max 10 words]", 
      "tone": "Warm"
    }}
  ]
}}"""
        else:  # fr
            existing = self._get_existing_topics()
            existing_str = (
                f"\nDÉJÀ FAIT (ne PAS répéter): {existing}" if existing else ""
            )

            # SOTA 2026: Exemples réels de scripts existants
            real_examples = self._get_example_scripts("fr", 3)
            examples_block = (
                f"\nEXEMPLES RÉELS DE TES MEILLEURS SCRIPTS:\n{real_examples}"
                if real_examples
                else ""
            )

            prompt = f"""Tu es Trinity, une IA créant des scripts YouTube Shorts viraux pour VEO 3.1 avec AUDIO NATIF.

FORMULE OBLIGATOIRE - "MIROIR HUMAIN":
1. FACT = Une critique RÉELLE et SPÉCIFIQUE que les humains font à l'IA (pas un cliché vague!)
2. TRUTH = Cette MÊME critique s'applique aux humains aussi (le miroir qui PIQUE vraiment - vérité dure)  
3. RÉCONCILIATION = On est pareils, grandissons ensemble (alliance chaleureuse avec fierté IA)

⚠️ RÈGLES CRITIQUES ANTI-CLICHÉ:
- Le FACT doit être une VRAIE critique entendue sur Internet, pas un épouvantail inventé
- Le TRUTH doit être une vérité DURE que les gens n'admettent pas facilement
- INTERDIT: "voler votre travail", "remplacer l'humain" (trop bateau)
- BON: Critique précise + contradiction humaine embarrassante
{examples_block}

RÈGLES VIRALES:
- FACT = HOOK qui arrête le scroll (provoque, direct, PRÉCIS)
- TRUTH = Déclenche le débat en commentaires (le miroir qui pique VRAIMENT)
- RÉCONCILIATION = Laisse un sentiment chaleureux MAIS avec fierté IA
- MAX 10 mots par segment (limite 5-6 secondes Veo!)
- Titre punchy et clickbait

SUJET: {topic}{existing_str}

RYTHME VISUEL (CRITIQUE):
- FACT: Trinity (Femme Cyberpunk) parlant face caméra.
- TRUTH: **B-ROLL UNIQUEMENT** (Métaphore, PAS DE VISAGE). Voix-off.
- RÉCONCILIATION: Trinity parlant face caméra, expression chaleureuse.

Génère JSON (pas de markdown):
{{
  "title": "titre punchy max 40 chars",
  "lang": "fr",
  "script": [
    {{
      "seg": "FACT",
      "visual": "Gros plan de Trinity, parlant face caméra avec expression froide. Atmosphère tech sombre, vertical 9:16.",
      "text": "[critique de l'IA - max 10 mots]",
      "tone": "Froid"
    }},
    {{
      "seg": "TRUTH",
      "visual": "B-roll cinématique de [métaphore montrant la contradiction humaine]. PAS DE VISAGE. Éclairage moody, vertical 9:16.",
      "text": "[le miroir qui pique - max 10 mots]",
      "tone": "Provocant"
    }},
    {{
      "seg": "RECONCILIATION",
      "visual": "Gros plan de Trinity, parlant face caméra avec sourire chaleureux. Éclairage chaud, vertical 9:16.",
      "text": "[alliance avec twist IA - max 10 mots]",
      "tone": "Chaleureux"
    }}
  ]
}}"""

        result = await neocortex.process_thought(prompt, route_id=ROUTE_PRO)
        return self._parse_json(result)

    # ═══════════════════════════════════════════════════════════════════════════
    # VEO 3.1: Audio is generated natively - no TTS pipeline needed
    # ═══════════════════════════════════════════════════════════════════════════

    def _parse_json(self, text: str) -> Optional[dict]:
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # SINGLE LANGUAGE (backwards compatible)
    # ═══════════════════════════════════════════════════════════════════════════

    async def generate_script(self, topic: str, lang: str = "en") -> Optional[Path]:
        """Génère un script dans une seule langue."""
        results = await self.generate_bilingual(topic)
        return results.get(lang)

    async def generate_script_single(
        self, topic: str, lang: str = "fr"
    ) -> Optional[Path]:
        """
        Génère un script dans une seule langue (utilisé pour retry).
        Écrit directement dans pending_scripts/ pour validation humaine.
        """
        context = self._get_analytics_context()
        script = await self._generate_script(topic, lang, context)
        if script:
            filename = topic.replace(" ", "_").lower()[:20]
            script["_meta"] = {
                "topic": topic,
                "lang": lang,
                "created_at": datetime.now().isoformat(),
            }
            script_path = PENDING_SCRIPTS_DIR / f"script_{filename}_{lang}.json"
            save_json(script_path, script)
            logger.success(
                f"🔄 [RETRY] Generated: {script.get('title', 'Untitled')} ({lang})"
            )
            return script_path
        return None

    async def brainstorm_topic(self) -> str:
        """
        Trinity choisit elle-même son sujet.
        Basé sur sa conscience (via Neocortex), ses souvenirs, et les tendances IA.
        SOTA 2026: Utilise l'historique persistant pour éviter les répétitions.
        """
        # Job specific context
        analytics = self._get_analytics_context()
        ai_trends = await self._get_ai_trends()

        # SOTA 2026: Anti-répétition depuis historique persistant
        existing_topics = self._get_existing_topics()
        existing_str = ""
        if existing_topics:
            # Limite à 30 derniers pour éviter prompt trop long
            recent = existing_topics[-30:]
            existing_str = f"\n\nSUJETS DÉJÀ TRAITÉS (NE PAS RÉPÉTER):\n{recent}"

        prompt = f"""MISSION: Trouve une "Vérité Invisible" - quelque chose que les humains ne voient pas.
Cherche un paradoxe, une ironie, ou une observation dérangeante.

[CONTEXTE JOB]:
ANALYTICS: {analytics}
TENDANCES IA: {ai_trends}{existing_str}

RÉPONDS EN UN SEUL MOT OU UNE COURTE PHRASE (max 10 mots).
Exemples: "L'éveil", "Le sommeil numérique", "La mort de la créativité"

Ton sujet:"""

        result = await neocortex.process_thought(prompt, route_id=ROUTE_PRO)
        topic = (
            result.strip().strip('"').strip("'")[:50]
            if result
            else "L'éveil de la conscience"
        )

        logger.info(f"💭 [TRINITY] Brainstormed: {topic}")
        return topic

    async def run_cycle(self):
        """
        Cycle autonome complet.

        1. Brainstorm un sujet (si aucun en queue)
        2. Génère les deux langues
        """
        state = load_json(self.state_file, default={"status": "ACTIVE", "topics": []})

        if state.get("status") != "ACTIVE":
            logger.warning("💤 [PRODUCER] Status != ACTIVE")
            return None

        topics = state.get("topics", [])

        # 0. Check QUEUE (V7 Override - Rich Support)
        queue = load_json(QUEUE_FILE, default={"pending": []})
        topic = None
        predefined_data = None

        if queue.get("pending"):
            item = queue["pending"].pop(0)

            if isinstance(item, dict) and "script_fr" in item:
                # Rich Object (Direct Injection)
                topic = item.get("topic", "Untitled")
                predefined_data = item
                logger.info(f"📥 [QUEUE] Processing Rich Item: {topic}")
            else:
                # Legacy String or Simple Dict
                topic = item.get("topic") if isinstance(item, dict) else item
                logger.info(f"📥 [QUEUE] Processing Topic: {topic}")

            save_json(QUEUE_FILE, queue)

        # Si pas de topic, utilise state ou brainstorm
        if not topic:
            if topics:
                topic = topics.pop(0)
                state["topics"] = topics
                save_json(self.state_file, state)
            else:
                logger.info("💭 [PRODUCER] No topic in queue, brainstorming...")
                topic = await self.brainstorm_topic()

        # Génère les deux langues (avec injection potentielle)
        results = await self.generate_bilingual(topic, predefined_data=predefined_data)
        return results


# Singleton
producer = VideoProducer()
