"""Idempotent squash operation - squash commits only if needed.

Squashes all commits on the current branch into one, but only if there
are 2 or more commits. If already a single commit, returns success with
no operation performed.
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.types import SquashError, SquashSuccess


def execute_squash(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[SquashSuccess | SquashError]]:
    """Execute idempotent squash.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with SquashSuccess if squash succeeded or was unnecessary,
        or SquashError if squash failed.
    """
    repo_root = ops.git.get_repository_root(cwd)

    # Step 1: Get trunk branch and count commits for progress reporting
    yield ProgressEvent("Detecting trunk branch...")
    trunk = ops.git.detect_trunk_branch(repo_root)

    yield ProgressEvent(f"Counting commits ahead of {trunk}...")
    commit_count = ops.git.count_commits_ahead(cwd, trunk)
    if commit_count == 0:
        yield CompletionEvent(
            SquashError(
                success=False,
                error="no-commits",
                message=f"No commits found ahead of {trunk}.",
            )
        )
        return

    # Step 2: Attempt squash using idempotent method
    # This handles the case where git count differs from Graphite's view
    yield ProgressEvent(f"Squashing {commit_count} commits...")
    result = ops.graphite.squash_branch_idempotent(repo_root, quiet=True)

    if result.success:
        yield ProgressEvent(result.message, style="success")
    yield CompletionEvent(result)
