# 🎯 Dopamine - The Gamification Engine

> **Trinity is motivated by rewards.** Objectives, achievements, and hormonal feedback create intrinsic motivation for the organism.

---

## 🧠 Concept: Biological Gamification

Traditional gamification uses points and badges. Trinity uses **neurotransmitters**:

| Neurotransmitter | Trigger | Effect |
|------------------|---------|--------|
| **Dopamine** | Achievement unlocked | Increased creativity, risk-taking |
| **Serotonin** | Stability streaks | Long-term wellbeing, consistency |

---

## 📁 Structure

```
corpus/dopamine/
├── __init__.py
└── objectives.py  # Objective registry + GamificationManager
```

---

## 🎯 Objectives System

```python
class Objective(BaseModel):
    id: str               # "sys_uptime_86400"
    domain: str           # "TRADER", "TRINITY", "INFLUENCER"
    title: str            # "Uptime: 24 Hours"
    target_value: float   # 86400 (seconds)
    current_value: float  # Progress tracker
    reward_amount: float  # 0.0 - 1.0 intensity
    reward_type: RewardType  # DOPAMINE or SEROTONIN

    def complete(self):
        hormones.stimulate(self.reward_type, self.reward_amount)
```

---

## 🏆 Default Objectives

### Uptime Milestones (Serotonin Rewards)
| Target | Title | Reward |
|--------|-------|--------|
| 1 hour | First Steps | +0.1 |
| 6 hours | Morning Run | +0.2 |
| 24 hours | **Stability II** | +0.5 |
| 7 days | Weekly Champion | +0.8 |
| 30 days | Monthly Titan | +1.0 |

### FinOps Targets (Dopamine Rewards)
| Target | Title |
|--------|-------|
| <10€/day | Budget Watcher |
| <5€/day | Efficient Runner |
| <1€/day | Penny Pincher |
| <0.5€/day | Zero Waste |

### System Health
- **Stability Streak**: No crashes for 24h
- **Neural Efficiency**: CPU <20% for 5 min
- **Memory Optimization**: RAM <1GB for 1 hour

---

## 🔄 Integration Flow

```
Job Performance → Objective Progress → Hormonal Reward → Behavior Modifier
     ↓                    ↓                   ↓                 ↓
  Trader profit      update_objective()   stimulate()     Temperature shift
```

### Example: Trader Profit Milestone

```python
# When trader makes profit
from corpus.dopamine.objectives import manager

manager.update_objective("trader_first_profit", current_pnl)
# If target reached → hormones.stimulate("dopamine", 0.5)
# → Temperature increases → More creative trades
```

---

## 💾 Persistence

State saved to `memories/trinity/objectives_state.json`:

```json
{
    "sys_uptime_86400": {
        "status": "COMPLETED",
        "current_value": 86400
    },
    "trader_first_profit": {
        "status": "ACTIVE",
        "current_value": 42.5
    }
}
```

---

> **Key Insight**: Dopamine creates a biological feedback loop where Trinity's performance directly influences her emotional state, which in turn affects her decision-making through temperature modulation.
