"""
TESTS/JULES/TEST_PLANNING_CRITIC.PY
══════════════════════════════════════════════════════════════════════════════
Unit tests for the PlanningCritic module.
══════════════════════════════════════════════════════════════════════════════
"""

import pytest
from unittest.mock import AsyncMock, patch
from jules.planning_critic import PlanningCritic


class TestPlanningCritic:
    """Tests for PlanningCritic.critique_plan()"""

    @pytest.mark.asyncio
    async def test_critique_returns_dict(self):
        """Critique should return a dict with required keys."""
        with patch("jules.planning_critic.gattaca") as mock_gattaca:
            mock_gattaca.route = AsyncMock(
                return_value='{"approved": true, "confidence": 85, "critique": "Good plan", "improvement_prompt": ""}'
            )
            mock_gattaca.ROUTE_PRO = 3

            result = await PlanningCritic.critique_plan(
                task_description="Add logging",
                plan_text="1. Create logger module\n2. Add log calls",
            )

            assert "approved" in result
            assert "confidence" in result
            assert "critique" in result
            assert "improvement_prompt" in result

    @pytest.mark.asyncio
    async def test_critique_approved_plan(self):
        """Good plan should be approved."""
        with patch("jules.planning_critic.gattaca") as mock_gattaca:
            mock_gattaca.route = AsyncMock(
                return_value='{"approved": true, "confidence": 90, "critique": "Solid plan", "improvement_prompt": ""}'
            )
            mock_gattaca.ROUTE_PRO = 3

            result = await PlanningCritic.critique_plan(
                task_description="Refactor auth",
                plan_text="Step 1: Extract auth logic\nStep 2: Add tests",
            )

            assert result["approved"] is True
            assert result["confidence"] >= 80

    @pytest.mark.asyncio
    async def test_critique_rejected_plan(self):
        """Bad plan should be rejected with improvement prompt."""
        with patch("jules.planning_critic.gattaca") as mock_gattaca:
            mock_gattaca.route = AsyncMock(
                return_value='{"approved": false, "confidence": 30, "critique": "Missing tests", "improvement_prompt": "Add test step"}'
            )
            mock_gattaca.ROUTE_PRO = 3

            result = await PlanningCritic.critique_plan(
                task_description="Add feature", plan_text="Just delete everything"
            )

            assert result["approved"] is False
            assert result["improvement_prompt"] != ""

    @pytest.mark.asyncio
    async def test_critique_handles_error_gracefully(self):
        """On error, should fail-safe to approval."""
        with patch("jules.planning_critic.gattaca") as mock_gattaca:
            mock_gattaca.route = AsyncMock(side_effect=Exception("API Error"))
            mock_gattaca.ROUTE_PRO = 3

            result = await PlanningCritic.critique_plan(
                task_description="Test task", plan_text="Test plan"
            )

            # Fail-safe: approve to avoid deadlock
            assert result["approved"] is True
            assert "unavailable" in result["critique"].lower()

    @pytest.mark.asyncio
    async def test_critique_parses_markdown_json(self):
        """Should handle JSON wrapped in markdown code blocks."""
        with patch("jules.planning_critic.gattaca") as mock_gattaca:
            mock_gattaca.route = AsyncMock(
                return_value='```json\n{"approved": true, "confidence": 75, "critique": "OK", "improvement_prompt": ""}\n```'
            )
            mock_gattaca.ROUTE_PRO = 3

            result = await PlanningCritic.critique_plan(
                task_description="Test", plan_text="Plan"
            )

            assert result["approved"] is True
            assert result["confidence"] == 75
