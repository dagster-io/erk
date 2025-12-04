"""Idempotent squash operation - squash commits only if needed.

Squashes all commits on the current branch into one, but only if there
are 2 or more commits. If already a single commit, returns success with
no operation performed.
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import SquashError, SquashSuccess


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

    # Step 1: Get trunk branch
    yield ProgressEvent("Detecting trunk branch...")
    trunk = ops.git.detect_trunk_branch(repo_root)

    # Step 2: Count commits
    yield ProgressEvent(f"Counting commits ahead of {trunk}...")
    commit_count = ops.git.count_commits_ahead(cwd, trunk)
    if commit_count == 0:
        error: SquashError = {
            "success": False,
            "error": "no_commits",
            "message": f"No commits found ahead of {trunk}.",
        }
        yield CompletionEvent(error)
        return

    # Step 3: If already single commit, return success with no-op
    if commit_count == 1:
        yield ProgressEvent("Already a single commit, no squash needed.", style="success")
        result: SquashSuccess = {
            "success": True,
            "action": "already_single_commit",
            "commit_count": 1,
            "message": "Already a single commit, no squash needed.",
        }
        yield CompletionEvent(result)
        return

    # Step 4: Squash commits
    yield ProgressEvent(f"Squashing {commit_count} commits...")
    try:
        ops.graphite.squash_branch(repo_root, quiet=True)
    except subprocess.CalledProcessError as e:
        combined = (e.stdout if hasattr(e, "stdout") else "") + (
            e.stderr if hasattr(e, "stderr") else ""
        )
        if "conflict" in combined.lower():
            conflict_error: SquashError = {
                "success": False,
                "error": "squash_conflict",
                "message": "Merge conflicts detected during squash.",
            }
            yield CompletionEvent(conflict_error)
            return
        stderr = e.stderr if hasattr(e, "stderr") else ""
        fail_error: SquashError = {
            "success": False,
            "error": "squash_failed",
            "message": f"Failed to squash: {stderr.strip()}",
        }
        yield CompletionEvent(fail_error)
        return

    yield ProgressEvent(f"Squashed {commit_count} commits into 1.", style="success")
    success: SquashSuccess = {
        "success": True,
        "action": "squashed",
        "commit_count": commit_count,
        "message": f"Squashed {commit_count} commits into 1.",
    }
    yield CompletionEvent(success)
