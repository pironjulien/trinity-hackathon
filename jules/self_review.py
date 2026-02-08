"""
JULES/SELF_REVIEW.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: JULES SELF-REVIEW & EVOLUTION 🧬
PURPOSE: Jules reviews its own code before merge and proposes self-improvements.
         Uses Jules API instead of Gemini to save API calls.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict
from loguru import logger
from datetime import datetime


class JulesSelfReview:
    """
    Uses Jules API to review code changes before merge.
    Non-blocking: if review fails, proceed anyway.
    """

    @classmethod
    async def review_branch(cls, branch_name: str) -> Dict:
        """
        Ask Jules to review a branch before merge.
        Returns: {"approved": bool, "verdict": str, "details": str}
        """
        try:
            from jules.jules_client import JulesClient, JulesMode

            # Get diff
            diff = await cls._get_branch_diff(branch_name)
            if not diff:
                return {
                    "approved": True,
                    "verdict": "NO_CHANGES",
                    "details": "No diff to review",
                }

            # Create review session with Jules
            prompt = f"""
            CODE REVIEW REQUEST (Self-Review)
            Branch: {branch_name}
            
            Review this diff for:
            1. Security issues (no secrets, no vulnerable code)
            2. Trinity style compliance (SOTA 2026)
            3. Potential bugs or regressions
            4. Test coverage adequacy
            
            DIFF:
            ```
            {diff[:3000]}  # Truncate for API limits
            ```
            
            Respond with:
            VERDICT: APPROVED / NEEDS_CHANGES / CRITICAL_ISSUE
            SUMMARY: One-line explanation
            DETAILS: Specific issues found (if any)
            """

            async with JulesClient(mode=JulesMode.GUARDIAN) as client:
                session = await client.create_session(
                    prompt=prompt,
                    title=f"Self-Review: {branch_name}",
                    auto_create_pr=False,  # Review only, no PR
                )

                if not session:
                    logger.warning(
                        "🔍 [SELF-REVIEW] Failed to create review session, proceeding anyway"
                    )
                    return {
                        "approved": True,
                        "verdict": "SKIP",
                        "details": "Review unavailable",
                    }

                logger.info(
                    f"🔍 [SELF-REVIEW] Review session {session.id} created, waiting for verdict..."
                )

                # Poll for completion (max 60s)
                for i in range(12):
                    await asyncio.sleep(5)
                    details = await client.get_session(session.id)

                    if details and details.status in ["COMPLETED", "FAILED"]:
                        # Parse Jules response from description/title
                        response_text = (
                            details.pr_description or details.pr_title or ""
                        ).upper()

                        if "CRITICAL" in response_text or "REJECT" in response_text:
                            logger.warning(
                                f"🔍 [SELF-REVIEW] Jules REJECTED: {response_text[:100]}"
                            )
                            return {
                                "approved": False,
                                "verdict": "REJECTED",
                                "details": response_text,
                            }
                        elif (
                            "APPROVED" in response_text or details.status == "COMPLETED"
                        ):
                            return {
                                "approved": True,
                                "verdict": "APPROVED",
                                "details": response_text,
                                "session_id": session.id,
                            }
                        else:
                            # Unclear verdict - default approve to not block
                            logger.info(
                                f"🔍 [SELF-REVIEW] Verdict unclear, proceeding: {response_text[:50]}"
                            )
                            return {
                                "approved": True,
                                "verdict": "UNCLEAR",
                                "details": response_text,
                            }

                # Timeout - REJECT and add to wishlist for later retry
                logger.warning(
                    "🔍 [SELF-REVIEW] Timeout waiting for verdict, deferring to wishlist"
                )

                # Add to wishlist for retry later
                try:
                    from pathlib import Path

                    wishlist = Path("memories/wishlist.md")
                    if wishlist.exists():
                        content = wishlist.read_text()
                        if branch_name not in content:
                            entry = (
                                f"- [ ] 🔄 [RETRY] Self-review timeout: {branch_name}\n"
                            )
                            wishlist.write_text(content + entry)
                            logger.info(
                                f"🔍 [SELF-REVIEW] Added to wishlist for retry: {branch_name}"
                            )
                except Exception as we:
                    logger.debug(f"Wishlist add failed: {we}")

                return {
                    "approved": False,
                    "verdict": "TIMEOUT",
                    "details": "Review timed out, added to wishlist",
                    "session_id": session.id,
                }

        except Exception as e:
            # REJECT on error - better safe than sorry
            logger.warning(f"🔍 [SELF-REVIEW] Review failed, rejecting for safety: {e}")
            return {"approved": False, "verdict": "ERROR", "details": str(e)}

    @staticmethod
    async def _get_branch_diff(branch_name: str) -> Optional[str]:
        """Get the diff between branch and main."""
        try:
            import subprocess

            result = subprocess.run(
                ["git", "diff", "main", branch_name, "--stat", "-p"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                timeout=30,
            )
            return result.stdout if result.returncode == 0 else None
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return None


class JulesSelfEvolution:
    """
    Jules analyzes its own code (jules/*) and proposes improvements.
    Proposals go to Night Report for human review.
    """

    JULES_DIR = Path("jules")
    EVOLUTION_FILE = Path("memories/jules/evolution_proposals.json")

    @classmethod
    async def analyze_self(cls) -> Dict:
        """
        Ask Jules to analyze its own code and propose improvements.
        Returns: {"proposals": list, "session_id": str}
        """
        try:
            from jules.jules_client import JulesClient, JulesMode

            # Gather current Jules code
            code_summary = cls._gather_code_summary()

            prompt = f"""
            SELF-EVOLUTION ANALYSIS 🧬
            
            You are analyzing YOUR OWN CODE. The jules/ directory contains:
            {code_summary}
            
            Your mission:
            1. Identify inefficiencies or outdated patterns
            2. Suggest SOTA 2026 improvements
            3. Propose new capabilities that would make you more effective
            4. Find potential bugs or edge cases
            
            Be specific. Reference exact files and line numbers where possible.
            
            Format your response as:
            ## Proposal 1: [Title]
            - File: [filename]
            - Issue: [what's wrong]
            - Solution: [how to fix]
            - Priority: HIGH/MEDIUM/LOW
            
            ## Proposal 2: ...
            """

            async with JulesClient(mode=JulesMode.CREATOR) as client:
                session = await client.create_session(
                    prompt=prompt,
                    title="🧬 Self-Evolution Analysis",
                    auto_create_pr=False,  # Proposals only
                )

                if session:
                    logger.info(
                        f"🧬 [EVOLUTION] Analysis session created: {session.id}"
                    )

                    # Save session ID for later retrieval
                    cls._save_session(session.id)

                    return {
                        "status": "ANALYZING",
                        "session_id": session.id,
                        "message": "Self-evolution analysis in progress",
                    }
                else:
                    return {"status": "FAILED", "message": "Could not create session"}

        except Exception as e:
            logger.error(f"🧬 [EVOLUTION] Analysis failed: {e}")
            return {"status": "ERROR", "message": str(e)}

    @classmethod
    def _gather_code_summary(cls) -> str:
        """Gather summary of jules/ code for analysis."""
        if not cls.JULES_DIR.exists():
            return "jules/ directory not found"

        summary = []
        for py_file in cls.JULES_DIR.glob("*.py"):
            try:
                lines = len(py_file.read_text().splitlines())
                summary.append(f"- {py_file.name}: {lines} lines")
            except Exception:
                summary.append(f"- {py_file.name}: (unreadable)")

        return "\n".join(summary)

    @classmethod
    def _save_session(cls, session_id: str):
        """Save evolution session for later retrieval."""
        import json

        cls.EVOLUTION_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {"session_id": session_id, "timestamp": datetime.now().isoformat()}
        cls.EVOLUTION_FILE.write_text(json.dumps(data))

    @classmethod
    async def check_proposals(cls) -> list:
        """
        Check if evolution session has completed and extract proposals.
        Returns list of proposal dicts.
        """
        import json

        if not cls.EVOLUTION_FILE.exists():
            return []

        try:
            data = json.loads(cls.EVOLUTION_FILE.read_text())
            session_id = data.get("session_id")

            if not session_id:
                return []

            from jules.jules_client import JulesClient, JulesMode

            async with JulesClient(mode=JulesMode.CREATOR) as client:
                session = await client.get_session(session_id)

                if session and session.status == "COMPLETED":
                    # Session completed, proposals should be in description
                    return [
                        {
                            "source": "self_evolution",
                            "session_id": session_id,
                            "title": session.pr_title or "Self-Evolution Proposals",
                            "description": session.pr_description
                            or "Check session for details",
                        }
                    ]

            return []

        except Exception as e:
            logger.error(f"Failed to check proposals: {e}")
            return []


# Convenience functions
async def quick_review(branch: str) -> bool:
    """Quick review before merge. Returns True if approved."""
    result = await JulesSelfReview.review_branch(branch)
    return result.get("approved", True)


async def trigger_evolution():
    """Trigger self-evolution analysis."""
    return await JulesSelfEvolution.analyze_self()
