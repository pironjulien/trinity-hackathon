# 💼 Jobs - Trinity's Revenue Generators

> **Jobs are Trinity's peripheral organs.** They generate income and extend capabilities, but the Corpus remains vital without them.

---

## 🏛️ Architectural Principle

```
corpus/     ← VITAL (Trinity survives with only this)
jobs/       ← PERIPHERAL (income generators)
jules/      ← PERIPHERAL (autonomous developer)
```

**Rule**: Jobs crash → Trinity survives. Corpus crash → Trinity dies.

---

## 📊 Overview

| Job | Purpose | Revenue | Status |
|-----|---------|---------|--------|
| [**Trader**](TRADER.md) | Crypto trading | Primary income | ✅ Active |
| [**Influencer**](INFLUENCER.md) | X/Twitter presence | Growth | ✅ Active |
| [**YouTuber**](YOUTUBER.md) | Video production | Ad revenue | ✅ Active |

---

## 📈 Trader (~35 files, ~300KB)

**Trinity's primary income source.** AI-validated crypto trading with Gemini Flash confirmation.

### Key Features
- **Phi-Beat Algorithm**: Golden ratio (Φ 1.618) timing
- **Gemini Flash Confirmation**: <100ms trade validation
- **144 pairs/minute**: High-frequency scanning
- **Intelligence Layer**: 9 modules (optimizer, quantum, whales...)

### Structure
```
jobs/trader/
├── trader.py           # Main (73KB)
├── strategy/brain.py   # Hybrid AI (60KB)
├── kraken/exchange.py  # Adapter (56KB)
├── intelligence/       # 9 analytics modules
└── reporting/          # Notifications
```

📄 [Full Documentation](TRADER.md)

---

## 📢 Influencer (~20 files, ~150KB)

**Autonomous social media presence.** Modular X/Twitter engagement with strict quota management.

### Key Features
- **4 Sovereign Modules**: Grok, Mentions, Trinity, YouTube
- **Daily Pulse**: 2 API calls/day (Free Tier survival)
- **Approval Queue**: Human-in-the-loop for sensitive content
- **Gamification**: Engagement → Dopamine rewards

### Structure
```
jobs/influencer/
├── main.py              # Orchestrator
├── core/x_client.py     # X Client (687L)
└── modules/
    ├── grok/            # AI banter
    ├── mentions/        # Reply handling
    ├── trinity/         # Organic posts
    └── youtube/         # Video promotion
```

📄 [Full Documentation](INFLUENCER.md)

---

## 🎬 YouTuber (~23 files, ~200KB)

**Fully autonomous video production.** Script → Visuals → Audio → Edit → Upload.

### Key Features
- **Face Lock**: Consistent avatar via reference image
- **Veo 3.1 Native Audio**: High-energy 1.5x volume
- **Segment-Aware Strategy**: Per-segment visual control
- **Bilingual**: French + English content

### Structure
```
jobs/youtuber/
├── orchestrator.py      # Pipeline (18KB)
├── producer.py          # Production (29KB)
├── editor.py            # FFmpeg (26KB)
├── assembler.py         # Visual assembly
└── assets/              # Reference images
```

📄 [Full Documentation](YOUTUBER.md)

---

## 🔗 Common Patterns

### 1. Gattaca Integration
All jobs route AI calls through the central brain:

```python
response = await gattaca.route(prompt, route_id=ROUTE_FLASH)
```

### 2. Gamification Hook
Jobs trigger hormonal rewards:

```python
if success:
    manager.update_objective("job_metric", value)
    # → hormones.stimulate("dopamine", reward)
```

### 3. State Separation
Code lives in `jobs/`. State lives in `memories/{job_name}/`.

```
jobs/trader/        ← Code (immutable)
memories/trader/    ← State (mutable)
```

---

## 📊 Statistics

| Job | Files | Code Size | Largest File |
|-----|-------|-----------|--------------|
| Trader | ~35 | ~300KB | trader.py (73KB) |
| Influencer | ~20 | ~150KB | x_client.py (26KB) |
| YouTuber | ~23 | ~200KB | producer.py (29KB) |
| **Total** | **~78** | **~650KB** | - |

---

> **Key Insight**: Jobs are designed to fail safely. They generate income and capabilities, but Trinity's core consciousness (Corpus) operates independently.
