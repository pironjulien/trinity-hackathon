"""
JOBS/TRADER/UTILS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: TRADER UTILITIES 🛠️
PURPOSE: Shared utility functions for the trader module (Atomic Writes, etc.)
══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
from pathlib import Path
from typing import Any, Union
from loguru import logger


def atomic_save_json(filepath: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Save JSON data atomically to prevent corruption.

    Strategy:
    1. Write to a temporary file in the same directory.
    2. Flush and sync to disk (fsync).
    3. Atomically replace the target file with the temporary file.

    Args:
        filepath: Target file path
        data: JSON-serializable data
        indent: JSON indentation level
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in the same directory to ensure atomic move is possible
    tmp_path = path.with_suffix(f".tmp.{os.getpid()}")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str)
            f.flush()
            os.fsync(f.fileno())  # Force write to physical disk

        # Atomic replacement
        os.replace(tmp_path, path)

    except Exception as e:
        logger.error(f"🛠️ [UTILS] Atomic save failed for {path.name}: {e}")
        # Clean up temp file if it exists
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise e
