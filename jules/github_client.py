"""
JULES GITHUB CLIENT
══════════════════════════════════════════════════════════════════════════════
Thin wrapper for GitHub operations via Jules git_ops.
Exposes functions for Jules V3 API endpoints.
══════════════════════════════════════════════════════════════════════════════
"""

from jules.git_ops import merge_pr as _merge_pr, close_pr as _close_pr


async def merge_pr(pr_url: str) -> dict:
    """
    Merge a PR via GitHub CLI.

    Args:
        pr_url: Full PR URL (e.g., https://github.com/owner/repo/pull/123)

    Returns:
        dict with status information
    """
    success = await _merge_pr(pr_url, squash=True)
    return {
        "merged": success,
        "pr_url": pr_url,
    }


async def close_pr(pr_url: str, reason: str = None) -> dict:
    """
    Close a PR without merging.

    Args:
        pr_url: Full PR URL
        reason: Optional reason for closing

    Returns:
        dict with status information
    """
    success = await _close_pr(pr_url)
    return {
        "closed": success,
        "pr_url": pr_url,
        "reason": reason,
    }
