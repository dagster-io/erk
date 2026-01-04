"""Restack preflight operation - squash commits and attempt restack.

Squashes all commits on the current branch, then attempts gt restack --no-interactive.
Detects conflicts and reports them for manual resolution.
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.operations.squash import execute_squash
from erk_shared.gateway.gt.types import (
    RestackPreflightError,
    RestackPreflightSuccess,
    SquashError,
)


def execute_restack_preflight(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[RestackPreflightSuccess | RestackPreflightError]]:
    """Execute restack preflight: squash + restack attempt + detect conflicts.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with RestackPreflightSuccess or RestackPreflightError.
    """
    # Get repository root
    repo_root = ops.git.get_repository_root(cwd)
    branch_name = ops.git.get_current_branch(cwd) or "unknown"

    # Step 0: Handle uncommitted changes (auto-commit)
    if not ops.git.is_worktree_clean(cwd):
        yield ProgressEvent("Auto-committing uncommitted changes...")
        ops.git.add_all(cwd)
        ops.git.commit(cwd, "WIP: auto-commit before restack")

    # Step 1: Squash commits (reuse existing squash operation)
    yield ProgressEvent("Squashing commits...")
    for event in execute_squash(ops, cwd):
        if isinstance(event, CompletionEvent):
            result = event.result
            if isinstance(result, SquashError):
                yield CompletionEvent(
                    RestackPreflightError(
                        success=False,
                        error_type="squash-failed"
                        if result.error == "squash-failed"
                        else "squash-conflict"
                        if result.error == "squash-conflict"
                        else "no-commits",
                        message=result.message,
                        details={"squash_error": result.error},
                    )
                )
                return
        else:
            yield event

    # Step 2: Attempt gt restack --no-interactive
    yield ProgressEvent("Running gt restack...")
    try:
        ops.graphite.restack(repo_root, no_interactive=True, quiet=True)
    except (subprocess.CalledProcessError, RuntimeError):
        pass  # Expected if conflicts

    # Step 3: Check for conflicts and loop until resolution or actual conflict
    # Check both is_rebase_in_progress AND conflicted files, because sometimes
    # rebase dirs get cleaned up but UU files remain (issue #2844)
    while True:
        rebase_in_progress = ops.git.is_rebase_in_progress(cwd)
        conflicts = ops.git.get_conflicted_files(cwd)

        if conflicts:
            # Actual conflicts exist - delegate to Claude
            yield ProgressEvent(f"Found {len(conflicts)} conflict(s)", style="warning")
            yield CompletionEvent(
                RestackPreflightSuccess(
                    success=True,
                    has_conflicts=True,
                    conflicts=conflicts,
                    branch_name=branch_name,
                    message=f"{len(conflicts)} conflict(s) detected",
                )
            )
            return

        if not rebase_in_progress:
            # No rebase in progress and no conflicts - we're done
            break

        # Rebase in progress but no conflicts - continue
        yield ProgressEvent("Continuing rebase...")
        ops.git.rebase_continue(cwd)

    # Rebase complete - fast path success
    yield ProgressEvent("Restack completed successfully", style="success")
    yield CompletionEvent(
        RestackPreflightSuccess(
            success=True,
            has_conflicts=False,
            conflicts=[],
            branch_name=branch_name,
            message="Restack completed successfully",
        )
    )
