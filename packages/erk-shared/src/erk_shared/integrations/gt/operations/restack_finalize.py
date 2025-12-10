"""Restack finalize operation - verify restack completed cleanly.

Validates that no rebase is in progress and working tree is clean.

Issue #2844 Investigation:
--------------------------
When running `erk pr auto-restack` with conflicts, after Claude resolves
the conflicts, this finalize step fails with "Working tree has uncommitted changes".

The bug happens reliably when there are conflicts. The hypothesis is that
after `gt continue` completes the restack, there's some state where:
- The rebase is complete (not in progress)
- But is_worktree_clean() returns False

Diagnostic information is collected when this happens:
- HEAD state (branch name or commit hash)
- Whether HEAD is detached (shell showed `git:(d168a3512) ✗` in original report)
- Which files show as dirty via `git status --porcelain`

A retry with 0.1s delay was added as a temporary fix for transient files,
but the root cause needs investigation based on the diagnostic output.

TODO for follow-up session:
1. Trigger the bug with conflicts
2. Check the error message for HEAD state, detached status, and dirty files
3. Based on that, implement proper fix (may need to handle detached HEAD,
   or specific file patterns, or wait for gt continue to fully complete)
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import (
    RestackFinalizeError,
    RestackFinalizeSuccess,
)


def execute_restack_finalize(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[RestackFinalizeSuccess | RestackFinalizeError]]:
    """Verify restack completed cleanly.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with RestackFinalizeSuccess or RestackFinalizeError.
    """
    branch_name = ops.git.get_current_branch(cwd) or "unknown"

    # Step 1: Verify no rebase in progress
    yield ProgressEvent("Checking rebase status...")
    if ops.git.is_rebase_in_progress(cwd):
        yield CompletionEvent(
            RestackFinalizeError(
                success=False,
                error_type="rebase_still_in_progress",
                message="Rebase is still in progress",
                details={},
            )
        )
        return

    # Step 2: Verify clean working tree
    # Retry once after brief delay to handle transient files from git rebase/graphite
    yield ProgressEvent("Checking working tree status...")
    if not ops.git.is_worktree_clean(cwd):
        # Diagnostic: capture git status for debugging
        import subprocess

        status_result = subprocess.run(
            ["git", "-C", str(cwd), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        head_result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Also check symbolic ref to detect detached HEAD
        symbolic_result = subprocess.run(
            ["git", "-C", str(cwd), "symbolic-ref", "-q", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        is_detached = symbolic_result.returncode != 0
        dirty_files = status_result.stdout.strip() if status_result.stdout else "(none)"
        head_state = head_result.stdout.strip() if head_result.stdout else "(unknown)"
        detached_info = "DETACHED" if is_detached else "attached"

        # Brief delay for transient file cleanup (graphite metadata, rebase temp files)
        ops.time.sleep(0.1)
        if not ops.git.is_worktree_clean(cwd):
            yield CompletionEvent(
                RestackFinalizeError(
                    success=False,
                    error_type="dirty_working_tree",
                    message=f"Working tree has uncommitted changes. HEAD={head_state} ({detached_info}), dirty_files:\n{dirty_files}",
                    details={"head_state": head_state, "dirty_files": dirty_files, "is_detached": str(is_detached)},
                )
            )
            return

    yield ProgressEvent("Restack verified successfully", style="success")
    yield CompletionEvent(
        RestackFinalizeSuccess(
            success=True,
            branch_name=branch_name,
            message="Restack completed and verified",
        )
    )
