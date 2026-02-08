"""
JULES/HEART.PY
══════════════════════════════════════════════════════════════════════════════
JOB: GOOGLE JULES WORKER 🤖
PURPOSE: Background worker for the Autonomous Coding Agent.
         Polls active tasks, detects PRs, and notifies the Neural Core.
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
from pathlib import Path
from loguru import logger

from jules.jules_client import (
    JulesClient,
    JulesMode,
    load_jules_tasks,
    remove_jules_task,
)
from jules.cortex import cortex
from jules.harvest import harvester
from jules.git_ops import get_pr_diff, cleanup_pr
from jules.sanitizer import CodeSanitizer
from jules.sandbox import Sandbox, SandboxResult

from social.messaging.notification_client import notify

REFINEMENT_COUNT_FILE = Path("memories/jules/refinement_counts.json")
JULES_CONFIG_FILE = Path("jules/config.json")


def _get_notify_config() -> dict:
    """Load Jules notification config from disk."""
    default = {
        "on_pr_created": True,
        "on_pr_merged": True,
        "on_council_complete": True,
        "on_mission_failed": False,
    }
    try:
        if JULES_CONFIG_FILE.exists():
            data = json.loads(JULES_CONFIG_FILE.read_text())
            return data.get("notifications", default)
    except Exception:
        pass
    return default


async def _jules_notify(event: str, message: str, actions: list = None) -> bool:
    """
    Send Jules notification if toggle is enabled.

    Args:
        event: One of 'pr_created', 'pr_merged', 'council_complete', 'mission_failed'
        message: Notification message
        actions: Optional action buttons

    Returns:
        True if notification was sent
    """
    config = _get_notify_config()
    toggle_key = f"on_{event}"

    if not config.get(toggle_key, True):
        logger.debug(f"📱 [JULES] Notification skipped: {toggle_key}=False")
        return False

    try:
        # SOTA 2026: Deduplication per event type (Standard 362.103)
        dedup_key = f"JULES_{event.upper()}"
        return await notify.jules(message, actions, dedup_key=dedup_key)
    except Exception as e:
        logger.debug(f"📱 [JULES] Notification failed: {e}")
        return False


class JulesJob:
    """Worker job for Google Jules."""

    def __init__(self):
        self.client = None
        self._running = False
        self.client = None
        self._running = False
        # self.session_retries removed -> handled by Cortex now
        self.refinement_counts = {}  # session_id -> count of feedback loops
        self._load_refinement_counts()

    def _load_refinement_counts(self):
        """Loads refinement counts from disk to persist state across restarts."""
        try:
            if REFINEMENT_COUNT_FILE.exists():
                self.refinement_counts = json.loads(REFINEMENT_COUNT_FILE.read_text())
        except Exception as e:
            logger.warning(f"Failed to load refinement counts: {e}")
            self.refinement_counts = {}

    def _save_refinement_counts(self):
        """Saves current refinement state."""
        try:
            REFINEMENT_COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
            REFINEMENT_COUNT_FILE.write_text(json.dumps(self.refinement_counts))
        except Exception as e:
            logger.error(f"Failed to save refinement counts: {e}")

    async def start(self):
        """Ignites the Jules Worker."""

        try:
            self.client = JulesClient(mode=JulesMode.GUARDIAN)
            # We don't necessarily fail here if key is missing, job just won't poll effectively
            # But JulesClient.start() raises ValueError if key missing.
            await self.client.start()
            self._running = True
            asyncio.create_task(self._watch_loop())
            logger.success("🤖 Jules online")
        except Exception as e:
            logger.warning(f"⚠️ [JULES JOB] Lobotomy (Start failed): {e}")

    async def _watch_loop(self):
        """Polls for updates on active tasks."""
        logger.debug("👀 [JULES JOB] Watchdog loop started.")

        while self._running:
            try:
                active_ids = load_jules_tasks()
                if active_ids:
                    logger.debug(f"👀 [JULES JOB] Polling {len(active_ids)} tasks...")

                for session_id in active_ids:
                    if not self.client:
                        break

                    response = await self.client.get_session(session_id)
                    if response:
                        if (
                            response.status in ["PR_OPEN", "COMPLETED"]
                            and response.pr_url
                        ):
                            # PR READY - Start event-driven flow
                            logger.info(
                                f"🧬 [JULES JOB] PR Detected: {response.pr_url}"
                            )

                            # HARVEST: Check if this is a harvest session (special handling)
                            try:
                                harvest_result = await harvester.check_and_import(
                                    session_id, response.pr_url
                                )
                                if harvest_result > 0:
                                    logger.success(
                                        f"🌾 [HARVEST] Imported {harvest_result} suggestions"
                                    )
                            except Exception as e:
                                logger.debug(f"Harvest import skipped: {e}")

                            # SAFETY CHECK (Probation)
                            if not await self.check_system_probation():
                                logger.warning("🔴 [HEART] System NOT Safe. Waiting...")
                                continue

                            # SECURITY SANITIZATION (Pre-Sandbox)
                            diff = await get_pr_diff(response.pr_url)
                            diff_preview = diff[:8000] if diff else "Diff unavailable"

                            is_safe, detected_threat = CodeSanitizer.scan_diff(diff)
                            if not is_safe:
                                logger.critical(
                                    f"🛑 [HEART] SECURITY ALERT: Malicious code detected ({detected_threat})"
                                )
                                await cleanup_pr(response.pr_url, merge=False)

                                # Notify User URGENTLY
                                payload = {
                                    "text": f"🛑 SECURITY VIOLATION: PR Rejected\n{response.pr_url}\n\n<b>Threat:</b> Detected '{detected_threat}' usage.\n<b>Policy:</b> Direct system calls are forbidden.",
                                    "buttons": [
                                        [
                                            {
                                                "text": "👀 Inspect Threat",
                                                "url": response.pr_url,
                                            }
                                        ]
                                    ],
                                }
                                await _jules_notify(
                                    "mission_failed",
                                    f"🛑 SECURITY VIOLATION: PR Rejected\n{response.pr_url}\n\nThreat: Detected '{detected_threat}' usage.\nPolicy: Direct system calls are forbidden.",
                                )

                                cortex.record_outcome(
                                    f"JULES:{response.title[:50] if response.title else session_id}",
                                    "REJECTED",
                                    f"Security Violation: {detected_threat}",
                                )
                                remove_jules_task(session_id)
                                continue

                            # SANDBOX CHECK (Feedback Loop)
                            sandbox_result = await self.run_sandbox()

                            if not sandbox_result.passed:
                                # FEEDBACK LOOP: Report error back to Jules via Cortex logic
                                # If it's a sandbox failure, we reject this attempt and log it in Cortex.
                                # The Architect will decide whether to retry based on Cortex state.

                                logger.warning(
                                    f"🧪 [HEART] Sandbox Failed: {sandbox_result.error[:200]}..."
                                )
                                await cleanup_pr(response.pr_url, merge=False)

                                # Send notification

                                payload = {
                                    "text": f"❌ PR Rejected (Sandbox Failed): {response.pr_url}\n\n<b>Error:</b>\n<pre>{sandbox_result.error[:500]}</pre>",
                                    "buttons": [
                                        [
                                            {
                                                "text": "👀 View PR",
                                                "url": response.pr_url,
                                            }
                                        ]
                                    ],
                                }
                                await _jules_notify(
                                    "mission_failed",
                                    f"❌ PR Rejected (Sandbox Failed): {response.pr_url}\n\nError: {sandbox_result.error[:300]}",
                                )

                                # Record failure in Cortex
                                signature = f"TASK:{session_id}"  # Fallback signature if we don't have the original one
                                if response.title:
                                    signature = f"JULES:{response.title[:50]}"

                                cortex.record_outcome(
                                    signature,
                                    "FAILED",
                                    f"Sandbox failure: {sandbox_result.error[:200]}",
                                )

                                remove_jules_task(session_id)
                                continue

                            # Tests Passed

                            # Tests Passed

                            # CLEANUP: If passed, reset retries for sandbox (handled by Cortex implicitly if next fails)
                            # But we might want to track this session's success

                            # TRINITY PR REVIEW (Route 1) + CONFIDENCE SCORE
                            try:
                                from corpus.brain.gattaca import gattaca
                                import re

                                # Diff already fetched by sanitizer
                                # diff = await get_pr_diff(response.pr_url)
                                # diff_preview = (
                                #     diff[:8000] if diff else "Diff unavailable"
                                # )

                                # TEST FILE CHECK: Verify tests are included for NEW CODE only
                                # SOTA 2026: Only reject if new functions/classes are added without tests
                                # Bugfixes on existing code (already covered by tests) don't need new test files
                                has_new_code = False
                                has_test_file = False

                                if diff:
                                    lines = diff.split("\n")
                                    for line in lines:
                                        # Check for test files in diff
                                        if line.startswith(
                                            "diff --git"
                                        ) or line.startswith("+++"):
                                            if "tests/" in line or "test_" in line:
                                                has_test_file = True

                                        # Check for NEW code (new functions/classes) - not just modifications
                                        if line.startswith("+") and not line.startswith(
                                            "+++"
                                        ):
                                            # Detect new function or class definitions
                                            stripped = line[1:].lstrip()
                                            if (
                                                stripped.startswith("def ")
                                                or stripped.startswith("async def ")
                                                or stripped.startswith("class ")
                                            ):
                                                # Check it's not in an exempt file (check recent diff --git lines)
                                                has_new_code = True

                                if has_new_code and not has_test_file:
                                    # REJECT: New code without tests
                                    logger.warning(
                                        "🧪 [HEART] REJECTED: New function/class added without test file"
                                    )
                                    await cleanup_pr(response.pr_url, merge=False)
                                    # SOTA 2026: Enforce test coverage with explanation

                                    payload = {
                                        "text": f"❌ PR Rejected: New Code without Tests\n{response.pr_url}\n\n<b>Policy:</b> Any new function/class must have accompanying tests.",
                                        "buttons": [
                                            [
                                                {
                                                    "text": "👀 View PR",
                                                    "url": response.pr_url,
                                                }
                                            ]
                                        ],
                                    }
                                    await _jules_notify(
                                        "mission_failed",
                                        f"❌ PR Rejected: New Code without Tests\n{response.pr_url}\n\nPolicy: Any new function/class must have accompanying tests.",
                                    )

                                    # Record for learning in Cortex
                                    signature = f"JULES:{response.title[:50] if response.title else session_id}"
                                    cortex.record_outcome(
                                        signature, "REJECTED", "New code without tests"
                                    )

                                    remove_jules_task(session_id)
                                    continue  # Skip to next session

                                logger.info(
                                    f"🧪 [HEART] Test check: new_code={has_new_code}, has_tests={has_test_file} ✓"
                                )

                                # Trinity reviews with CONFIDENCE SCORE
                                review_prompt = f"""
Tu es Trinity, le gardien du code. Review cette PR de Jules avec un SCORE DE CONFIANCE.

URL: {response.pr_url}
DIFF:
```
{diff_preview}
```

CRITÈRES:
1. Code correct et fonctionnel
2. Pas de failles de sécurité
3. Tests inclus pour les nouvelles fonctionnalités
4. Style et qualité du code

RÉPONDS AVEC CE FORMAT EXACT:
CONFIDENCE: [0-100]
VERDICT: [APPROVE/REJECT]
REASON: [explication courte]
"""
                                review = await gattaca.route(review_prompt, route_id=1)

                                # Parse confidence score
                                confidence = 70  # Default
                                if review:
                                    match = re.search(
                                        r"CONFIDENCE[:\s]*(\d+)", review.upper()
                                    )
                                    if match:
                                        confidence = min(
                                            100, max(0, int(match.group(1)))
                                        )

                                logger.info(
                                    f"📊 [HEART] Trinity Confidence: {confidence}/100"
                                )

                                # Decision logic based on confidence
                                # JULES V3: No more auto-merge, always notify user with 3 choices
                                if confidence >= 50:
                                    # SUFFICIENT CONFIDENCE: Notify user for decision
                                    logger.success(
                                        f"✅ [HEART] CONFIDENCE OK ({confidence}%) - Awaiting user decision..."
                                    )

                                    pr_id = response.pr_url.split("/")[-1]
                                    pr_title = (
                                        response.title[:60]
                                        if response.title
                                        else "Unknown"
                                    )

                                    # Extract modified files from diff
                                    modified_files = []
                                    if diff:
                                        for line in diff.split("\n"):
                                            if line.startswith("diff --git"):
                                                parts = line.split(" b/")
                                                if len(parts) > 1:
                                                    modified_files.append(parts[1])
                                    files_text = (
                                        ", ".join(modified_files[:5])
                                        if modified_files
                                        else "N/A"
                                    )
                                    if len(modified_files) > 5:
                                        files_text += f" (+{len(modified_files) - 5})"

                                    pr_desc = (
                                        response.pr_description[:200]
                                        if response.pr_description
                                        else "No description"
                                    )

                                    # JULES V3: 3 choices notification
                                    payload = {
                                        "text": f"📦 PR #{pr_id} Ready for Review\n\n📝 {pr_title}\n🎯 Confidence: {confidence}%\n📁 {files_text}\n\n💬 {pr_desc}",
                                        "buttons": [
                                            [
                                                {
                                                    "text": f"✅ Merge #{pr_id}",
                                                    "data": f"JULES_MERGE_PR_{pr_id}",
                                                },
                                                {
                                                    "text": f"⏳ Attente #{pr_id}",
                                                    "data": f"JULES_PENDING_PR_{pr_id}",
                                                },
                                                {
                                                    "text": f"❌ Refus #{pr_id}",
                                                    "data": f"JULES_REJECT_PR_{pr_id}",
                                                },
                                            ]
                                        ],
                                        "pr_url": response.pr_url,
                                        "confidence": confidence,
                                        "session_id": session_id,
                                    }
                                    await _jules_notify(
                                        "pr_created",
                                        f"🔔 Jules PR Ready for Review\n{response.pr_url}\n\nConfidence: {confidence}%\nTitle: {pr_title}",
                                        actions=[
                                            {
                                                "id": f"JULES_MERGE_{session_id}",
                                                "label": "✅ Merge",
                                                "type": "primary",
                                            },
                                            {
                                                "id": f"JULES_REJECT_{session_id}",
                                                "label": "❌ Reject",
                                                "type": "danger",
                                            },
                                        ],
                                    )

                                    # Record as waiting for decision
                                    cortex.record_outcome(
                                        f"JULES:{pr_title}",
                                        "SUCCESS",
                                        f"Ready for review with confidence {confidence}%",
                                    )
                                    logger.info(
                                        f"🔔 [HEART] Notification sent for PR #{pr_id}"
                                    )

                                else:
                                    # LOW CONFIDENCE (<50): Auto-reject + Learn
                                    logger.warning(
                                        f"❌ [HEART] LOW CONFIDENCE ({confidence}) - Auto-rejecting: {review}"
                                    )
                                    await cleanup_pr(response.pr_url, merge=False)

                                    payload = {
                                        "text": f"❌ PR Rejected (Low Confidence {confidence}%)\n{response.pr_url}\n\n<b>Reason:</b>\n{review[:500]}",
                                        "buttons": [
                                            [
                                                {
                                                    "text": "👀 View PR",
                                                    "url": response.pr_url,
                                                }
                                            ]
                                        ],
                                    }
                                    await _jules_notify(
                                        "mission_failed",
                                        f"❌ PR Rejected (Low Confidence {confidence}%)\n{response.pr_url}\n\nReason: {review[:300]}",
                                    )

                                    # FEEDBACK LOOP: Record rejection in Cortex
                                    signature = f"JULES:{response.title[:50] if response.title else session_id}"
                                    cortex.record_outcome(
                                        signature,
                                        "REJECTED",
                                        f"Low confidence ({confidence}%)",
                                    )
                                    logger.info(
                                        f"📚 [HEART] Recorded rejection in Cortex: {signature}"
                                    )

                            except Exception as e:
                                logger.error(f"🐛 [HEART] Review error: {e}")
                                # Fallback: notify user for manual approval

                                pr_id = response.pr_url.split("/")[-1]
                                payload = {
                                    "text": f"⚠️ Review failed, manual approval needed: {response.pr_url}",
                                    "buttons": [
                                        [
                                            {
                                                "text": f"✅ Approve #{pr_id}",
                                                "data": f"APPROVE_PR_{pr_id}",
                                            }
                                        ]
                                    ],
                                }
                                await _jules_notify(
                                    "pr_created",
                                    f"🔔 Jules PR Needs Manual Review\\n{response.pr_url}\\n\\nReason: Confidence score was borderline",
                                    actions=[
                                        {
                                            "id": f"APPROVE_PR_{pr_id}",
                                            "label": "✅ Approve",
                                            "type": "primary",
                                        }
                                    ],
                                )

                            if session_id in self.refinement_counts:
                                del self.refinement_counts[session_id]
                                self._save_refinement_counts()

                            remove_jules_task(session_id)

                        elif response.status == "AWAITING_PLAN_APPROVAL":
                            # PLAN APPROVAL REQUIRED (CREATOR MODE)
                            logger.info(
                                f"📋 [HEART] Plan awaiting approval: {session_id}"
                            )

                            # Fetch plan details via activities API
                            plan_summary = "Plan ready for review"
                            try:
                                activities = await self.client.get_activities(
                                    session_id, page_size=5
                                )
                                for activity in activities:
                                    if "plan" in str(activity).lower():
                                        plan_summary = str(activity)[
                                            :5000
                                        ]  # Increased limit for critique
                                        break
                            except Exception as e:
                                logger.debug(f"Could not fetch activities: {e}")

                            # 😈 SOTA 2026: PLANNING CRITIC INTERVENTION
                            # Before asking User, we ask the Critic (Gattaca)
                            current_refinements = self.refinement_counts.get(
                                session_id, 0
                            )
                            MAX_REFINEMENTS = 3

                            if current_refinements < MAX_REFINEMENTS:
                                try:
                                    from jules.planning_critic import critic

                                    # Critique the plan
                                    review = await critic.critique_plan(
                                        task_description=response.title
                                        or "Unknown Task",
                                        plan_text=plan_summary,
                                    )

                                    if not review["approved"]:
                                        logger.warning(
                                            f"😈 [CRITIC] Plan Rejected (Confidence {review['confidence']}%): {review['critique']}"
                                        )

                                        # Feedback Loop: Tell Jules to fix it
                                        await self.client.send_message(
                                            session_id,
                                            f"PLANNING CRITIC FEEDBACK: {review['improvement_prompt']}",
                                        )

                                        # Increment count
                                        self.refinement_counts[session_id] = (
                                            current_refinements + 1
                                        )
                                        self._save_refinement_counts()

                                        logger.info(
                                            f"↺ [CRITIC] Requested Refinement ({current_refinements + 1}/{MAX_REFINEMENTS})"
                                        )
                                        continue  # Skip user notification, wait for new plan

                                    else:
                                        logger.success(
                                            f"😈 [CRITIC] Plan Approved (Confidence {review['confidence']}%)"
                                        )

                                except Exception as e:
                                    logger.error(f"😈 [CRITIC] Failed to critique: {e}")

                            # Notify user with Approve button (Only if Critic Approved or Max Refinements reached)
                            payload = {
                                "text": f"📋 **Plan Approval Required**\n\nSession: {response.title or session_id}\n\n{plan_summary[:500]}...",
                                "buttons": [
                                    [
                                        {
                                            "text": "✅ Approve Plan",
                                            "data": f"JULES_APPROVE_PLAN_{session_id}",
                                        },
                                        {
                                            "text": "❌ Cancel",
                                            "data": f"JULES_REJECT_PLAN_{session_id}",
                                        },
                                    ]
                                ],
                                "session_id": session_id,
                            }
                            await _jules_notify(
                                "pr_created",
                                f"📋 Jules Plan Ready for Approval\n\n{response.review[:500] if response.review else 'No summary available'}",
                                actions=[
                                    {
                                        "id": f"JULES_APPROVE_PLAN_{session_id}",
                                        "label": "✅ Approve",
                                        "type": "primary",
                                    },
                                    {
                                        "id": f"JULES_REJECT_PLAN_{session_id}",
                                        "label": "❌ Cancel",
                                        "type": "danger",
                                    },
                                ],
                            )
                            # Don't remove task - wait for user decision

                        elif response.status == "WORKING":
                            # LIVE ACTIVITY LOGGING (optional enrichment)
                            try:
                                activities = await self.client.get_activities(
                                    session_id, page_size=3
                                )
                                if activities:
                                    latest = activities[0]
                                    logger.debug(
                                        f"🔄 [HEART] Session {session_id[:8]} activity: {str(latest)[:100]}"
                                    )
                            except Exception:
                                pass  # Silent fail for activity streaming

                        elif response.status in ["FAILED", "ERROR"]:
                            # FAILURE
                            logger.error(f"❌ [JULES JOB] Task {session_id} Failed.")

                            # JSON Payload for consistency (no buttons)

                            payload = {"text": f"❌ Jules Task Failed: {session_id}"}
                            await _jules_notify(
                                "mission_failed",
                                f"❌ Jules Task Failed: {session_id}",
                            )
                            # nerves.fire("URGENT", "JULES_FAIL", f"Jules Task Failed: {session_id}") # Fallback

                            remove_jules_task(session_id)

            except Exception as e:
                logger.error(f"🐛 [JULES JOB] Watchdog error: {e}")

            await asyncio.sleep(60)

    async def check_system_probation(self) -> bool:
        """Checks if system is in probation. Delegates to Sandbox module."""
        return await Sandbox.check_probation()

    async def run_sandbox(self) -> SandboxResult:
        """Runs tests in the sandbox. Delegates to Sandbox module."""
        return await Sandbox.run_tests()

    # Deprecated alias
    async def is_safe_to_merge(self) -> bool:
        if not await self.check_system_probation():
            return False
        res = await self.run_sandbox()
        return res.passed

    async def stop(self):
        """Stops the worker."""
        self._running = False
        if self.client:
            await self.client.close()
        logger.info("💤 [JULES JOB] Stopped.")


# Singleton Instance
heart = JulesJob()
