# 🧬 SYNAPSES - Neural Routing Map
# ═══════════════════════════════════════════════════════════════════════════════
# Updated: Feb 2026 | Routes 1-8 (100% Gemini 3 / Standard Compliant)
# ═══════════════════════════════════════════════════════════════════════════════

> [!CAUTION]
> **CORE DIRECTIVE**: This map is the LAW. `corpus/brain/gattaca.py` is the ONLY valid implementation of these routes.

## 📊 ROUTES SUMMARY (1-8 SCHEMA SOTA 2026)

| # | Name | Model | Use Case |
|:--|:-----|:------|:---------|
| **1** | **PRO** | **gemini-3-pro-preview** | Deep Reasoning |
| **2** | **FLASH** | **gemini-3-flash-preview** | Fast Reasoning |
| **3** | **VISION** | **gemini-3-pro-preview** | Image Understanding |
| **4** | **IMAGE** | **gemini-3-pro-image-preview** | Native Image Generation |
| **5** | **GROUNDING**| **gemini-3-flash-preview** | Live Knowledge / Facts |
| **6** | **MEMORY**| **gemini-embedding-001** | Semantic RAG |
| **7** | **VIDEO** | **veo-3.1-fast-generate-preview** | Video Gen Fast |
| **8** | **VIDEO_PRO** | **veo-3.1-generate-preview** | Video Gen Pro |
| **9** | **CHAT** | **gemini-3-flash-preview** | Agentic (Tools) |

---

## 🔑 AUTHENTICATION STRATEGY

### Route 1 (PRO) - Official CLI
Uses the official Google `gemini` CLI tool with standard `gcloud auth login` OAuth authentication.

```python
# Official Google Gemini CLI with gcloud OAuth
import subprocess

result = subprocess.run(
    ["gemini", "-m", "gemini-3-pro-preview", "-o", "json"],
    input=prompt.encode(),
    capture_output=True,
    env={**os.environ, "GOOGLE_GENAI_USE_GCA": "true"}
)
```

### Routes 2-8 - Standard API
Uses the official `google-genai` SDK with API key authentication.

---

## 📋 DETAILED ROUTES

### 🧠 ROUTE 1 (PRO)
**Model**: `gemini-3-pro-preview`
Deep reasoning for complex strategy decisions.

### ⚡ ROUTE 2 (FLASH)
**Model**: `gemini-3-flash-preview`
Latency-optimized for real-time responses.

### 👁️ ROUTE 3 (VISION)
**Model**: `gemini-3-pro-preview` (with image input)
Image understanding and visual analysis.

### 🎨 ROUTE 4 (IMAGE)
**Model**: `gemini-3-pro-image-preview`
Native image generation for thumbnails and assets.

### 🔍 ROUTE 5 (GROUNDING)
**Model**: `gemini-3-flash-preview` + `google_search` tool
Live knowledge with real-time search.

### 💾 ROUTE 6 (MEMORY)
**Model**: `gemini-embedding-001`
Semantic embeddings for RAG memory.

### 🎬 ROUTE 7 (VIDEO)
**Model**: `veo-3.1-fast-generate-preview`
Fast video generation with native audio.

### 🎥 ROUTE 8 (VIDEO_PRO)
**Model**: `veo-3.1-generate-preview`
High-quality video generation.

---

## 🔧 TECHNICAL IMPLEMENTATION

### SDK
```python
google-genai >= 1.56.0  # Unified Gemini SDK
```

### Async Pattern
```python
from google import genai

response = await client.aio.models.generate_content(
    model="gemini-3-pro-preview",
    contents=prompt
)
```

---

## 📦 MODELS USED

```
gemini-3-flash-preview
gemini-3-pro-preview
gemini-3-pro-image-preview
gemini-embedding-001
veo-3.1-fast-generate-preview
veo-3.1-generate-preview
```

---

## 🧠 IMPLEMENTATION FILE

Main implementation: `corpus/brain/gattaca.py`
- `gattaca` singleton instance
- Async routes with `client.aio.models.*`
- 100% Gemini 3 Family
