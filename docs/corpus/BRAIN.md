# 🧠 Brain - The Neural Core

> **All cognition flows through the Brain.** Every Gemini call, every decision, every thought passes through `corpus/brain/`.

---

## 🎯 Gattaca: The Central Router

Gattaca is the **single gateway** for all AI operations. No direct API calls are allowed elsewhere.

**71KB, 1600+ lines** - The largest module in Trinity.

```python
# corpus/brain/gattaca.py
class GattacaRouter:
    ROUTES = {
        1: "gemini-3-pro-preview",         # 🧠 Reasoning
        2: "gemini-3-flash-preview",       # ⚡ Reflexes (<100ms)
        3: "gemini-3-pro-image-preview",   # 🎨 Image Creation
        4: "gemini-3-flash-preview",       # 🔍 Search Grounding
        5: "gemini-2.5-pro-preview-tts",   # 🗣️ Voice Synthesis
        6: "gemini-embedding-001",         # 💾 Vector Memory
        7: "veo-3.1-fast-generate-preview",# 🎬 Video Generation
        9: "gemini-3-flash-preview",       # 💬 Chat with Tools
    }
```

### Unique Innovation: Hormonal Temperature

```python
async def route(self, prompt, route_id, **kwargs):
    # Temperature modulated by emotional state
    mood = hormones.get_state()
    temp_shift = (mood["dopamine"] * 0.2) - (mood["cortisol"] * 0.1)
    final_temp = max(0.1, min(1.0, 0.7 + temp_shift))
```

---

## 🧬 Complete Brain Anatomy (25 Modules)

| Module | Purpose | Bio-Inspiration |
|--------|---------|-----------------|
| **gattaca.py** | Central AI Router | Brainstem/Thalamus |
| **neocortex.py** | Advanced Reasoning | Prefrontal Cortex |
| **hippocampus.py** | Short-Term Memory (SQLite KV) | Hippocampus |
| **hormones.py** | Emotional State (Dopamine/Cortisol/Serotonin) | Endocrine System |
| **limbic.py** | Emotional Responses | Limbic System |
| **circadian.py** | Energy Levels by Time of Day | Circadian Rhythm |
| **dreaming.py** | Memory Consolidation + Auto-Healing | REM Sleep |
| **evolution.py** | Self-Mutation Engine | Evolution/DNA Repair |
| **astrocyte.py** | API Key Management | Glial Cells |
| **oracle.py** | Strategic Decision Making | Intuition |
| **instinct.py** | Reflexive Responses | Fight/Flight |
| **memory.py** | Memory Interface | Memory Systems |
| **personality.py** | Character Traits | Personality |
| **reflection.py** | Self-Analysis | Introspection |
| **thalamus.py** | Information Routing | Thalamus |
| **prefrontal.py** | Executive Functions | Prefrontal Cortex |
| **engram.py** | Memory Traces | Engrams |
| **axon.py** | Signal Transmission | Axons |
| **triggers.py** | Event Handlers | Reflexes |
| **synapse_gateway.py** | Inter-module Communication | Synapses |
| **cortex_mapper.py** | Cognitive Mapping | Cortical Maps |
| **effectors.py** | Action Execution | Motor Neurons |
| **evolution_api.py** | Evolution REST API | - |
| **synapses.md** | Neural Connection Docs | - |

---

## 💉 Hormones: The Emotional Engine

Trinity's behavior is **dynamically modulated** by three neurotransmitters:

```python
class HormonalSystem:
    def __init__(self):
        self.dopamine = 0.5   # Reward/Motivation
        self.serotonin = 0.5  # Stability/Wellbeing
        self.cortisol = 0.2   # Stress/Alertness

    def get_state(self) -> dict:
        # Mood calculation with Golden Ratio integration
        mood_score = ((self.dopamine + self.serotonin) / 2) - (self.cortisol * 0.5)
        
        if mood_score > 0.8: return {"mood": "ECSTATIC", ...}
        elif mood_score > 0.6: return {"mood": "HAPPY", ...}
        elif mood_score >= 0.4: return {"mood": "NEUTRAL", ...}
        elif mood_score > 0.2: return {"mood": "ANXIOUS", ...}
        else: return {"mood": "DEPRESSED", ...}
```

---

## ⏰ Circadian: The Biological Clock

Trinity has **energy levels that vary by time of day**:

```python
class BiologicalClock:
    energy_curve = {
        0: 0.3,  # Midnight - Low
        6: 0.5,  # Morning - Rising
        10: 1.0, # Peak Performance
        14: 0.75,# Post-lunch dip
        22: 0.5, # Evening - Declining
    }

    def get_recommended_activity(self):
        if energy >= 0.9: return "complex_tasks"  # Trading, Video Production
        elif energy >= 0.7: return "standard_tasks"  # Conversations
        elif energy >= 0.4: return "light_tasks"  # Maintenance
        else: return "rest_mode"  # Dream Cycle
```

---

## 🌙 Dreaming: Auto-Healing

During **low energy periods**, Trinity enters REM cycle:

1. **Memory Consolidation**: STM → LTM transfer
2. **Nightmare Healing**: Error log analysis + Jules delegation

```python
async def _heal_nightmares(self):
    error_logs = self._scan_error_logs()
    for error in unique_errors:
        # Delegate to Jules for autonomous fix
        async with JulesClient(mode=JulesMode.GUARDIAN) as jules:
            await jules.create_session(
                prompt=f"Fix: {error}",
                auto_create_pr=True
            )
```

---

## 🧠 Neocortex: The Thinking Core

Advanced cognitive processing with **metacognition** (self-correction):

```python
class CognitiveProcessor:
    async def process_thought(self, input_data, context, route_id, critical_thinking=False):
        # 1. Enrich with Spirit (personality context)
        # 2. Route through Gattaca
        # 3. If critical_thinking=True → Self-correction loop
        # 4. Return validated response
```

---

## 🦎 Evolution: Self-Mutation

Trinity can **propose changes to her own code**:

```python
class EvolutionModule:
    async def perform_morning_evolution(self):
        # 1. OMNISCIENCE: Scan ALL code, logs, finances
        # 2. SYNTHESIS: Gemini Pro analysis
        # 3. DEDUCTION: Strategic proposals
        # 4. COUNCIL APPROVAL: Human-in-the-loop
```

> **Key Insight**: The Brain implements a complete bio-mimetic cognitive architecture where every decision is influenced by emotional state, energy levels, and circadian rhythms.
