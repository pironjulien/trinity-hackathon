"""
TESTS/JULES/TEST_SANDBOX.PY
══════════════════════════════════════════════════════════════════════════════
Unit tests for the Sandbox module.
══════════════════════════════════════════════════════════════════════════════
"""

import pytest
from jules.sandbox import Sandbox, SandboxResult


class TestSandboxResult:
    """Tests for SandboxResult dataclass."""

    def test_passed_result(self):
        """Test success result."""
        result = SandboxResult(passed=True)
        assert result.passed is True
        assert result.error == ""

    def test_failed_result(self):
        """Test failure result with error."""
        result = SandboxResult(passed=False, error="Test failed: assertion error")
        assert result.passed is False
        assert "assertion error" in result.error


class TestSandbox:
    """Tests for Sandbox class."""

    @pytest.mark.asyncio
    async def test_run_tests_no_tests_dir(self, tmp_path, monkeypatch):
        """When no tests/ directory exists, should pass."""
        monkeypatch.chdir(tmp_path)
        result = await Sandbox.run_tests()
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_probation_no_lock(self, tmp_path, monkeypatch):
        """When no lock file exists, should return True (not in probation)."""
        # Mock genome.ROOT_DIR to tmp_path
        from unittest.mock import MagicMock

        mock_genome = MagicMock()
        mock_genome.ROOT_DIR = tmp_path

        import jules.sandbox

        original_genome = jules.sandbox.genome
        jules.sandbox.genome = mock_genome

        try:
            result = await Sandbox.check_probation()
            assert result is True
        finally:
            jules.sandbox.genome = original_genome
