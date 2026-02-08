"""
TESTS/TEST_ORACLE.PY
══════════════════════════════════════════════════════════════════════════════
Unit tests for The Oracle of Antithesis.
══════════════════════════════════════════════════════════════════════════════
"""

import pytest
from unittest.mock import AsyncMock, patch
from corpus.brain.oracle import oracle
from corpus.brain.gattaca import ROUTE_PRO

@pytest.mark.asyncio
async def test_generate_red_team_report_success():
    """Test successful generation and parsing of Red Team report."""

    # Mock AI Response
    mock_response = """
Here is the analysis:

---FAILURE_MODES---
1. The database might explode due to concurrency issues.
2. API rate limits will be hit immediately.

---DEVIL_ADVOCATE---
This project is redundant because a spreadsheet could do the same thing.

---BLIND_SPOTS---
The team is ignoring GDPR compliance costs.

---VERDICT---
PIVOT
"""

    with patch("corpus.brain.oracle.gattaca.route", new_callable=AsyncMock) as mock_route:
        mock_route.return_value = mock_response

        report = await oracle.generate_red_team_report(
            project_name="Project Chaos",
            description="A system to manage entropy.",
            context="High load expected."
        )

        # Assertions
        assert report["project_name"] == "Project Chaos"
        assert "database might explode" in report["failure_modes"]
        assert "spreadsheet" in report["devil_advocate"]
        assert "GDPR" in report["blind_spots"]
        assert report["verdict"] == "PIVOT"

        # Verify Gattaca was called with ROUTE_PRO
        mock_route.assert_called_once()
        args, kwargs = mock_route.call_args
        assert "Project Chaos" in args[0]
        assert kwargs["route_id"] == ROUTE_PRO

@pytest.mark.asyncio
async def test_generate_report_error_handling():
    """Test graceful handling of AI failures."""

    with patch("corpus.brain.oracle.gattaca.route", new_callable=AsyncMock) as mock_route:
        mock_route.side_effect = Exception("Neural Network Collapse")

        report = await oracle.generate_red_team_report("Project Doom", "Desc")

        assert "error" in report
        assert report["error"] == "Neural Network Collapse"
        assert report["project_name"] == "Project Doom"

def test_parse_section_robustness():
    """Test the parsing logic with messy inputs."""

    text = """
    ---FAILURE_MODES---
    Mode 1
    ---DEVIL_ADVOCATE---
    Advocate 1
    ---UNKNOWN_SECTION---
    Text
    """

    # Access private method for testing logic directly
    assert "Mode 1" in oracle._parse_section(text, "FAILURE_MODES")
    assert "Advocate 1" in oracle._parse_section(text, "DEVIL_ADVOCATE")
    assert oracle._parse_section(text, "NON_EXISTENT") == ""
