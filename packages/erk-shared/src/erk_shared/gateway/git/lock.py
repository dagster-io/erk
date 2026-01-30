"""Git index lock waiting utilities.

This module provides utilities for handling git's index.lock file, which is
per-worktree (not repository-wide). Each worktree has its own index stored in
its admin directory.

Note: What IS shared across worktrees is refs and the object database. Ref
lockfiles can cause contention when updating the same branch from multiple
worktrees, but the index itself is per-worktree.
"""

import subprocess
from pathlib import Path

from erk_shared.gateway.time.abc import Time

# Feature flag: set to False to disable index lock waiting
INDEX_LOCK_WAITING_ENABLED = True


def get_lock_path(repo_root: Path) -> Path | None:
    """Get the index.lock path for this worktree using git rev-parse.

    Uses `git rev-parse --git-path index.lock` to let git correctly resolve
    the lock file path for any repository layout (normal repos, worktrees,
    or custom GIT_DIR configurations).

    Args:
        repo_root: Repository or worktree root directory

    Returns:
        Absolute path to the index.lock file for this worktree, or None if not
        in a git repo.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-path", "index.lock"],
        check=False,
        capture_output=True,
        text=True,
    )
    # LBYL: Check returncode explicitly instead of using exception for control flow
    if result.returncode != 0:
        # Not a git repository or git not available
        return None
    lock_path_str = result.stdout.strip()
    # git rev-parse may return relative paths - resolve them against repo_root
    lock_path = Path(lock_path_str)
    if lock_path.is_absolute():
        return lock_path
    return repo_root / lock_path


def wait_for_index_lock(
    repo_root: Path,
    time: Time,
    *,
    max_wait_seconds: float = 5.0,
    poll_interval: float = 0.5,
) -> bool:
    """Wait for index.lock to be released.

    When multiple git operations run concurrently in the same worktree, they
    can conflict on the index.lock file. This function waits with polling
    until the lock is released or timeout occurs.

    Note: The index.lock is per-worktree, not repository-wide. Operations in
    different worktrees do NOT share the same index.lock.

    Args:
        repo_root: Repository root directory
        time: Time provider for testability (use context.time or RealTime)
        max_wait_seconds: Maximum time to wait before giving up
        poll_interval: Time between lock file checks

    Returns:
        True if lock was released (or never existed), False if timed out.
        Always returns True if INDEX_LOCK_WAITING_ENABLED is False or if
        not in a git repository.
    """
    if not INDEX_LOCK_WAITING_ENABLED:
        return True

    lock_path = get_lock_path(repo_root)
    if lock_path is None:
        # Not a git repo, nothing to wait for
        return True

    elapsed = 0.0

    while lock_path.exists() and elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

    return not lock_path.exists()
