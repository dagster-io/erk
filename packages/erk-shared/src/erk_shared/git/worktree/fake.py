"""Fake worktree operations for testing.

FakeWorktree is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

import os
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktree.abc import Worktree


class FakeWorktree(Worktree):
    """In-memory fake implementation of git worktree operations.

    State Management:
    -----------------
    This fake maintains mutable state to simulate git's stateful behavior.
    Operations like add_worktree, move_worktree modify internal state.
    State changes are visible to subsequent method calls within the same test.

    Constructor Injection:
    ---------------------
    All INITIAL state is provided via constructor (immutable after construction).
    Runtime mutations occur through operation methods.
    Tests should construct fakes with complete initial state.

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - added_worktrees: Worktrees added via add_worktree()
    - removed_worktrees: Worktrees removed via remove_worktree()
    - chdir_history: Directories changed to via safe_chdir()
    """

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        existing_paths: set[Path] | None = None,
        dirty_worktrees: set[Path] | None = None,
    ) -> None:
        """Create FakeWorktree with pre-configured state.

        Args:
            worktrees: Mapping of repo_root -> list of worktrees
            existing_paths: Set of paths that should be treated as existing (for pure mode)
            dirty_worktrees: Set of worktree paths that have uncommitted/staged/untracked changes
        """
        # Use `is None` checks instead of `or` to preserve empty collections
        # Empty set is falsy, so `set() or set()` creates a new set!
        self._worktrees = worktrees if worktrees is not None else {}
        self._existing_paths = existing_paths if existing_paths is not None else set()
        self._dirty_worktrees = dirty_worktrees if dirty_worktrees is not None else set()

        # Mutation tracking
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._removed_worktrees: list[Path] = []
        self._chdir_history: list[Path] = []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository.

        Mimics `git worktree list` behavior:
        - Can be called from any worktree path or the main repo root
        - Returns the same worktree list regardless of which path is used
        - Handles symlink resolution differences (e.g., /var vs /private/var on macOS)
        """
        resolved_root = repo_root.resolve()

        # Check exact match first (with symlink resolution)
        for key, worktree_list in self._worktrees.items():
            if key.resolve() == resolved_root:
                return worktree_list

        # Check if repo_root is one of the worktree paths in any list
        for worktree_list in self._worktrees.values():
            for wt_info in worktree_list:
                if wt_info.path.resolve() == resolved_root:
                    return worktree_list

        return []

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add a new worktree (mutates internal state and creates directory)."""
        if repo_root not in self._worktrees:
            self._worktrees[repo_root] = []
        # New worktrees are never the root worktree
        self._worktrees[repo_root].append(WorktreeInfo(path=path, branch=branch, is_root=False))
        # Create the worktree directory to simulate git worktree add behavior
        path.mkdir(parents=True, exist_ok=True)
        # Add to existing paths for pure mode tests
        self._existing_paths.add(path)
        # Track the addition
        self._added_worktrees.append((path, branch))

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree (mutates internal state and simulates filesystem move)."""
        if repo_root in self._worktrees:
            for i, wt in enumerate(self._worktrees[repo_root]):
                if wt.path == old_path:
                    self._worktrees[repo_root][i] = WorktreeInfo(
                        path=new_path, branch=wt.branch, is_root=wt.is_root
                    )
                    break
        # Update existing_paths for pure test mode
        if old_path in self._existing_paths:
            self._existing_paths.discard(old_path)
            self._existing_paths.add(new_path)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree (mutates internal state)."""
        if repo_root in self._worktrees:
            self._worktrees[repo_root] = [
                wt for wt in self._worktrees[repo_root] if wt.path != path
            ]
        # Track the removal
        self._removed_worktrees.append(path)
        # Remove from existing_paths so path_exists() returns False after deletion
        self._existing_paths.discard(path)

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata (no-op for in-memory fake)."""
        pass

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name in fake data."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        return self.find_worktree_for_branch(repo_root, branch)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree has no uncommitted changes, staged changes, or untracked files."""
        # Check if path exists (LBYL pattern)
        if worktree_path not in self._existing_paths:
            return False

        # Check if worktree is marked as dirty
        if worktree_path in self._dirty_worktrees:
            return False

        return True

    def _is_parent(self, parent: Path, child: Path) -> bool:
        """Check if parent is an ancestor of child."""
        return child.is_relative_to(parent)

    def _is_sentinel_path(self, path: Path) -> bool:
        """Check if path is a SentinelPath (pure test mode).

        SentinelPath is only available in the tests package. Returns False
        if SentinelPath is not available (e.g., when used from erk-kits).
        """
        try:
            from tests.test_utils.paths import SentinelPath

            return isinstance(path, SentinelPath)
        except ImportError:
            return False

    def path_exists(self, path: Path) -> bool:
        """Check if path should be treated as existing.

        Used in erk_inmem_env to simulate filesystem checks without
        actual filesystem I/O. Paths in existing_paths are treated as
        existing even though they're sentinel paths.

        For erk_isolated_fs_env (real directories), falls back to
        checking the real filesystem for paths within known worktrees.
        """
        # First check if path is explicitly marked as existing
        if path in self._existing_paths:
            return True

        # Don't check real filesystem for sentinel paths (pure test mode)
        if self._is_sentinel_path(path):
            return False

        # For real filesystem tests, check if path is under any existing path
        for existing_path in self._existing_paths:
            try:
                # Check if path is relative to existing_path
                path.relative_to(existing_path)
                # If we get here, path is under existing_path
                # Check if it actually exists on real filesystem
                return path.exists()
            except (ValueError, OSError, RuntimeError):
                # Not relative to this existing_path or error checking, continue
                continue

        # Fallback: if no existing_paths configured and path is not under any known path,
        # check real filesystem.
        if not self._existing_paths or not any(
            self._is_parent(ep, path) for ep in self._existing_paths
        ):
            try:
                return path.exists()
            except (OSError, RuntimeError):
                return False

        return False

    def is_dir(self, path: Path) -> bool:
        """Check if path should be treated as a directory.

        For testing purposes, paths in existing_paths that represent
        git directories (.git) or worktree directories are treated as
        directories. This is used primarily for distinguishing .git
        directories (normal repos) from .git files (worktrees).

        Returns True if path exists and is likely a directory.
        """
        if path not in self._existing_paths:
            return False
        # If it's a .git path, treat it as a directory
        # (worktrees would have .git as a file, which wouldn't be in existing_paths)
        return True

    def safe_chdir(self, path: Path) -> bool:
        """Change directory if path exists, handling sentinel paths.

        For sentinel paths (pure test mode), returns False without changing directory.
        For real filesystem paths, changes directory if path exists and returns True.

        Tracks successful directory changes in chdir_history for test assertions.
        """
        # Check if path should be treated as existing
        if not self.path_exists(path):
            return False

        # Don't try to chdir to sentinel paths - they're not real filesystem paths
        if self._is_sentinel_path(path):
            # Track the attempt even for sentinel paths (tests need to verify intent)
            self._chdir_history.append(path)
            return False

        # For real filesystem paths, change directory
        os.chdir(path)
        self._chdir_history.append(path)
        return True

    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        """Get list of worktrees added during test.

        Returns list of (path, branch) tuples.
        This property is for test assertions only.
        """
        return self._added_worktrees.copy()

    @property
    def removed_worktrees(self) -> list[Path]:
        """Get list of worktrees removed during test.

        This property is for test assertions only.
        """
        return self._removed_worktrees.copy()

    @property
    def chdir_history(self) -> list[Path]:
        """Get list of directories changed to during test.

        Returns list of Path objects passed to safe_chdir().
        This property is for test assertions only.
        """
        return self._chdir_history.copy()
