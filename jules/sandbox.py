"""
JULES/SANDBOX.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE SANDBOX 🧪
PURPOSE: Test execution environment for validating generated code.
         Runs pytest and checks system probation status.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from loguru import logger

from corpus.dna import genome


class SandboxResult:
    """Result of a sandbox execution."""

    def __init__(self, passed: bool, error: str = ""):
        self.passed = passed
        self.error = error


class Sandbox:
    """Test execution sandbox for Jules-generated code."""

    @staticmethod
    async def run_tests() -> SandboxResult:
        """
        Runs tests in the sandbox. Returns result with stdout/stderr.
        """
        tests_dir = Path("tests")
        if not tests_dir.exists():
            return SandboxResult(True)  # No tests to run

        logger.debug("🧪 [SANDBOX] Running Tests...")
        try:
            # SOTA 2026: Block Shell Execution (RCE Fix)
            # Use exec with explicit argument list instead of shell=True
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path.cwd())  # Ensure root is in path for imports

            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pytest",
                "tests/",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = f"STDOUT:\n{stdout.decode()[:1000]}\n\nSTDERR:\n{stderr.decode()[:1000]}"
                return SandboxResult(False, error_msg)

            logger.success("✅ [SANDBOX] Tests PASSED.")
            return SandboxResult(True)

        except Exception as e:
            logger.error(f"⚠️ [SANDBOX] Execution Error: {e}")
            return SandboxResult(False, str(e))

    @staticmethod
    async def check_probation() -> bool:
        """Checks if system is in probation (lock file)."""
        LOCK_FILE = genome.ROOT_DIR / ".probation_lock"

        if LOCK_FILE.exists():
            # SOTA 2026: Dynamic Timeout based on last confidence
            dynamic_timeout = 600
            try:
                conf_file = Path("memories/jules/.last_confidence")
                if conf_file.exists():
                    last_conf = int(conf_file.read_text())
                    dynamic_timeout = max(0, int(600 * (1 - ((last_conf - 50) / 50))))
            except Exception:
                pass

            lock_age = time.time() - LOCK_FILE.stat().st_mtime
            if lock_age > dynamic_timeout:
                try:
                    LOCK_FILE.unlink()
                except Exception:
                    pass
            else:
                return False
        return True


# Singleton
sandbox = Sandbox()
