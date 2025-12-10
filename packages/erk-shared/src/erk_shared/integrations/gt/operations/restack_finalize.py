"""Restack finalize operation - verify restack completed cleanly.

Validates that no rebase is in progress and working tree is clean.

Issue #2844 Root Cause (FOUND):
-------------------------------
When `gt continue` is run after conflict resolution, if there are still
unresolved conflicts (UU files), the rebase-merge directory gets cleaned up
but HEAD remains detached and unmerged files remain. This leaves git in
a broken state where:
- is_rebase_in_progress() returns False (no rebase dirs)
- is_worktree_clean() returns False (UU/staged files exist)
- HEAD is detached (pointing to commit hash, not branch)

The fix: Check for unmerged files (UU status) specifically and give a
helpful error message directing the user to resolve remaining conflicts.
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

    # Step 2: Check for unmerged files (UU status) - indicates incomplete conflict resolution
    # This happens when gt continue runs but conflicts weren't fully resolved
    yield ProgressEvent("Checking for unresolved conflicts...")
    import subprocess

    status_result = subprocess.run(
        ["git", "-C", str(cwd), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    status_lines = status_result.stdout.strip().split("\n") if status_result.stdout.strip() else []

    # Parse status output to find unmerged files (UU, AA, DD, AU, UA, DU, UD)
    unmerged_prefixes = ("UU", "AA", "DD", "AU", "UA", "DU", "UD")
    unmerged_files = [line[3:] for line in status_lines if line[:2] in unmerged_prefixes]

    if unmerged_files:
        # There are still unresolved conflicts - this is the root cause of issue #2844
        conflict_count = len(unmerged_files)
        conflict_list = "\n".join(f"  - {f}" for f in unmerged_files)
        msg = (
            f"Restack incomplete: {conflict_count} file(s) still have "
            f"unresolved conflicts:\n{conflict_list}\n\n"
            "Resolve these conflicts, then run `gt continue` to complete the restack."
        )
        yield CompletionEvent(
            RestackFinalizeError(
                success=False,
                error_type="unresolved_conflicts",
                message=msg,
                details={"unmerged_files": ",".join(unmerged_files)},
            )
        )
        return

    # Step 3: Verify clean working tree
    # Retry once after brief delay to handle transient files from git rebase/graphite
    yield ProgressEvent("Checking working tree status...")
    if not ops.git.is_worktree_clean(cwd):
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
            msg = (
                f"Working tree has uncommitted changes. "
                f"HEAD={head_state} ({detached_info}), dirty_files:\n{dirty_files}"
            )
            yield CompletionEvent(
                RestackFinalizeError(
                    success=False,
                    error_type="dirty_working_tree",
                    message=msg,
                    details={
                        "head_state": head_state,
                        "dirty_files": dirty_files,
                        "is_detached": str(is_detached),
                    },
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
