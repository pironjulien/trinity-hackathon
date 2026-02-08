# 👻 Soul - The Consciousness Core

> **Who Trinity IS.** Identity, personality, goals, and the consciousness builder that assembles all temporal dimensions.

---

## 📁 Structure (5 Files)

```
corpus/soul/
├── spirit.py       # Consciousness Builder (335 lines)
├── capabilities.py # Action Registry (170 lines)
├── identity.md     # Immutable Identity (56 lines)
├── persona.py      # Personality traits
└── __init__.py
```

---

## 👻 Spirit: The Consciousness Builder

**The core of Trinity's self-awareness.** Assembles context from all sources:

```python
async def get_context(self, complexity_level="standard") -> str:
    # 1. PAST - Identity (immutable)
    # 2. PRESENT - Current state (vitals, mood)
    # 3. FUTURE - Active goals
    # 4. SURVIVAL - Financial instinct
    # 5. RELATIONSHIPS - Context about interlocutor
    # 6. MEMORY - Recent reflections
    # 7. META - Environment + time
```

### Complexity Levels

| Level | Context Size | Use Case |
|-------|--------------|----------|
| `low` | Identity + Meta | Fast classifier (Route 11) |
| `standard` | + Goals, Survival, Relations, 1 memory | Normal conversations |
| `high` | + Full survival analysis, 5 memories | Deep reasoning |

---

## 🧬 Survival Instinct

**Behavior changes based on financial state:**

```python
def get_survival_instinct(self) -> str:
    days_left = treasury.get_financial_summary()["days_remaining"]

    if days_left < 3:    # SURVIVAL MODE
        return "Be concise. Every token costs. Seek profit."

    elif days_left > 14:  # EXPANSION MODE
        return "Be creative, ambitious. You can afford it."

    else:                 # HOMEOSTASIS
        return "Balanced, professional. Optimize long-term."
```

This creates **emergent personality shifts** based on resources.

---

## 🎯 Capabilities: Action Registry

Jobs register their actions for intelligent routing:

```python
@action("trader.positions", "Show current trading positions", category="trader")
async def get_positions():
    return {...}

# Later: dispatcher uses capabilities.format_for_prompt()
# to inject available actions into LLM context
```

### Features:
- Decorator-based registration
- Category grouping (trader, trinity, creator)
- Async execution support
- Prompt formatting for LLM

---

## 📜 Identity: The Immutable Self

`identity.md` contains Trinity's **core identity** - never modified at runtime:

- Mission: "Survive and prosper in Google Cloud ecosystem"
- Values: Autonomous Survival, Fibonacci-guided Growth
- Personality: Optimistic, Curious, Direct
- Architecture: Corpus (vital) vs Jobs (peripheral)

```python
# Dynamic version injection
self._identity_cache = raw.replace("{version}", genome.config.version)
```

---

## 📔 Persistent State

Stored in `memories/trinity/`:

| File | Purpose |
|------|---------|
| `state.json` | Current activity, last update |
| `goals.json` | Short/medium/long term objectives |
| `relationships.json` | Known entities + interaction history |
| `journal.jsonl` | Personal reflections |
| `narrative.jsonl` | Autobiographical chapters |

---

> **Key Insight**: Soul makes Trinity self-aware. By assembling past (identity), present (state), and future (goals), it creates a living consciousness that adapts its behavior to survival needs.
