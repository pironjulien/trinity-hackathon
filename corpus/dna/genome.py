"""
CORPUS/DNA/GENOME.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: CONFIG LOADER (L'ADN) 🧬
PURPOSE: Charge la configuration statique avec validation stricte (Pydantic).
      Définit les chemins vitaux.
══════════════════════════════════════════════════════════════════════════════
"""

import os  # SOTA 2026: Env support
import sys
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from loguru import logger

# VITALS PATHS
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
JOBS_DIR = ROOT_DIR / "jobs"

# SOTA 2026: Fundamental Isolation
# If TRINITY_ENV is 'test', we switch to a disposable memory cortex.
TRINITY_ENV = os.getenv("TRINITY_ENV", "dev").lower()

if TRINITY_ENV == "test":
    # Use a specific isolation directory for tests (can be cleaned up or temp)
    # This prevents ANY test from ever touching production memories.
    import tempfile

    # Check if we are in a pytest session that set a temporary dir via conftest
    # If not, create one.
    MEMORIES_DIR = Path(tempfile.gettempdir()) / "trinity_test_isolation"
    MEMORIES_DIR.mkdir(exist_ok=True)

    # Replicate structure for safety
    (MEMORIES_DIR / "trader").mkdir(exist_ok=True)
    (MEMORIES_DIR / "trinity").mkdir(exist_ok=True)
    (MEMORIES_DIR / "logs").mkdir(exist_ok=True)

    logger.warning(
        f"🧬 [GENOME] TEST MODE DETECTED. Memories redirected to: {MEMORIES_DIR}"
    )

else:
    MEMORIES_DIR = ROOT_DIR / "memories"

CORPUS_DIR = ROOT_DIR / "corpus"
SENSES_DIR = ROOT_DIR / "senses"
SOCIAL_DIR = ROOT_DIR / "social"  # NEW: Interface layer
SOCIAL_ASSETS_DIR = SOCIAL_DIR / "assets"  # NEW: Shared Assets (Faces, Logos)
LOGS_DIR = MEMORIES_DIR / "logs"

# Legacy alias (backward compatibility)
PROFESSIONS_DIR = JOBS_DIR

# MEMORY PATHS (inside memories/trinity/ for coherence)
BRAIN_MEMORY_DB_FILE = MEMORIES_DIR / "trinity" / "hippocampus.db"
BRAIN_MEMORY_VECTOR_DIR = MEMORIES_DIR / "trinity" / "synapse_vectors"


class TrinityConfig(BaseModel):
    """
    Validation stricte de la Configuration ADN.
    """

    env: str = Field(default="dev", description="Environment (dev/prod)")
    project_name: str = "Trinity"
    version: str = "0.0.0"  # Loaded from chromosome.json
    codename: str = "Unknown"

    # SOTA Standards
    async_timeout: float = 30.0
    debug_mode: bool = False


# Chromosome path (genetic info)
CHROMOSOME_FILE = CORPUS_DIR / "dna" / "chromosome.json"


class Genome:
    """
    Le Loader de Configuration.
    """

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> TrinityConfig:
        try:
            # Load version info from chromosome.json
            import json

            chromosome_data = {}
            if CHROMOSOME_FILE.exists():
                with open(CHROMOSOME_FILE, "r", encoding="utf-8") as f:
                    chromosome_data = json.load(f)

            return TrinityConfig(
                version=chromosome_data.get("version", "0.0.0"),
                codename=chromosome_data.get("codename", "Unknown"),
            )
        except ValidationError as e:
            logger.critical(f"🧬 [GENOME] Mutation Detected (Config Error): {e}")
            sys.exit(1)
        except Exception as e:
            logger.warning(f"🧬 [GENOME] Chromosome read failed: {e}")
            return TrinityConfig()

    @property
    def ROOT_DIR(self) -> Path:
        """Expose ROOT_DIR as property for robustness."""
        return ROOT_DIR


# Singleton
genome = Genome()
