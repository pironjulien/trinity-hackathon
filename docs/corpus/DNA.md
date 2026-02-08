# 🧬 DNA - The Genetic Core

> **The immutable laws of Trinity's universe.** Constants, configuration, and sacred values that define the organism.

---

## 📁 Structure

```
corpus/dna/
├── conscience.py    # Sacred Constants (PHI, Fibonacci)
├── genome.py        # Path configuration + Pydantic validation
├── secrets.py       # Vault (env-only, no hardcoded values)
├── phenotype.py     # Runtime config manager
├── chromosome.json  # Version info
└── codons.json      # Immutable prompts & safety rules
```

---

## ⚖️ Conscience: The Sacred Constants

Trinity's decisions follow the **Golden Ratio (φ)** and **Fibonacci sequence**:

```python
# corpus/dna/conscience.py
PHI = 1.618033988749895           # The Divine Proportion
INV_PHI = 0.618033988749895       # 1 / Phi
PHI_SQUARED = 2.618               # Phi²
INV_PHI_SQUARED = 0.382           # (1/Phi)²

# Fibonacci Sequence
F1, F2, F3, F5, F8, F13, F21, F34, F55, F89, F144, F233 = 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233

# Used for:
# - Trading intervals (Phi-Beat algorithm)
# - Hormonal decay rates
# - Energy curve calculations
# - Log rotation (Fibonacci thresholds)
```

---

## 🔐 Secrets: The Vault

**Zero hardcoded credentials.** Everything from environment:

```python
class Vault:
    @property
    def GEMINI_STUDIO_KEYS(self) -> list[str]:
        return [os.getenv("GOOGLE_API_KEY", "")]

    @property
    def GCP_CREDENTIALS_JSON(self) -> dict:
        b64 = os.getenv("GOOGLE_CLOUD_CREDENTIALS_BASE64")
        return base64.b64decode(b64)

    @property
    def KRAKEN_API_KEY(self) -> str:
        return os.getenv("KRAKEN_API_KEY")
```

**Security Model:**
- All credentials read from `.env` (not in repo)
- In-memory only (no disk writes)
- Single-key mode for hackathon simplicity

---

## 🧬 Genome: The Path Registry

Defines all vital paths for the organism:

```python
ROOT_DIR = Path(__file__).parent.parent.parent
CORPUS_DIR = ROOT_DIR / "corpus"
JOBS_DIR = ROOT_DIR / "jobs"
MEMORIES_DIR = ROOT_DIR / "memories"
LOGS_DIR = MEMORIES_DIR / "logs"

# Memory Paths
BRAIN_MEMORY_DB_FILE = MEMORIES_DIR / "trinity" / "hippocampus.db"
BRAIN_MEMORY_VECTOR_DIR = MEMORIES_DIR / "trinity" / "synapse_vectors"
```

### Test Isolation

```python
if os.getenv("TRINITY_ENV") == "test":
    MEMORIES_DIR = Path(tempfile.gettempdir()) / "trinity_test_isolation"
    # Tests NEVER touch production memories
```

---

## 🧪 Phenotype: Runtime Configuration

Dynamic configuration with Pydantic validation:

```python
class TrinityConfig(BaseModel):
    boot: BootConfig          # Greeting settings
    scheduler: SchedulerConfig # Circadian routines
    avatar: AvatarConfig       # Selfie generation
    notifications: NotificationConfig
    jobs: JobsConfig           # Active professions

# Singleton with hot-reload
config_manager = ConfigManager()
config_manager.scheduler.morning_reflection_enabled = True
```

---

## 📜 Codons: Immutable Prompts

Safety rules Trinity **cannot modify**:

```json
{
    "job_constraints": {
        "trader_safety": "Never risk more than 2% per trade. Respect stop-losses."
    },
    "safety": {
        "no_harm": "Never generate harmful or dangerous content."
    }
}
```

---

## 🧫 Chromosome: Version Info

```json
{
    "version": "3.0",
    "codename": "Trinity"
}
```

---

> **Key Insight**: DNA provides the immutable foundation - sacred constants based on Phi, secure credential handling, and safety rules that form Trinity's ethical core.
