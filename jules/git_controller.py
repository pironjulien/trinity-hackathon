"""
LAB/GIT_CONTROLLER.PY
══════════════════════════════════════════════════════════════════════════════
MODULE: THE HAND (GIT) ✋
PURPOSE: Contrôleur Git pour manipuler le code source de l'organisme.
         Permet de récupérer, vérifier et fusionner les PRs de Jules.
══════════════════════════════════════════════════════════════════════════════
"""

import git
from pathlib import Path
from loguru import logger

# These constants appear to be for another module (Nightwatch/Architect)
# but are placed here as per the instruction's diff.
# Note: LOGS_DIR and genome.ROOT_DIR would need to be defined or imported
# for these lines to be functional in this specific file context.
# ALERTS_FILE = LOGS_DIR / "alerts.jsonl" # Commented out as LOGS_DIR is undefined
# LOCK_FILE = genome.ROOT_DIR / ".probation_lock" # Commented out as genome is undefined


class GitController:
    """Wrapper around GitPython for safe organism mutations."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        try:
            self.repo = git.Repo(repo_path)
            logger.info(f"✋ [GIT] Connected to repo at {repo_path}")
        except git.InvalidGitRepositoryError:
            logger.error(f"❌ [GIT] Invalid repository at {repo_path}")
            self.repo = None

    def get_current_branch(self) -> str:
        if not self.repo:
            return "unknown"
        return self.repo.active_branch.name

    def fetch_pr(self, pr_number: int) -> bool:
        """Fetches a PR to a local branch 'pr/123'."""
        if not self.repo:
            return False

        # Determine remote (usually 'origin')
        remote_name = "origin"
        ref_spec = f"pull/{pr_number}/head:pr/{pr_number}"

        try:
            origin = self.repo.remote(name=remote_name)
            origin.fetch(ref_spec)
            logger.info(f"⬇️ [GIT] Fetched PR #{pr_number}")
            return True
        except Exception as e:
            logger.error(f"❌ [GIT] Fetch failed: {e}")
            return False

    def checkout_pr(self, pr_number: int):
        """Checkout the PR branch."""
        branch_name = f"pr/{pr_number}"
        try:
            self.repo.git.checkout(branch_name)
            logger.success(f"🔀 [GIT] Switched to {branch_name}")
        except Exception as e:
            logger.error(f"❌ [GIT] Checkout failed: {e}")

    def merge_pr(self, pr_number: int) -> bool:
        """Merges the PR branch into the current branch (usually main)."""
        # Assumes we are on main or the target branch
        pr_branch = f"pr/{pr_number}"

        try:
            logger.info(f"🧬 [GIT] Merging {pr_branch}...")
            self.repo.git.merge(pr_branch)
            logger.success("✅ [GIT] Merge successful!")
            return True
        except git.GitCommandError as e:
            logger.error(f"💥 [GIT] Merge Conflict/Error: {e}")
            self.repo.git.merge("--abort")
            return False

    def revert_last_commit(self) -> bool:
        """
        CRITICAL: Reverts the last commit safely.
        Used by the Angel Guardian (Nightwatch) in case of system failure.
        """
        if not self.repo:
            return False

        try:
            logger.warning("↩️ [GIT] REVERT TRIGGERED! Undoing last changes...")

            # Handle dirty working tree (stashing changes)
            if self.repo.is_dirty(untracked_files=True):
                logger.warning(
                    "⚠️ [GIT] Dirty working tree detected. Stashing changes before revert..."
                )
                try:
                    self.repo.git.stash(
                        "save", "--include-untracked", "Nightwatch Auto-Revert Stash"
                    )
                    logger.success("✅ [GIT] Changes stashed.")
                except Exception as stash_error:
                    logger.error(f"❌ [GIT] Stash failed: {stash_error}")

            # Check for merge commit to add '-m 1'
            if len(self.repo.head.commit.parents) > 1:
                logger.info("↩️ [GIT] Merge commit detected. Reverting with -m 1.")
                self.repo.git.revert("HEAD", m=1, no_edit=True)
            else:
                # 'git revert HEAD --no-edit' creates a new commit that undoes changes
                self.repo.git.revert("HEAD", no_edit=True)

            # Push the revert immediately
            try:
                self.repo.git.push()
                logger.success("✅ [GIT] Revert successful & pushed. System restored.")
            except Exception as push_error:
                logger.error(
                    f"⚠️ [GIT] Revert committed locally but PUSH failed: {push_error}"
                )
                logger.warning("⚠️ [GIT] Attempting FORCE push for emergency...")
                try:
                    self.repo.git.push(force=True)
                    logger.success("✅ [GIT] FORCE PUSH SUCCESSFUL.")
                except Exception as force_error:
                    logger.critical(
                        f"❌ [GIT] FORCE PUSH FAILED. Manual intervention required. {force_error}"
                    )

            return True
        except Exception as e:
            logger.critical(f"❌ [GIT] REVERT FAILED: {e}")
            return False
