"""Git index lock waiting utilities.

This module provides utilities for handling git's index.lock file, which is
repository-wide and can cause conflicts when multiple operations run concurrently
across worktrees.
"""

from pathlib import Path

from erk_shared.gateway.time.abc import Time

# Feature flag: set to False to disable index lock waiting
INDEX_LOCK_WAITING_ENABLED = True


def get_git_dir(repo_root: Path) -> Path:
    """Get actual .git directory, following worktree indirection.

    For worktrees, the `.git` path is a file containing a gitdir pointer
    to the real .git directory. The index.lock file lives in the main
    repository's .git directory, not the worktree-specific subdirectory.

    Args:
        repo_root: Repository or worktree root directory

    Returns:
        Path to the main .git directory where index.lock lives
    """
    git_path = repo_root / ".git"

    if not git_path.exists():
        # No .git at all - return what we have
        return git_path

    if git_path.is_file():
        # Worktree: .git contains "gitdir: /path/to/real/.git/worktrees/name"
        content = git_path.read_text(encoding="utf-8").strip()
        if content.startswith("gitdir: "):
            worktree_git = Path(content[8:])
            # index.lock is in the main .git, not worktree subdir
            # Structure: .git/worktrees/<name> -> go up two levels to get .git
            if worktree_git.exists():
                return worktree_git.parent.parent

    # Either a normal .git directory or couldn't resolve worktree
    return git_path


def wait_for_index_lock(
    repo_root: Path,
    time: Time,
    *,
    max_wait_seconds: float = 5.0,
    poll_interval: float = 0.5,
) -> bool:
    """Wait for index.lock to be released.

    When multiple git operations run concurrently across worktrees, they can
    conflict on git's repository-wide index.lock. This function waits with
    polling until the lock is released or timeout occurs.

    Args:
        repo_root: Repository root directory
        time: Time provider for testability (use context.time or RealTime)
        max_wait_seconds: Maximum time to wait before giving up
        poll_interval: Time between lock file checks

    Returns:
        True if lock was released (or never existed), False if timed out.
        Always returns True if INDEX_LOCK_WAITING_ENABLED is False.
    """
    if not INDEX_LOCK_WAITING_ENABLED:
        return True

    git_dir = get_git_dir(repo_root)
    lock_path = git_dir / "index.lock"
    elapsed = 0.0

    while lock_path.exists() and elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

    return not lock_path.exists()
