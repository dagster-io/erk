"""Restack finalize operation - verify restack completed cleanly.

Validates that no rebase is in progress and working tree is clean.
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
        # Brief delay for transient file cleanup (graphite metadata, rebase temp files)
        ops.time.sleep(0.1)
        if not ops.git.is_worktree_clean(cwd):
            yield CompletionEvent(
                RestackFinalizeError(
                    success=False,
                    error_type="dirty_working_tree",
                    message="Working tree has uncommitted changes",
                    details={},
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
