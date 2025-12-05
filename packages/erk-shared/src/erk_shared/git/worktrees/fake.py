"""Fake git worktree operations for testing."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees


class FakeGitWorktrees(GitWorktrees):
    """In-memory fake implementation of git worktree operations.

    State Management:
    - worktrees: dict[Path, list[WorktreeInfo]] - Mapping of repo_root -> worktrees
    - git_common_dirs: dict[Path, Path] - Mapping of cwd -> git common directory
    - existing_paths: set[Path] - Paths that exist in the fake filesystem

    Mutation Tracking:
    - added_worktrees: list[tuple[Path, str | None]]
    - removed_worktrees: list[Path]
    """

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        git_common_dirs: dict[Path, Path] | None = None,
        existing_paths: set[Path] | None = None,
    ) -> None:
        self._worktrees = worktrees or {}
        self._git_common_dirs = git_common_dirs or {}
        self._existing_paths = existing_paths or set()

        # Mutation tracking
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._removed_worktrees: list[Path] = []

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

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory.

        Mimics `git rev-parse --git-common-dir` behavior:
        1. First checks explicit mapping for cwd or ancestors
        2. Handles symlink resolution differences (e.g., /var vs /private/var on macOS)
        3. Returns None if not in a git repository
        """
        # Build a resolved-key lookup for symlink handling
        resolved_lookup = {k.resolve(): v for k, v in self._git_common_dirs.items()}
        resolved_cwd = cwd.resolve()

        # Check exact match first
        if resolved_cwd in resolved_lookup:
            return resolved_lookup[resolved_cwd]

        # Walk up parent directories to find a match
        for parent in resolved_cwd.parents:
            if parent in resolved_lookup:
                return resolved_lookup[parent]

        return None

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None = None,
        ref: str | None = None,
        create_branch: bool = False,
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

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool = False) -> None:
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

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name in fake data."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    # Read-only properties for test assertions
    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        return self._added_worktrees.copy()

    @property
    def removed_worktrees(self) -> list[Path]:
        return self._removed_worktrees.copy()
