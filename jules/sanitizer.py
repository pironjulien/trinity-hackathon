"""
JULES/SANITIZER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE SECURITY GATE 🛡️
PURPOSE: Scans generated code for dangerous patterns before merge.
         Blocks os.system, subprocess, eval, exec, etc.
══════════════════════════════════════════════════════════════════════════════
"""

import re
from loguru import logger


class CodeSanitizer:
    """Security Gate: Blocks dangerous patterns in generated code."""

    FORBIDDEN_REGEX = [
        r"import\s+os",
        r"from\s+os",
        r"import\s+subprocess",
        r"from\s+subprocess",
        r"import\s+shutil",
        r"from\s+shutil",
        r"import\s+sys",
        r"from\s+sys",
        r"eval\(",
        r"exec\(",
        r"__import__",
        r"os\.system",
        r"os\.popen",
    ]

    @staticmethod
    def scan_diff(diff: str) -> tuple[bool, str]:
        """
        Scans added lines in a diff for forbidden patterns using Regex.
        Returns (Passed: bool, Detection: str).
        """
        if not diff:
            return True, ""

        current_file = ""
        is_test_file = False

        for line in diff.split("\n"):
            # Detect file context from diff
            if line.startswith("+++ b/") or line.startswith("diff --git"):
                # SOTA 2026: Robust Path Detection
                parts = line.split(" b/")
                if len(parts) > 1:
                    current_file = parts[1].strip()  # Full path relative to repo root
                else:
                    current_file = line.split("/")[-1]  # Fallback

                # Allow forbidden imports in Test Files (by path or filename)
                if (
                    "tests/" in current_file
                    or "test_" in current_file.split("/")[-1]
                    or "conftest.py" in current_file
                ):
                    is_test_file = True
                else:
                    is_test_file = False
                continue

            # Check added lines only
            if line.startswith("+") and not line.startswith("+++"):
                if is_test_file:
                    continue  # Skip check for test files

                content = line[1:].strip()
                # Skip comments
                if content.startswith("#"):
                    continue

                for pattern in CodeSanitizer.FORBIDDEN_REGEX:
                    if re.search(pattern, content):
                        # Allow harmless usages if clearly mocked (heuristic)
                        if "mock" in content.lower():
                            continue
                        logger.critical(
                            f"🛡️ [SANITIZER] Blocked pattern '{pattern}' in: {content}"
                        )
                        return False, pattern

        return True, ""


# Singleton
sanitizer = CodeSanitizer()
