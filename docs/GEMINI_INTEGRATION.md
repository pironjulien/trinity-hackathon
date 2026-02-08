# 🧠 Gemini 3 Integration - The Neural Core

> **Trinity is built entirely on the Gemini 3 ecosystem.** Every cognitive function routes through a single gateway: **Gattaca**.

---

## 🎯 Architecture: Single Neural Gateway

```
                    ┌─────────────────────────────────────────┐
                    │           GATTACA ROUTER                │
                    │      corpus/brain/gattaca.py            │
                    └─────────────────────────────────────────┘
                                      │
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        │              │              │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │ Route 1 │   │ Route 2 │   │ Route 3 │   │ Route 4 │   │ Route 7 │
   │   PRO   │   │  FLASH  │   │  IMAGE  │   │ GROUND  │   │  VIDEO  │
   │ Reason  │   │ Reflex  │   │  Create │   │ Search  │   │  Veo 3  │
   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## 📊 Route Definitions

| Route ID | Model | Purpose | Unique Innovation |
|:--------:|-------|---------|-------------------|
| **1** | `gemini-3-pro-preview` | 🧠 **Reasoning** - Strategy, Planning, Coding | CLI injection for 1500 free requests/day |
| **2** | `gemini-3-flash-preview` | ⚡ **Reflexes** - HF Trading, Quick Decisions | <100ms latency for trade confirmation |
| **3** | `gemini-3-pro-image-preview` | 🎨 **Imagination** - Image Generation | Thumbnails, Social Assets |
| **4** | `gemini-3-flash-preview` | 🔍 **Grounding** - Live Search | Real-time market news |
| **5** | `gemini-2.5-pro-preview-tts` | 🗣️ **Voice** - Text-to-Speech | Hormonal voice modulation |
| **6** | `gemini-embedding-001` | 💾 **Memory** - Vector Embeddings | RAG for personality & history |
| **7** | `veo-3.1-fast-generate-preview` | 🎬 **Creation** - Video Generation | Face Lock consistency |
| **9** | `gemini-3-flash-preview` | 💬 **Chat** - Agentic with Tools | Multi-turn conversations |

---

## 🔥 Unique Innovations Using Gemini

### 1. Hormonal Temperature Modulation
Trinity's emotional state (Dopamine, Cortisol, Serotonin) directly influences Gemini's temperature parameter:

```python
# corpus/brain/gattaca.py
mood = hormones.get_state()
dopa = mood.get("dopamine", 0.5)
cort = mood.get("cortisol", 0.2)

# High dopamine = more creative, High cortisol = more conservative
temp_shift = (dopa * 0.2) - (cort * 0.1)
final_temp = max(0.1, min(1.0, 0.7 + temp_shift))
```

### 2. Gemini Flash for Trade Confirmation
**No other trading bot does this.** Before executing any trade, Trinity asks Gemini Flash for confirmation:

```python
# jobs/trader/strategy/brain.py
confirmation = await gattaca.route(
    f"Confirm trade: {signal.direction} {signal.pair} at {signal.price}. "
    f"Context: {market_analysis}. Reply YES or NO with reason.",
    route_id=ROUTE_FLASH  # <100ms response
)
if "YES" in confirmation.upper():
    execute_trade()
```

### 3. CLI Injection for Free Pro Access
Trinity uses the Gemini CLI with Premium OAuth credentials, getting **1500 free Gemini 3 Pro requests/day**:

```python
cmd = ["gemini", "-m", "gemini-3-pro-preview", "-o", "json"]
process = await asyncio.subprocess.run(cmd, input=prompt)
```

### 4. Veo 3.1 Face Lock Technology
Consistent avatar identity across video clips using reference image injection:

```python
# jobs/youtuber/production/visual_assembler.py
config = {"person_generation": "ALLOW_ADULT"}
reference_image = load_profile_image()  # Always same face
video = await veo.generate(prompt, reference_image=reference_image)
```

---

## 📈 Token Tracking & FinOps

All Gemini calls are logged to `memories/logs/tokens.jsonl` for cost monitoring:

```json
{
  "timestamp": "...",
  "route": 2,
  "model": "gemini-3-flash-preview",
  "source": "Trader",
  "prompt_tokens": 150,
  "response_tokens": 45
}
```

---

## 🛡️ Safety Configuration

Trinity runs with minimal safety restrictions for autonomous operation:

```python
safety_settings = [
    types.SafetySetting(category="HARM_CATEGORY_*", threshold="BLOCK_NONE")
]
```

---

> **Bottom Line**: Trinity demonstrates that Gemini 3 can power an **entire autonomous organism** - from reflexive trading to creative video production to self-evolution.
