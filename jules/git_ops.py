"""
JULES/GIT_OPS.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: GIT OPERATIONS 🔧
PURPOSE: Handle PR merge, close, and branch deletion using GitHub CLI (gh).
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import os
import re
from pathlib import Path
from loguru import logger


# Load GITHUB_TOKEN from .env
def _load_github_token() -> str:
    """Load GITHUB_TOKEN from .env file."""
    # Calculate path relative to this file: jules/ -> trinity/
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("GITHUB_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                return token
    return os.environ.get("GITHUB_TOKEN", "")


GITHUB_TOKEN = _load_github_token()
REPO_ROOT = Path(__file__).resolve().parent.parent


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    # Robust ANSI escape sequence regex
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def _normalize_error_message(text: str) -> str:
    """Strip ANSI, punctuation and normalize whitespace for robust error matching."""
    clean = _strip_ansi(text)
    # Replace all non-alphanumeric characters with space to handle punctuation/format diffs
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", clean)
    # Replace all whitespace sequences (newlines, tabs, non-breaking spaces) with single space
    clean = " ".join(clean.split())
    return clean


async def run_gh_command(
    args: list, ignored_errors: list[str] = None
) -> tuple[bool, str]:
    """
    Run a GitHub CLI command and return (success, output).

    Args:
        args: List of command arguments.
        ignored_errors: List of error strings that should not trigger an error log.
    """
    try:
        # Pass GITHUB_TOKEN in environment
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = GITHUB_TOKEN

        proc = await asyncio.create_subprocess_exec(
            "gh",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_ROOT),
            env=env,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return True, stdout.decode().strip()
        else:
            err_msg = stderr.decode().strip()
            # Clean ANSI codes and normalize whitespace for checking
            err_msg_norm = _normalize_error_message(err_msg)
            should_log = True

            if ignored_errors:
                # Case-insensitive check for resilience
                # Both error message and ignored patterns are normalized (stripping punctuation)
                err_msg_lower = err_msg_norm.lower()
                for ignored in ignored_errors:
                    ignored_norm = _normalize_error_message(ignored)
                    if ignored_norm.lower() in err_msg_lower:
                        should_log = False
                        break

            if should_log:
                logger.error(f"🔧 [GIT_OPS] gh {' '.join(args)} failed: {err_msg}")

            return False, err_msg
    except Exception as e:
        logger.error(f"🔧 [GIT_OPS] Command error: {e}")
        return False, str(e)


def extract_pr_number(pr_url: str) -> str:
    """Extract PR number from URL like https://github.com/owner/repo/pull/123"""
    match = re.search(r"/pull/(\d+)", pr_url)
    return match.group(1) if match else None


async def get_pr_diff(pr_url: str) -> str:
    """Get the diff content of a PR."""
    pr_number = extract_pr_number(pr_url)
    if not pr_number:
        return ""

    success, output = await run_gh_command(["pr", "diff", pr_number])
    return output if success else ""


async def get_pr_branch(pr_url: str) -> str:
    """Get the branch name of a PR."""
    pr_number = extract_pr_number(pr_url)
    if not pr_number:
        return ""

    success, output = await run_gh_command(
        ["pr", "view", pr_number, "--json", "headRefName", "-q", ".headRefName"]
    )
    return output if success else ""


async def is_pr_merged(pr_number: str) -> bool:
    """Check if a PR is merged."""
    success, output = await run_gh_command(["pr", "view", pr_number, "--json", "state"])
    if success:
        try:
            data = json.loads(output)
            return data.get("state") == "MERGED"
        except json.JSONDecodeError:
            pass
    return False


async def merge_pr(pr_url: str, squash: bool = True) -> bool:
    """Merge a PR. Returns True on success."""
    pr_number = extract_pr_number(pr_url)
    if not pr_number:
        logger.error("🔧 [GIT_OPS] Invalid PR URL")
        return False

    args = ["pr", "merge", pr_number, "--auto", "--delete-branch"]
    if squash:
        args.append("--squash")
    else:
        args.append("--merge")

    # Specific error for protected branch rules not configured for auto-merge
    protected_branch_error = "Protected branch rules not configured for this branch"
    pr_closed_error = "Pull request is closed"

    success, output = await run_gh_command(
        args, ignored_errors=[protected_branch_error, pr_closed_error]
    )

    # Retry without --auto if failure is due to protected branch rules
    if not success:
        output_norm = _normalize_error_message(output).lower()

        # Case: PR Closed
        if "pull request is closed" in output_norm:
            logger.warning(
                f"🔧 [GIT_OPS] PR #{pr_number} is already closed. Checking status..."
            )
            if await is_pr_merged(pr_number):
                logger.success(f"🔧 [GIT_OPS] PR #{pr_number} was already merged.")
                return True
            else:
                logger.info(f"🔧 [GIT_OPS] PR #{pr_number} is closed but NOT merged.")
                return False

        # Case 1: Protected Branch Rules
        if _normalize_error_message(protected_branch_error).lower() in output_norm:
            logger.warning(
                f"🔧 [GIT_OPS] Auto-merge not configured for PR #{pr_number}. Retrying without --auto..."
            )
            args.remove("--auto")
            success, output = await run_gh_command(args)

        # Case 2: Merge Conflict / Not Mergeable (Auto-Rebase)
        elif (
            "not mergeable" in output_norm
            or "conflict" in output_norm
            or "cleanly created" in output_norm
        ):
            logger.warning(
                f"🔧 [GIT_OPS] PR #{pr_number} has conflicts. Attempting AUTO-REBASE..."
            )

            if await update_pr_branch(pr_url):
                logger.info(
                    f"🔧 [GIT_OPS] Rebase success. Retrying merge for PR #{pr_number}..."
                )
                # Give GitHub a moment to update state
                await asyncio.sleep(2)
                success, output = await run_gh_command(args)

                if success:
                    logger.success(
                        f"🔧 [GIT_OPS] PR #{pr_number} merged via auto-rebase!"
                    )
                else:
                    logger.error(
                        f"🔧 [GIT_OPS] Merge failed even after rebase: {output}"
                    )
            else:
                logger.error(
                    f"🔧 [GIT_OPS] Auto-rebase failed. Manual intervention required.\nExecute locally:\n  gh pr checkout {pr_number}\n  git merge main\n  git push"
                )

    if success:
        logger.success(f"🔧 [GIT_OPS] PR #{pr_number} merged successfully")
    return success


async def close_pr(pr_url: str) -> bool:
    """Close a PR without merging. Returns True on success."""
    pr_number = extract_pr_number(pr_url)
    if not pr_number:
        return False

    success, _ = await run_gh_command(["pr", "close", pr_number])
    if success:
        logger.info(f"🔧 [GIT_OPS] PR #{pr_number} closed")
    return success


async def delete_branch(branch_name: str) -> bool:
    """Delete a remote branch. Returns True on success."""
    if not branch_name or branch_name in ["main", "master"]:
        logger.warning(
            f"🔧 [GIT_OPS] Refusing to delete protected branch: {branch_name}"
        )
        return False

    # Delete remote branch
    # Added explicit error messages seen in production logs to avoid regex mismatches
    ignored = [
        "Reference does not exist",
        "422",
        "Not Found",
        "HTTP 422",
        "gh: Reference does not exist",
    ]
    success, output = await run_gh_command(
        [
            "api",
            "-X",
            "DELETE",
            f"repos/pironjulien/trinity/git/refs/heads/{branch_name}",
        ],
        ignored_errors=ignored,
    )

    if not success:
        # Check if it was one of the ignored errors (which means we treat it as success)
        output_norm = _normalize_error_message(output)
        output_lower = output_norm.lower()
        for err in ignored:
            # Normalize ignored pattern too
            err_norm = _normalize_error_message(err)
            if err_norm.lower() in output_lower:
                logger.info(
                    f"🔧 [GIT_OPS] Branch '{branch_name}' already deleted (or not found)"
                )
                return True

    if success:
        logger.info(f"🔧 [GIT_OPS] Branch '{branch_name}' deleted")
    return success


async def cleanup_pr(pr_url: str, merge: bool = False) -> bool:
    """Complete cleanup: close/merge PR and delete branch."""
    branch = await get_pr_branch(pr_url)

    if merge:
        success = await merge_pr(pr_url)
    else:
        success = await close_pr(pr_url)

    # Delete branch if not auto-deleted
    if branch and success:
        await delete_branch(branch)

    return success


async def update_pr_branch(pr_url: str) -> bool:
    """
    Update a PR branch with latest changes from base.
    Tries REBASE first, then falls back to MERGE if rebase fails.
    Returns True on success.
    """
    pr_number = extract_pr_number(pr_url)
    if not pr_number:
        # Try to use the arg as number if it doesn't look like a URL
        if pr_url.isdigit():
            pr_number = pr_url
        else:
            return False

    # 1. Try Rebase
    logger.info(f"🔧 [GIT_OPS] Attempting REBASE update for PR #{pr_number}...")
    success, output = await run_gh_command(
        ["pr", "update-branch", pr_number, "--rebase"]
    )

    if success:
        logger.success(f"🔧 [GIT_OPS] PR #{pr_number} updated via REBASE")
        return True

    # 2. Fallback to Merge
    logger.warning(
        f"🔧 [GIT_OPS] Rebase failed for PR #{pr_number}. Falling back to MERGE update..."
    )
    logger.debug(f"Rebase error: {output}")

    success, output = await run_gh_command(["pr", "update-branch", pr_number])

    if success:
        logger.info(f"🔧 [GIT_OPS] PR #{pr_number} updated via MERGE")
        return True

    logger.error(f"🔧 [GIT_OPS] Failed to update PR #{pr_number}: {output}")
    return False
