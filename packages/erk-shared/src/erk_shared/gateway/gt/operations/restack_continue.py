"""Restack continue operation - stage resolved files and continue restack.

Stages resolved conflict files, runs gt continue, and checks for more conflicts.
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.types import (
    RestackContinueError,
    RestackContinueSuccess,
)


def execute_restack_continue(
    ops: GtKit,
    cwd: Path,
    resolved_files: list[str],
) -> Generator[ProgressEvent | CompletionEvent[RestackContinueSuccess | RestackContinueError]]:
    """Stage resolved files, continue restack, check for more conflicts.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).
        resolved_files: List of file paths that were resolved.

    Yields:
        ProgressEvent for status updates
        CompletionEvent with RestackContinueSuccess or RestackContinueError.
    """
    repo_root = ops.git.get_repository_root(cwd)
    branch_name = ops.git.get_current_branch(cwd) or "unknown"

    # Step 1: Stage resolved files
    yield ProgressEvent(f"Staging {len(resolved_files)} resolved file(s)...")
    try:
        ops.git.stage_files(cwd, resolved_files)
    except (subprocess.CalledProcessError, RuntimeError) as e:
        yield CompletionEvent(
            RestackContinueError(
                success=False,
                error_type="stage-failed",
                message=f"Failed to stage files: {e}",
                details={"files": ",".join(resolved_files)},
            )
        )
        return

    # Step 2: Run gt continue
    yield ProgressEvent("Continuing restack...")
    try:
        ops.graphite.continue_restack(repo_root, quiet=True)
    except (subprocess.CalledProcessError, RuntimeError):
        pass  # Expected if more conflicts

    # Step 3: Check for new conflicts
    if ops.git.is_rebase_in_progress(cwd):
        conflicts = ops.git.get_conflicted_files(cwd)
        if conflicts:
            yield ProgressEvent(f"Found {len(conflicts)} new conflict(s)", style="warning")
            yield CompletionEvent(
                RestackContinueSuccess(
                    success=True,
                    restack_complete=False,
                    has_conflicts=True,
                    conflicts=conflicts,
                    branch_name=branch_name,
                    message=f"{len(conflicts)} new conflict(s) detected",
                )
            )
        else:
            # Rebase in progress but no conflicts - this can happen if all files
            # were resolved and we need another continue
            yield ProgressEvent("No new conflicts, restack may need more iterations", style="info")
            yield CompletionEvent(
                RestackContinueSuccess(
                    success=True,
                    restack_complete=False,
                    has_conflicts=False,
                    conflicts=[],
                    branch_name=branch_name,
                    message="Rebase in progress, no new conflicts detected",
                )
            )
    else:
        yield ProgressEvent("Restack completed successfully", style="success")
        yield CompletionEvent(
            RestackContinueSuccess(
                success=True,
                restack_complete=True,
                has_conflicts=False,
                conflicts=[],
                branch_name=branch_name,
                message="Restack completed successfully",
            )
        )
