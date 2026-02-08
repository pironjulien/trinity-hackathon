# 🫀 Soma - The Body Systems

> **The organism's infrastructure.** Nerves, senses, immune system, and vital functions that keep Trinity alive.

---

## 📁 Structure (10 Modules)

```
corpus/soma/
├── nerves.py      # Logging + Pub/Sub Signals (276 lines)
├── reserves.py    # Treasury/FinOps (771 lines)
├── immune.py      # Health Check (132 lines)
├── senses.py      # Web Perception (150 lines)
├── voice.py       # TTS Larynx (139 lines)
├── cells.py       # Atomic JSON I/O (112 lines)
├── hygiene.py     # Cleanup routines
├── organelles.py  # Small utilities
├── sentinel.py    # Cloud monitoring
└── __init__.py
```

---

## 🧠 Nerves: The Logging System

**Pub/Sub architecture** for real-time log streaming:

```python
class SignalLevel(str, Enum):
    PAIN = "PAIN"        # Errors
    PLEASURE = "PLEASURE" # Successes
    ALERT = "ALERT"      # Warnings
    INFO = "INFO"
    DEBUG = "DEBUG"

class NervesSystem:
    def fire(self, signal: str, level: str, message: str):
        # Notify all subscribers
        for callback in self._subscribers:
            callback({"signal": signal, "level": level, "message": message})
```

### Features:
- **JSONL routing**: Logs → module-specific files (trader.jsonl, angel.jsonl)
- **Alerts extraction**: WARNING/ERROR/CRITICAL → alerts.jsonl
- **Token logging**: All Gemini usage → tokens.jsonl
- **Auto-rotation**: Fibonacci-based size limits

---

## 💰 Reserves (Treasury): FinOps System

**771 lines** - The largest soma module. Manages financial awareness:

```python
class Treasury:
    async def get_financial_summary(self):
        return {
            "capital_trading": self._get_trader_profit(),
            "gcp_credits": self._get_gcp_credits(),
            "daily_burn": await self._calculate_daily_burn_rate(),
            "survival_days": credits / daily_burn
        }
```

### Data Sources:
- **BigQuery**: Real-time GCP billing
- **Portfolio.json**: Trading capital
- **metrics.bin**: System health (binary format)

### Key Feature: Hormonal Stress Response
```python
if survival_days < 7:
    hormones.stimulate("cortisol", 0.5)  # Financial stress
```

---

## 🛡️ Immune: Health Check

System diagnostics via **metrics.bin** (binary format for speed):

```python
async def check_vitals(self):
    # Read from metrics.bin (12 doubles = 96 bytes)
    data = struct.unpack("dddddddddddd", f.read(96))
    # Returns: sys_cpu, sys_ram, sys_disk, angel_cpu/ram, trinity_cpu/ram...

    if disk > 90:
        await instinct.sense_threat("resource_pressure", severity=0.9)
```

### Code Quality Scan:
```python
async def scan(self):
    subprocess.run(["uv", "run", "ruff", "check", "."])
    subprocess.run(["uv", "run", "pyright", "corpus/brain"])
```

---

## 👁️ Senses: Web Perception

Trinity can **read the internet**:

```python
class Senses:
    async def read_url(self, url: str) -> str:
        # HTTP GET with aiohttp

    async def scan_rss(self, feed_url: str) -> List[Dict]:
        # Parse RSS/Atom feeds
        # Returns: [{title, link, summary}, ...]
```

---

## 🗣️ Voice (Larynx): TTS

Text-to-speech via **Gattaca routes**:

```python
class Larynx:
    async def speak(self, text: str, fast: bool = False):
        route = ROUTE_LIVE if fast else ROUTE_VOICE
        # ROUTE_VOICE: gemini-2.5-pro-preview-tts (quality)
        # ROUTE_LIVE: flash native audio (speed)
        return await gattaca.route(text, route_id=route)
```

---

## 🦠 Cells: Atomic I/O

**Crash-safe JSON operations**:

```python
def save_json(path, data):
    # 1. Write to temp buffer
    # 2. os.fsync() force to disk
    # 3. Atomic rename (shutil.move)
```

Also provides `save_json_async()` for non-blocking writes.

---

> **Key Insight**: Soma provides the life support systems - logging that feels like a nervous system, financial awareness that triggers stress responses, and immune systems that scan for code "pathogens".
