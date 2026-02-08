"""
TESTS/JULES/TEST_SANITIZER.PY
══════════════════════════════════════════════════════════════════════════════
Unit tests for the CodeSanitizer module.
══════════════════════════════════════════════════════════════════════════════
"""

import pytest
from jules.sanitizer import CodeSanitizer


class TestCodeSanitizer:
    """Tests for CodeSanitizer.scan_diff()"""

    def test_empty_diff_passes(self):
        """Empty diff should pass."""
        passed, threat = CodeSanitizer.scan_diff("")
        assert passed is True
        assert threat == ""

    def test_safe_code_passes(self):
        """Normal Python code should pass."""
        diff = """
diff --git a/utils.py b/utils.py
+++ b/utils.py
+def hello():
+    return "world"
+
+class MyClass:
+    pass
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is True

    def test_os_import_blocked(self):
        """os import should be blocked."""
        diff = """
diff --git a/malicious.py b/malicious.py
+++ b/malicious.py
+import os
+os.system("rm -rf /")
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is False
        assert "os" in threat.lower()

    def test_subprocess_blocked(self):
        """subprocess import should be blocked."""
        diff = """
diff --git a/evil.py b/evil.py
+++ b/evil.py
+from subprocess import run
+run(["echo", "pwned"])
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is False
        assert "subprocess" in threat.lower()

    def test_eval_blocked(self):
        """eval() should be blocked."""
        diff = """
diff --git a/bad.py b/bad.py
+++ b/bad.py
+result = eval(user_input)
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is False
        assert "eval" in threat.lower()

    def test_exec_blocked(self):
        """exec() should be blocked."""
        diff = """
diff --git a/bad.py b/bad.py
+++ b/bad.py
+exec(code_string)
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is False
        assert "exec" in threat.lower()

    def test_test_files_allowed(self):
        """Test files can use forbidden imports."""
        diff = """
diff --git a/tests/test_utils.py b/tests/test_utils.py
+++ b/tests/test_utils.py
+import os
+import subprocess
+# These are allowed in test files
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is True

    def test_conftest_allowed(self):
        """conftest.py can use forbidden imports."""
        diff = """
diff --git a/tests/conftest.py b/tests/conftest.py
+++ b/tests/conftest.py
+import os
+import sys
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is True

    def test_comments_ignored(self):
        """Comments mentioning forbidden patterns should pass."""
        diff = """
diff --git a/utils.py b/utils.py
+++ b/utils.py
+# Note: don't use os.system here
+# subprocess is forbidden
+def safe_function():
+    pass
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is True

    def test_mocked_patterns_allowed(self):
        """Mock usages of forbidden patterns should pass."""
        diff = """
diff --git a/utils.py b/utils.py
+++ b/utils.py
+mock_os_system = MagicMock()
+with patch("os.system") as mock:
+    pass
"""
        passed, threat = CodeSanitizer.scan_diff(diff)
        assert passed is True
