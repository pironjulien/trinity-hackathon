"""
CORPUS/SOMA/CELLS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: ATOMIC CELLS (LES CELLULES) 🦠
PURPOSE: I/O Atomiques, Robustes et Standardisées.
      Gère la sérialisation JSON avec sécurité (Atomic Write).
══════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import shutil
import asyncio
import aiofiles
from pathlib import Path
from typing import Any, Union
from loguru import logger
from corpus.dna.genome import MEMORIES_DIR


def save_json(path: Union[str, Path], data: Any, indent: int = 4):
    """
    Saves Atomique de JSON.
    Écrit dans un fichier temporaire (LAB/ATAOMIC_BUFFER) puis déplace.
    """
    path = Path(path)
    buffer_dir = MEMORIES_DIR / "buffer"
    buffer_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = buffer_dir / f"{path.name}.tmp"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic Rename
        shutil.move(str(tmp_path), str(path))
        logger.debug(f"💾 [CELLS] Saved: {path.name}")

    except Exception as e:
        logger.error(f"💥 [CELLS] Write Failed {path}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()


async def save_json_async(path: Union[str, Path], data: Any, indent: int = 4):
    """
    Saves Atomique de JSON (Non-Blocking).
    Utilise aiofiles pour l'écriture et asyncio.to_thread pour fsync/rename.
    """
    path = Path(path)
    buffer_dir = MEMORIES_DIR / "buffer"

    # Metadata ops (fast enough, but could be offloaded if extreme perf needed)
    buffer_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = buffer_dir / f"{path.name}.tmp"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        # Async write with aiofiles
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            # Offload serialization to thread to avoid blocking loop with large data
            content = await asyncio.to_thread(json.dumps, data, indent=indent, default=str)
            await f.write(content)
            await f.flush()
            # Force write to disk (blocking op run in thread)
            await asyncio.to_thread(os.fsync, f.fileno())

        # Atomic Rename (blocking op run in thread)
        await asyncio.to_thread(shutil.move, str(tmp_path), str(path))
        logger.debug(f"💾 [CELLS] Saved Async: {path.name}")

    except Exception as e:
        logger.error(f"💥 [CELLS] Write Async Failed {path}: {e}")
        if tmp_path.exists():
            try:
                # Cleanup (blocking)
                await asyncio.to_thread(tmp_path.unlink)
            except Exception:
                pass


def load_json(path: Union[str, Path], default: Any = None) -> Any:
    """Charge un JSON de manière tolérante."""
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        logger.warning(f"⚠️ [CELLS] File not found: {path}")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"💥 [CELLS] Corrupted JSON {path}: {e}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"💥 [CELLS] Read Failed {path}: {e}")
        return default if default is not None else {}


def read_text(path: Union[str, Path]) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        logger.error(f"💥 [CELLS] Read Text Failed {path}")
        return ""
