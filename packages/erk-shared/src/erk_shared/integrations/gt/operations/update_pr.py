"""Graphite update-pr workflow.

This module provides a streamlined version of the Graphite update-pr workflow.

Design goals:
- Fail fast with natural error messages
- Single linear execution flow
- No error categorization or state tracking
- Reuse existing RealGtKit operations
- Simple JSON output without complex types
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent


def execute_update_pr(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[dict]]:
    """Execute the update-pr workflow.

    Args:
        ops: GtKit operations interface.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with dict containing:
        - success: bool
        - pr_number: int (if successful)
        - pr_url: str (if successful)
        - error: str (if failed)
        - error_type: str (if failed, for specific error categories)
        - details: dict (if failed, for additional context)
    """
    # 1. Commit if uncommitted changes
    if ops.git.has_uncommitted_changes(cwd):
        yield ProgressEvent("Staging uncommitted changes...")
        try:
            ops.git.add_all(cwd)
        except subprocess.CalledProcessError:
            yield CompletionEvent({"success": False, "error": "Failed to stage changes"})
            return

        yield ProgressEvent("Committing changes...")
        try:
            ops.git.commit(cwd, "Update changes")
        except subprocess.CalledProcessError:
            yield CompletionEvent({"success": False, "error": "Failed to commit changes"})
            return
        yield ProgressEvent("Changes committed", style="success")

    # 2. Restack with conflict detection
    yield ProgressEvent("Restacking branch...")
    try:
        repo_root = ops.git.get_repository_root(cwd)
        ops.graphite.restack(repo_root, no_interactive=True, quiet=False)
    except subprocess.CalledProcessError as e:
        has_output = hasattr(e, "stdout") and hasattr(e, "stderr")
        combined_output = e.stdout + e.stderr if has_output else str(e)
        combined_lower = combined_output.lower()

        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            yield CompletionEvent(
                {
                    "success": False,
                    "error_type": "restack_conflict",
                    "error": (
                        "Merge conflict detected during restack. "
                        "Resolve conflicts manually or run 'gt restack --continue' after fixing."
                    ),
                    "details": {"stderr": e.stderr if hasattr(e, "stderr") else str(e)},
                }
            )
            return

        yield CompletionEvent(
            {
                "success": False,
                "error_type": "restack_failed",
                "error": "Failed to restack branch",
                "details": {"stderr": e.stderr if hasattr(e, "stderr") else str(e)},
            }
        )
        return
    yield ProgressEvent("Branch restacked", style="success")

    # 3. Submit update
    yield ProgressEvent("Submitting PR update...")
    try:
        ops.graphite.submit_stack(repo_root, publish=True, restack=False, quiet=False)
    except RuntimeError as e:
        error_str = str(e).lower()
        # Detect remote divergence - this requires manual resolution
        if "updated remotely" in error_str or "has been updated remotely" in error_str:
            yield CompletionEvent(
                {
                    "success": False,
                    "error_type": "remote_divergence",
                    "error": "ABORT: Branch has diverged from remote. Manual resolution required.",
                }
            )
            return
        yield CompletionEvent({"success": False, "error": f"Failed to submit update: {e}"})
        return

    # 4. Fetch PR info after submission
    yield ProgressEvent("Fetching PR info...")
    branch = ops.git.get_current_branch(cwd)
    if branch is None:
        yield CompletionEvent({"success": False, "error": "Could not determine current branch"})
        return

    pr_info = ops.github.get_pr_info_for_branch(repo_root, branch)
    if not pr_info:
        yield CompletionEvent(
            {"success": False, "error": "PR submission succeeded but failed to retrieve PR info"}
        )
        return

    pr_number, pr_url = pr_info

    yield ProgressEvent(f"PR #{pr_number} updated successfully", style="success")
    yield CompletionEvent({"success": True, "pr_number": pr_number, "pr_url": pr_url})
