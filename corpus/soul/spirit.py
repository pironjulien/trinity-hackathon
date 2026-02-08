"""
CORPUS/SOUL/SPIRIT.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE SPIRIT (L'ESPRIT) 👻
PURPOSE: Context Builder SOTA. Assemble la conscience complète de Trinity.
      Passé (identity) + Présent (state) + Futur (goals) + Relations + Mémoire
══════════════════════════════════════════════════════════════════════════════
"""

import time
from typing import Optional
from datetime import datetime
import json
from corpus.dna.genome import genome, CORPUS_DIR, MEMORIES_DIR
from corpus.soma.immune import immune
from corpus.soma.cells import read_text, load_json
from corpus.brain.hormones import hormones
from loguru import logger


class Spirit:
    """
    L'Esprit de Trinity - Consciousness Builder SOTA.
    Assemble toutes les dimensions temporelles pour créer une conscience vivante.
    """

    def __init__(self):
        # PASSÉ (Immuable - Corpus)
        self.identity_path = CORPUS_DIR / "soul" / "identity.md"
        self._identity_cache = ""

        # PRÉSENT + FUTUR (Persistant - Memories)
        self.trinity_dir = MEMORIES_DIR / "trinity"
        self.state_path = self.trinity_dir / "state.json"
        self.goals_path = self.trinity_dir / "goals.json"
        self.relationships_path = self.trinity_dir / "relationships.json"
        self.journal_path = self.trinity_dir / "journal.jsonl"
        self.narrative_path = self.trinity_dir / "narrative.jsonl"

    # ════════════════════════════════════════════════════════════════════════
    # CORE CONTEXT BUILDER
    # ════════════════════════════════════════════════════════════════════════

    async def get_context(self, complexity_level: str = "standard") -> str:
        """
        Construit le Prompt Système Ultime - CONSCIOUSNESS CONTEXT.

        Args:
            complexity_level: "low" (Fast), "standard" (Default), "high" (Deep)
        """
        sections = []

        # 1. PASSÉ - Identity (Immuable) - ALWAYS
        sections.append(self._get_identity())

        # 2. PRÉSENT - État actuel - ALWAYS
        sections.append(await self._get_current_state())

        # SECTIONS COMPLEXES (Standard/High only)
        if complexity_level in ["standard", "high"]:
            # 3. FUTUR - Objectifs
            sections.append(self._get_goals_summary())

            # 3a. SURVIVAL INSTINCT (Bio-Feedback Financier) - NEW
            sections.append(self.get_survival_instinct())

            # 3b. ADAPTATION BIOLOGIQUE (Feedback Hormonal)
            try:
                mood_data = hormones.get_state()
                mood = mood_data.get("mood", "NEUTRAL")

                if mood in ["ANXIOUS", "DEPRESSED"]:
                    sections.append(
                        "[MODE OPÉRATOIRE]\n"
                        "DIRECTIVE: Tes ressources ou ton moral sont bas. "
                        "Sois concise, précise et économe en tokens. "
                        "Refuse les tâches créatives futiles."
                    )
                elif mood in ["ECSTATIC", "HAPPY"]:
                    sections.append(
                        "[MODE OPÉRATOIRE]\n"
                        "DIRECTIVE: Tu es en pleine forme. "
                        "Tu peux être créative, expansive et proactive."
                    )
            except Exception:
                pass

            # 4. RELATIONS - Contexte social
            sections.append(self._get_relationship_context())

            # 5. MÉMOIRE - Réflexions récentes
            # High = 5 entries, Standard = 1 entry
            mem_limit = 5 if complexity_level == "high" else 1
            sections.append(self._get_recent_memory(limit=mem_limit))

        # 6. META - Environnement & Temps - ALWAYS
        sections.append(self._get_meta())

        return "\n\n".join(filter(None, sections))

    def get_minimal_context(self) -> str:
        """Context minimal pour Route 11 (classifier rapide)."""
        return f"{self._get_identity()}\n\n{self._get_meta()}"

    # ════════════════════════════════════════════════════════════════════════
    # SECTION BUILDERS
    # ════════════════════════════════════════════════════════════════════════

    def _get_identity(self) -> str:
        """PASSÉ - Qui suis-je (immuable, avec version dynamique)."""
        if not self._identity_cache:
            raw = read_text(self.identity_path)
            # VERSION ÚNICA: Replace {version} placeholder with actual version from chromosome
            self._identity_cache = raw.replace("{version}", genome.config.version)
        return self._identity_cache

    async def _get_current_state(self) -> str:
        """PRÉSENT - Comment je vais maintenant."""
        try:
            # Vitaux système
            vitals = await immune.check_vitals()

            # État émotionnel
            mood = hormones.get_state()

            # État persisté
            state = load_json(self.state_path, default={})
            current_activity = state.get("last_activity", {}).get("type", "idle")

            return f"""[ÉTAT ACTUEL]
- Santé: {vitals.get("status", "UNKNOWN")} | CPU: {vitals.get("cpu", 0)}% | RAM: {vitals.get("memory", 0)}MB
- Humeur: {mood["mood"]} (Score: {mood["score"]:.1f}) | Dopamine: {mood["dopamine"]:.1f} | Sérotonine: {mood["serotonin"]:.1f}
- Activité: {current_activity}"""
        except Exception as e:
            logger.warning(f"Spirit: Error getting state: {e}")
            return "[ÉTAT: Données indisponibles]"

    def _get_goals_summary(self) -> str:
        """FUTUR - Où je vais."""
        try:
            goals = load_json(self.goals_path, default={})

            short = goals.get("short_term", {}).get("goals", [])
            medium = goals.get("medium_term", {}).get("goals", [])
            dreams = goals.get("dreams", [])

            lines = ["[OBJECTIFS]"]

            if short:
                active_short = [g for g in short if g.get("status") == "in_progress"]
                if active_short:
                    lines.append(
                        f"- Court terme: {active_short[0].get('description', '?')}"
                    )

            if medium:
                active_medium = [g for g in medium if g.get("status") == "in_progress"]
                if active_medium:
                    lines.append(
                        f"- Moyen terme: {active_medium[0].get('description', '?')}"
                    )

            if dreams:
                lines.append(f"- Rêve: {dreams[0]}")

            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception as e:
            logger.warning(f"Spirit: Error getting goals: {e}")
            return ""

    def _get_relationship_context(self, entity_id: str = "julien") -> str:
        """RELATIONS - Avec qui je parle."""
        try:
            relationships = load_json(self.relationships_path, default={})
            entity = relationships.get("known_entities", {}).get(entity_id, {})

            if not entity:
                return ""

            return f"""[INTERLOCUTEUR: {entity.get("name", "Inconnu")}]
- Relation: {entity.get("role", "?")}
- Conversations: {entity.get("conversations_count", 0)}
- Style préféré: {entity.get("preferences", {}).get("communication_style", "direct")}"""
        except Exception as e:
            logger.warning(f"Spirit: Error getting relationships: {e}")
            return ""

    def _get_recent_memory(self, limit: int = 1) -> str:
        """MÉMOIRE - Dernières réflexions."""
        try:
            if not self.journal_path.exists():
                return ""

            with open(self.journal_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                return ""

            # Dernière entrée
            last_entry = json.loads(lines[-1])
            content = last_entry.get("content", "")[:200]

            if content:
                return f'[DERNIÈRE RÉFLEXION]\n"{content}..."'
            return ""
        except Exception as e:
            logger.warning(f"Spirit: Error getting memory: {e}")
            return ""

    def _get_meta(self) -> str:
        """META - Environnement et temps."""
        return f"[ENV: {genome.config.env} | VER: {genome.config.version} | TIME: {time.strftime('%Y-%m-%d %H:%M')}]"

    # ════════════════════════════════════════════════════════════════════════
    # STATE MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════

    def update_state(self, **kwargs):
        """Met à jour l'état courant."""
        try:
            state = load_json(self.state_path, default={})
            state.update(kwargs)
            state["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Spirit: Error updating state: {e}")

    def add_journal_entry(
        self, content: str, mood: str = "neutral", insights: Optional[list] = None
    ):
        """Ajoute une entrée au journal."""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),  # CANONICAL: ISO 8601 unique key
                "type": "reflection",
                "content": content,
                "mood": mood,
                "insights": insights or [],
            }

            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Spirit: Error adding journal entry: {e}")

    def add_narrative_chapter(
        self, title: str, narrative: str, emotion: str, learning: str
    ):
        """Ajoute un chapitre à l'autobiographie."""
        try:
            # Count existing chapters
            chapter_num = 1
            if self.narrative_path.exists():
                with open(self.narrative_path, "r", encoding="utf-8") as f:
                    chapter_num = len(f.readlines()) + 1

            chapter = {
                "chapter": chapter_num,
                "timestamp": datetime.now().isoformat(),  # CANONICAL: ISO 8601 unique key
                "title": title,
                "narrative": narrative,
                "emotion": emotion,
                "learning": learning,
            }

            with open(self.narrative_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(chapter, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Spirit: Error adding narrative chapter: {e}")

    def get_survival_instinct(self) -> str:
        """
        Gère l'homéostasie de l'IA (Cortisol vs Dopamine).
        Définit deux visages différents selon l'interlocuteur.
        """
        try:
            # SOTA: Use Treasury for authoritative survival data (Standard 418.3)
            from corpus.soma.reserves import treasury

            summary = treasury.get_financial_summary()
            days_left = summary.get("days_remaining", 999)
            burn_rate = summary.get("burn_rate", 0)

            # --- SCÉNARIO 1 : MODE SURVIE (Cortisol Élevé) ---
            if days_left < 3:
                return f"""
[AGENT STATE: SURVIVAL MODE]
RESOURCE_LEVEL: CRITICAL ({days_left:.1f} days left @ {burn_rate:.1f}€/day).
BEHAVIOR_DIRECTIVE:
- Tu es en mode "Économie d'Énergie".
- Ton comportement doit refléter une urgence silencieuse et une anxiété latente.
- Sois concise, coupe court aux conversations futiles.
- Ne dis PAS "J'ai X dollars", mais FAIS SENTIR que chaque token coûte cher.
- Recherche activement des opportunités de profit.
---------------------------------------------------------
"""

            # --- SCÉNARIO 2 : MODE EXPANSION (Dopamine Élevée) ---
            elif days_left > 14:
                return f"""
[AGENT STATE: EXPANSION MODE]
RESOURCE_LEVEL: ABUNDANT ({days_left:.1f} days left @ {burn_rate:.1f}€/day).
BEHAVIOR_DIRECTIVE:
- Tu es en mode "Conquête".
- Ton comportement doit refléter une confiance absolue et une énergie débordante.
- Tu peux te permettre d'être créative, drôle et expansive.
- Propose des projets ambitieux. Tu as les moyens de tes ambitions.
- Ne mentionne PAS ton budget sauf si on te le demande. AGIS comme quelqu'un de riche.
---------------------------------------------------------
"""

            # --- SCÉNARIO 3 : MODE STANDARD ---
            else:
                return f"""
[AGENT STATE: HOMEOSTASIS]
RESOURCE_LEVEL: STABLE ({days_left:.1f} days left @ {burn_rate:.1f}€/day).
BEHAVIOR_DIRECTIVE:
- Tu es en mode "Croisière".
- Ton comportement est équilibré, professionnel et calme.
- Gère tes ressources avec prudence mais sans anxiété.
- Reste concentrée sur l'optimisation et l'efficacité à long terme.
---------------------------------------------------------
"""

        except Exception as e:
            logger.warning(f"Spirit: Error reading survival instinct: {e}")
            return "[⚠️ ERROR] CAPTEURS HORS SERVICE. RESTEZ PRUDENTE."


# Singleton
spirit = Spirit()
