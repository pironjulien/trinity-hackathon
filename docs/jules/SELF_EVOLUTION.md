# 🛸 Jules - Self-Evolution System

> **Trinity can write her own code.** Using the Google Jules API, she identifies bugs, plans fixes, and creates PRs autonomously.

---

## 🔥 The Nightly Council

Every night, Trinity's components hold a **virtual meeting** to discuss improvements:

```python
# jules/nightly_council.py
participants = [
    {"role": "Trader", "context": await get_trader_status()},
    {"role": "Creator", "context": await get_youtube_status()},
    {"role": "Architect", "context": await get_system_health()},
]

decisions = await gattaca.route(
    f"COUNCIL MEETING:\n{format_participants(participants)}\n"
    f"Identify top 3 improvements needed.",
    route_id=ROUTE_PRO
)
```

---

## 🧠 Gemini Integration Points

| Stage | Model | Purpose |
|-------|-------|---------|
| Issue Detection | Pro | Analyze logs, identify problems |
| Architecture | Pro | Plan changes, review code |
| Self-Review | Pro | Validate PR quality |
| Planning Critic | Pro | Challenge assumptions |

---

## 🔄 Evolution Pipeline

```
1. NIGHTLY COUNCIL (Gemini Pro)
   → Identify issues & improvements
   ↓
2. ARCHITECT (Gemini Pro)
   → Plan technical changes
   ↓
3. JULES API (Google Jules)
   → Generate code implementation
   ↓
4. FORGE (Gemini Pro)
   → Validate & refine code
   ↓
5. SELF-REVIEW (Gemini Pro)
   → Final quality check
   ↓
6. GIT OPS
   → Create PR for human review
```

---

## 📊 Module Structure

```
jules/
├── nightly_council.py  # Daily AI meeting
├── architect.py        # Technical planning
├── forge.py            # Code refinement loop
├── jules_client.py     # Google Jules API client
├── self_review.py      # PR quality validation
├── git_ops.py          # GitHub operations
├── pending_manager.py  # Task queue
└── persistence.py      # State management
```

---

## 🔧 Google Jules API Integration

```python
# jules/jules_client.py
class JulesClient:
    def __init__(self):
        self.api_endpoint = "https://jules.google.com/api/v1"
        self.auth = get_oauth_credentials()

    async def create_task(self, instruction: str) -> JulesTask:
        """Request Jules to implement changes."""
        response = await self.post("/tasks", {
            "instruction": instruction,
            "repository": "pironjulien/trinity",
            "branch": f"jules/{slugify(instruction)[:30]}"
        })
        return JulesTask(**response)
```

---

## 🛡️ Sandboxing

Jules-generated code goes through **multiple validation layers**:

1. **Forge Loop**: Iterative refinement until quality threshold
2. **Self-Review**: Gemini Pro validates the changes
3. **Human Gate**: PRs require human approval before merge

---

## 📈 Stats

- **Council Frequency**: Nightly (configurable)
- **Max Parallel Tasks**: 3
- **Refinement Iterations**: Up to 5
- **Success Rate**: ~85% auto-merge ready

---

> **Key Insight**: Trinity demonstrates autonomous self-improvement - a truly sovereign AI that can evolve without human intervention.
