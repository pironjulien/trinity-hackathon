"""
CORPUS/BRAIN/EVOLUTION_API.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: Evolution Report API
PURPOSE: Endpoint to retrieve the latest evolution report for 8810 UI
ARCH: Biological Naming Convention Compliant
══════════════════════════════════════════════════════════════════════════════
"""

import json
import glob
from typing import Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

from corpus.dna.genome import MEMORIES_DIR


router = APIRouter(prefix="/api/evolution", tags=["evolution"])


class EvolutionReportResponse(BaseModel):
    """Response model for evolution report endpoint."""

    hasReport: bool
    date: Optional[str] = None
    summary: Optional[str] = None
    analysisPreview: Optional[str] = None


@router.get("/latest", response_model=EvolutionReportResponse)
async def get_latest_evolution_report() -> EvolutionReportResponse:
    """
    Retrieve the latest evolution report.
    Returns metadata for the 8810 UI sentinel button.
    """
    try:
        # Find all evolution reports
        report_dir = MEMORIES_DIR / "trinity"
        pattern = str(report_dir / "evolution_report_*.json")
        reports = sorted(glob.glob(pattern), reverse=True)

        if not reports:
            return EvolutionReportResponse(hasReport=False)

        # Get the most recent report
        latest_path = Path(reports[0])

        # Extract date from filename (evolution_report_YYYY-MM-DD.json)
        filename = latest_path.stem  # evolution_report_2026-02-01
        date_str = filename.replace("evolution_report_", "")

        # Check if it's from today (only show recent reports)
        today = datetime.now().strftime("%Y-%m-%d")
        is_today = date_str == today

        # Read the report content
        with open(latest_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Extract summary/analysis preview
        analysis = report.get("analysis", "")
        if isinstance(analysis, str):
            analysis_preview = (
                analysis[:300] + "..." if len(analysis) > 300 else analysis
            )
        else:
            analysis_preview = str(analysis)[:300]

        # Get roadmap summary if available
        roadmap = report.get("evolution_roadmap", [])
        if roadmap and isinstance(roadmap, list):
            summary = f"📋 {len(roadmap)} objectifs pour aujourd'hui"
        else:
            summary = "Rapport d'évolution disponible"

        return EvolutionReportResponse(
            hasReport=True,
            date=date_str,
            summary=summary if is_today else f"Dernier rapport: {date_str}",
            analysisPreview=analysis_preview,
        )

    except Exception as e:
        logger.error(f"🧬 [EVOLUTION_API] Failed to read report: {e}")
        return EvolutionReportResponse(hasReport=False)
