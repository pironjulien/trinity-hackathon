"""
JULES/FORGE.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE FORGE ⚒️
PURPOSE: The refinement loop. Jules receives a Mission, executes it,
         and iterates based on Quality Gate feedback until SOTA.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
from loguru import logger
from jules.jules_client import JulesClient, JulesMode, JulesSession
from jules.gate import gate
from jules.git_ops import get_pr_diff, cleanup_pr  # Legacy fallback


class TheForge:
    """
    The Factory Floor.
    Manages the lifecycle of a coding task: Draft -> Test -> Refine.
    """

    MAX_ITERATIONS = 5  # Cap to prevent loops

    def _get_architecture_map(self) -> str:
        """
        Generate a structural map of the Trinity codebase.
        Helps Jules understand where to place code.
        """
        return """
        corpus/ (VITAL - Core biological systems)
        ├── brain/
        │   ├── gattaca.py          # AI Gateway (ALL LLM calls go here)
        │   ├── neocortex.py        # High-level reasoning
        │   └── memory/             # Vector memory, compression
        ├── soma/
        │   ├── nerves.py           # Logging infrastructure
        │   └── immune.py           # Rate limiting, protection
        └── dna/
            └── genome.py           # Core constants (MEMORIES_DIR, etc.)
        
        jobs/ (PERIPHERAL - Business logic, can crash independently)
        ├── trader/
        │   ├── orchestrator.py     # Main trading loop (Phi-Beat)
        │   ├── modules/api.py      # Exchange APIs (Kraken)
        │   └── modules/risk.py     # Risk management
        ├── youtuber/
        │   ├── orchestrator.py     # Video production pipeline
        │   ├── uploader.py         # YouTube upload
        │   └── auth_manager.py     # OAuth management
        └── influencer/
            ├── orchestrator.py     # Social media automation
            └── modules/grok.py     # X/Twitter AI (Grok)
        
        tests/jobs/{job_name}/      # Tests MUST go here
        memories/{job_name}/        # State persistence (JSON)
        
        RULES:
        - Jobs import FROM corpus, never the reverse
        - Each job has orchestrator.py as entry point
        - State files go in memories/, NOT in jobs/
        """

    def _parse_files_from_diff(self, diff: str) -> list[dict]:
        """
        Extract file metadata from a unified diff.

        Returns:
            List of {"path": str, "additions": int, "deletions": int}
        """
        if not diff:
            return []

        files = []
        current_file = None
        additions = 0
        deletions = 0

        for line in diff.split("\n"):
            if line.startswith("diff --git"):
                # Save previous file stats
                if current_file:
                    files.append(
                        {
                            "path": current_file,
                            "additions": additions,
                            "deletions": deletions,
                        }
                    )
                # Extract new file path (b/path format)
                parts = line.split(" ")
                if len(parts) >= 4:
                    current_file = parts[3][2:]  # Remove 'b/' prefix
                else:
                    current_file = None
                additions = 0
                deletions = 0
            elif current_file:
                if line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

        # Don't forget last file
        if current_file:
            files.append(
                {
                    "path": current_file,
                    "additions": additions,
                    "deletions": deletions,
                }
            )

        logger.debug(f"⚒️ [FORGE] Parsed {len(files)} files from diff")
        return files

    async def forge_mission(self, mission: dict) -> dict:
        """
        Executes a mission (Project Spec) to produce a validated PR.
        Routes to Repoless sandbox if requires_repo is False.
        Returns: {'status': 'SUCCESS'/'FAILED', 'pr_url': ..., 'score': ...}
        """
        title = mission.get("title", "Untitled Mission")
        requires_repo = mission.get("requires_repo", True)  # Default: repo mode
        logger.info(f"⚒️ [FORGE] Starting mission: {title} (repo={requires_repo})")

        # REPOLESS ROUTING
        if not requires_repo:
            return await self._forge_repoless(mission)

        # 1. INITIAL DRAFT
        # Use GUARDIAN key for standard execution, or rotate if economizer impl.
        # For now, simplistic usage.
        mode = JulesMode.GUARDIAN

        # Build architecture context map
        arch_map = self._get_architecture_map()

        prompt = f"""
        CONTEXTE TRINITY (OBLIGATOIRE):
        - Architecture biomimétique: corpus/ (vital) et jobs/ (périphérique) séparés
        - SDK: google-genai v1.0+ uniquement (from google import genai)
        - Modèles: gemini-3.0-flash (vitesse), gemini-3.0-pro (raisonnement)
        - Gateway AI: Toutes les invocations LLM passent par corpus.brain.gattaca
        - Standards: Typage strict, docstrings, gestion d'erreur exhaustive
        - Tests: Obligatoires pour tout nouveau code (tests/jobs/...)
        - Interdit: os.system, imports google.generativeai (legacy)
        
        ARCHITECTURE CODEBASE (CARTE):
        {arch_map}
        
        MISSION D'EXECUTION (THE FORGE)
        
        TITRE: {title}
        DESCRIPTION: {mission.get("description")}
        CONTEXTE TECHNIQUE: {mission.get("rationale")}
        
        CONSIGNE:
        Implémente en respectant STRICTEMENT la structure existante.
        - Identifie les fichiers EXISTANTS à modifier (ne réinvente pas la roue).
        - AJOUTE DES TESTS (tests/jobs/{{job_name}}/test_*).
        - Sois SOTA: Typage strict, Docstrings, Gestion d'erreurs exhaustive.
        """

        MAX_PLAN_ATTEMPTS = 3  # Max new sessions to create for plan approval
        feedback_history = []

        for attempt in range(1, MAX_PLAN_ATTEMPTS + 1):
            # Build prompt with accumulated feedback
            full_prompt = prompt
            if feedback_history:
                feedback_section = "\n\nPREVIOUS PLAN FEEDBACK (FIX THESE ISSUES):\n"
                for i, fb in enumerate(feedback_history, 1):
                    feedback_section += f"{i}. {fb}\n"
                full_prompt = prompt + feedback_section
                logger.info(f"⚒️ [FORGE] Retry {attempt} with critic feedback")

            async with JulesClient(mode=mode) as client:
                session = await client.create_session(
                    prompt=full_prompt,
                    title=f"⚒️ Forge: {title}",
                    auto_create_pr=True,
                    require_plan_approval=True,
                )

                if not session:
                    return {"status": "FAILED", "reason": "Session creation failed"}

                # 😈 PLANNING CRITIC GATE: Validate plan before execution
                result = await self._critic_gate(client, session.id, mission)

                if result.get("approved"):
                    # Plan approved - enter refinement loop
                    return await self._refinement_loop(client, session, mission)
                else:
                    # Plan rejected - collect feedback for next attempt
                    feedback = result.get("feedback", "Improve the plan")
                    feedback_history.append(feedback)
                    logger.info(
                        f"😈 [CRITIC] Plan rejected (attempt {attempt})  — retrying"
                    )

        # All attempts exhausted
        logger.info("😈 [CRITIC] All plan attempts failed. Aborting mission.")
        return {
            "status": "FAILED",
            "reason": f"Plan rejected after {MAX_PLAN_ATTEMPTS} sessions",
        }

    async def _critic_gate(
        self, client: JulesClient, session_id: str, mission: dict
    ) -> dict:
        """
        😈 PLANNING CRITIC GATE
        Evaluates Jules' plan before code execution begins.
        Returns dict with 'approved' bool and 'feedback' if rejected.
        """
        from jules.planning_critic import critic
        import asyncio

        title = mission.get("title", "Unknown")
        logger.info("😈 [CRITIC] Waiting for plan...")

        # Wait for plan to be ready (AWAITING_PLAN_APPROVAL status)
        plan_ready = False
        for _ in range(30):  # 30 * 5s = 2.5 mins max
            session = await client.get_session(session_id)
            if session:
                logger.debug(f"😈 [CRITIC] Session status: {session.status}")
                if session.status == "AWAITING_PLAN_APPROVAL":
                    plan_ready = True
                    break
                if session.status in ["FAILED", "ERROR", "COMPLETED"]:
                    logger.warning(f"😈 [CRITIC] Session ended: {session.status}")
                    return {"approved": False, "feedback": "Session ended unexpectedly"}
            await asyncio.sleep(5)

        if not plan_ready:
            logger.warning("😈 [CRITIC] Timeout waiting for plan")
            return {"approved": False, "feedback": "Timeout waiting for plan"}

        # Fetch plan using the dedicated get_plan() method
        plan_data = await client.get_plan(session_id)
        if plan_data:
            steps = plan_data.get("steps", [])
            plan_text = "\n".join(
                f"- {s.get('title', 'Step')}: {s.get('description', '')}" for s in steps
            )
            logger.info(f"😈 [CRITIC] Got plan with {len(steps)} steps")
        else:
            plan_text = "No plan structure available"
            logger.warning("😈 [CRITIC] Could not fetch plan structure")

        # Critique the plan with Planning Critic
        review = await critic.critique_plan(title, plan_text)

        if review["approved"]:
            logger.success(
                f"😈 [CRITIC] Plan APPROVED (confidence {review['confidence']}%)"
            )
            # Use the correct approve_plan API endpoint
            approved = await client.approve_plan(session_id)
            if approved:
                logger.success("😈 [CRITIC] Plan approval sent to Jules")
                return {"approved": True, "session_id": session_id}
            else:
                logger.error("😈 [CRITIC] Failed to send plan approval")
                return {"approved": False, "feedback": "API approval failed"}
        else:
            logger.info(f"😈 [CRITIC] Plan REJECTED: {review['critique'][:100]}")
            return {
                "approved": False,
                "feedback": review["improvement_prompt"],
                "critique": review["critique"],
            }

    async def _forge_repoless(self, mission: dict) -> dict:
        """
        Execute mission in serverless sandbox (no repo, no PR).
        Uses Jules Repoless API for standalone scripts/analyses.
        """
        title = mission.get("title", "Untitled")
        logger.info(f"🔬 [FORGE] Repoless sandbox: {title}")

        prompt = f"""
        MISSION SANDBOX (REPOLESS)
        
        TITRE: {title}
        DESCRIPTION: {mission.get("description", "N/A")}
        
        CONSIGNE:
        Tu opères dans un environnement cloud éphémère avec Node, Python, Rust, Bun.
        Exécute cette tâche et retourne les résultats directement.
        Pas de PR nécessaire - output direct.
        """

        async with JulesClient() as client:
            session = await client.create_repoless_session(
                prompt=prompt, title=f"🔬 Sandbox: {title}"
            )

            if not session:
                return {
                    "status": "FAILED",
                    "reason": "Repoless session creation failed",
                }

            # Poll for completion and extract outputs
            return await self._wait_for_sandbox_output(client, session.id, title)

    async def _wait_for_sandbox_output(
        self, client: JulesClient, session_id: str, title: str
    ) -> dict:
        """Poll repoless session for completion and extract outputs."""
        import asyncio

        retries = 48  # 48 * 10s = 8 mins max
        for _ in range(retries):
            session = await client.get_session(session_id)
            if session:
                if session.status == "COMPLETED":
                    # Get outputs from session
                    outputs = await client.get_session_outputs(session_id)
                    logger.success(f"🔬 [FORGE] Sandbox completed: {title}")
                    return {
                        "status": "SUCCESS",
                        "session_id": session_id,
                        "outputs": outputs,
                        "mode": "repoless",
                    }
                if session.status == "FAILED":
                    logger.error(f"🔬 [FORGE] Sandbox failed: {title}")
                    return {"status": "FAILED", "reason": "Session failed"}
            await asyncio.sleep(10)

        return {"status": "FAILED", "reason": "Timeout waiting for sandbox"}

    async def _refinement_loop(
        self, client: JulesClient, session: JulesSession, mission: dict
    ) -> dict:
        """
        SOTA 2026 Refinement Loop with:
        - Diff-change detection (don't burn iterations on unchanged code)
        - Adaptive patience (bonus iterations when score improves)
        - Gap Analysis feedback (concrete steps to reach 90+)
        - MAX_UNCHANGED_RETRIES to prevent infinite loops
        """
        previous_diff = None
        previous_score = 0
        bonus_iterations = 0
        unchanged_retries = 0
        MAX_UNCHANGED_RETRIES = 5  # Max times we wait for unchanged diff

        iteration = 0
        while iteration < self.MAX_ITERATIONS + bonus_iterations:
            iteration += 1
            effective_max = self.MAX_ITERATIONS + bonus_iterations
            logger.info(
                f"⚒️ [FORGE] Iteration {iteration}/{effective_max} for {session.id}"
            )

            # 1. Wait for PR or Completion
            pr_url = await self._wait_for_pr(client, session.id)
            if not pr_url:
                logger.error("⚒️ [FORGE] No PR generated.")
                return {"status": "FAILED", "reason": "No PR generated"}

            # 2. Extract Diff
            diff = await self._get_diff(client, session.id, pr_url)

            # 3. DIFF-CHANGE DETECTION: Skip if unchanged
            if previous_diff and diff == previous_diff:
                unchanged_retries += 1
                logger.info(
                    f"⚒️ [FORGE] Diff unchanged - waiting for Jules update... "
                    f"(retry {unchanged_retries}/{MAX_UNCHANGED_RETRIES})"
                )

                if unchanged_retries >= MAX_UNCHANGED_RETRIES:
                    logger.warning(
                        f"⚒️ [FORGE] Max unchanged retries ({MAX_UNCHANGED_RETRIES}) reached. "
                        "Jules may be unresponsive. Aborting."
                    )
                    return {
                        "status": "FAILED",
                        "reason": f"Jules unresponsive after {MAX_UNCHANGED_RETRIES} unchanged diff cycles",
                    }

                await self._wait_for_pr_update(client, session.id, previous_diff)
                diff = await self._get_diff(client, session.id, pr_url)
                if diff == previous_diff:
                    logger.warning(
                        f"⚒️ [FORGE] Diff still unchanged after wait (retry {unchanged_retries}/{MAX_UNCHANGED_RETRIES})"
                    )
                    # Don't burn iteration - continue waiting
                    iteration -= 1
                    continue
            else:
                # Diff changed, reset retry counter
                unchanged_retries = 0

            previous_diff = diff

            # 4. PASS JUDGMENT (Quality Gate)
            judgment = await gate.evaluate(diff, str(mission))
            score = judgment["score"]
            verdict = judgment["verdict"]

            logger.info(f"⚒️ [FORGE] Judgement: {verdict} (Score: {score})")

            # 5. ADAPTIVE PATIENCE: Bonus iterations when improving
            if score > previous_score and previous_score > 0:
                improvement = score - previous_score
                if improvement >= 5:  # Significant improvement
                    bonus_iterations += 1
                    logger.info(
                        f"📈 [FORGE] Score improved +{improvement} ({previous_score}→{score}) - "
                        f"granting bonus iteration (now {self.MAX_ITERATIONS + bonus_iterations} max)"
                    )
            previous_score = score

            if verdict == "PASS":
                logger.success(f"⚒️ [FORGE] Mission Accomplished! PR Ready: {pr_url}")

                # Stage project for human review
                from jules.staging import staging

                staging.stage_project(
                    project_id=session.id,
                    title=mission.get("title", "Untitled"),
                    session_id=session.id,
                    outputs={"files": self._parse_files_from_diff(diff), "patch": diff},
                    pr_url=pr_url,
                    description=mission.get("description"),
                )

                return {
                    "status": "SUCCESS",
                    "pr_url": pr_url,
                    "score": score,
                    "session_id": session.id,
                }

            elif verdict == "TRASH":
                logger.info("⚒️ [FORGE] Code is TRASH. Aborting immediately.")
                await cleanup_pr(pr_url, merge=False)
                return {
                    "status": "FAILED",
                    "reason": f"Trash Code ({score}): {judgment['feedback']}",
                }

            else:  # REFINE
                effective_max = self.MAX_ITERATIONS + bonus_iterations
                if iteration >= effective_max:
                    logger.info(
                        f"⚒️ [FORGE] Max iterations ({effective_max}) reached. Aborting."
                    )
                    await cleanup_pr(pr_url, merge=False)
                    return {
                        "status": "FAILED",
                        "reason": f"Max iterations reached (Score: {score}/100).",
                    }

                # BUILD FEEDBACK WITH GAP ANALYSIS
                gap = judgment.get("gap_analysis", {})
                gap_section = ""
                if gap and gap.get("fixes"):
                    gap_section = "\n\n📊 GAP ANALYSIS (pour atteindre 90+):\n"
                    for fix in gap.get("fixes", []):
                        gap_section += (
                            f"  • {fix.get('action')} (+{fix.get('points', '?')} pts)\n"
                        )

                feedback = (
                    f"⚠️ TRINITY GATE FEEDBACK (Score: {score}/100)\n"
                    f"Il te manque {90 - score} points pour atteindre SOTA.\n\n"
                    f"ANALYSE:\n{judgment['feedback']}\n\n"
                    f"PROBLÈMES CRITIQUES: {judgment['critical_issues']}"
                    f"{gap_section}\n\n"
                    "Corrige ces points PRÉCIS et pousse sur la MÊME branche."
                )

                logger.info("⚒️ [FORGE] Sending feedback for refinement...")
                sent = await client.send_message(session.id, feedback)
                if not sent:
                    return {"status": "FAILED", "reason": "Communication breakdown"}

                # Wait for Jules to process (adaptive based on complexity)
                # SOTA 2026: Jules needs ~60-90s to process feedback and push
                wait_time = 90 if len(judgment.get("critical_issues", [])) > 2 else 60
                logger.info(f"⚒️ [FORGE] Waiting {wait_time}s for Jules to process...")
                await asyncio.sleep(wait_time)

        return {"status": "FAILED", "reason": "Unknown Error"}

    async def _wait_for_pr_update(
        self,
        client: JulesClient,
        session_id: str,
        previous_diff: str,
        timeout: int = 120,
    ) -> bool:
        """
        Wait for the PR to be updated (new commits pushed).
        Returns True if diff changed, False if timeout.
        """
        import time

        start = time.time()
        while time.time() - start < timeout:
            s = await client.get_session(session_id)
            if s and s.pr_url:
                new_diff = await self._get_diff(client, session_id, s.pr_url)
                if new_diff != previous_diff:
                    logger.info("⚒️ [FORGE] Detected PR update!")
                    return True
            await asyncio.sleep(15)
        return False

    async def _wait_for_pr(self, client: JulesClient, session_id: str) -> str:
        """Polls until PR is created or session fails."""
        # SOTA 2026: Extended timeout for complex projects (90 min max)
        retries = 540  # 540 * 10s = 90 mins wait max
        for i in range(retries):
            s = await client.get_session(session_id)
            if s:
                if s.pr_url:
                    return s.pr_url
                if s.status == "FAILED":
                    return None
            # Log every 5 minutes to show progress
            if i > 0 and i % 30 == 0:
                logger.info(f"⏳ [FORGE] Still waiting for PR... ({i * 10}s elapsed)")
            await asyncio.sleep(10)
        logger.warning("⏰ [FORGE] Timeout waiting for PR after 90 minutes")
        return None

    async def _get_diff(self, client: JulesClient, session_id: str, pr_url: str) -> str:
        """
        Get diff from session activities (SOTA 2026).

        CRITICAL: session.outputs does NOT contain the actual patch.
        The real diff is in activities[].artifacts[].changeSet.gitPatch.unidiffPatch.
        Falls back to gh CLI if Activities API unavailable.
        """
        # SOTA 2026: Use Activities API for real unidiff
        patch = await client.get_git_patch(session_id)
        if patch:
            logger.debug(
                f"⚒️ [FORGE] Got GitPatch from Activities API ({len(patch)} chars)"
            )
            return patch

        # Fallback to legacy gh CLI method
        logger.warning(
            "⚒️ [FORGE] Activities API returned no patch, falling back to gh CLI"
        )
        return await get_pr_diff(pr_url)


# Singleton
forge = TheForge()
