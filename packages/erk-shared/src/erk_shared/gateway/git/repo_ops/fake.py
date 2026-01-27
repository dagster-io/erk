"""Fake implementation of git repository operations for testing."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class FakeGitRepoOps(GitRepoOps):
    """In-memory fake implementation for testing.

    Constructor Injection: pre-configured state passed via constructor.
    """

    def __init__(
        self,
        *,
        repository_roots: dict[Path, Path] | None = None,
        git_common_dirs: dict[Path, Path] | None = None,
        worktrees: dict[Path, list] | None = None,
    ) -> None:
        """Create FakeGitRepoOps with pre-configured state.

        Args:
            repository_roots: Mapping of cwd -> repo root
            git_common_dirs: Mapping of cwd -> git common dir
            worktrees: Mapping of repo_root -> list of worktree info (for root inference)
        """
        self._repository_roots: dict[Path, Path] = (
            repository_roots if repository_roots is not None else {}
        )
        self._git_common_dirs: dict[Path, Path] = (
            git_common_dirs if git_common_dirs is not None else {}
        )
        self._worktrees: dict[Path, list] = worktrees if worktrees is not None else {}

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory.

        Mimics `git rev-parse --show-toplevel` behavior:
        1. First checks explicit repository_roots mapping
        2. Falls back to finding the deepest worktree path that contains cwd
        3. Falls back to deriving root from git_common_dirs (parent of .git directory)
        4. Returns cwd as last resort if no match found
        5. Handles symlink resolution differences (e.g., /var vs /private/var on macOS)
        """
        resolved_cwd = cwd.resolve()

        # Check explicit mapping first (with symlink resolution)
        resolved_roots = {k.resolve(): v for k, v in self._repository_roots.items()}
        if resolved_cwd in resolved_roots:
            return resolved_roots[resolved_cwd]

        # Infer from worktrees: find the deepest worktree path that contains cwd
        # This mimics git --show-toplevel returning the worktree root from subdirectories
        best_match: Path | None = None
        for worktree_list in self._worktrees.values():
            for wt_info in worktree_list:
                wt_path = wt_info.path.resolve()
                # Check if cwd is the worktree path or a subdirectory of it
                if resolved_cwd == wt_path or wt_path in resolved_cwd.parents:
                    # Prefer deeper paths (more specific match)
                    if best_match is None or len(wt_path.parts) > len(best_match.parts):
                        best_match = wt_path

        if best_match is not None:
            return best_match

        # Fallback: derive from git_common_dirs (parent of .git directory is repo root)
        # This handles the case where we're in a subdirectory of a normal repo (not a worktree)
        git_common_dir = self.get_git_common_dir(cwd)
        if git_common_dir is not None:
            # For normal repos, git_common_dir is the .git directory
            # Its parent is the repository root
            return git_common_dir.parent

        # Last resort: return cwd itself
        return cwd

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

    # ============================================================================
    # Test Setup (FakeGit integration)
    # ============================================================================

    def link_state(
        self,
        *,
        repository_roots: dict[Path, Path],
        git_common_dirs: dict[Path, Path],
        worktrees: dict[Path, list],
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            repository_roots: FakeGit's repository roots mapping
            git_common_dirs: FakeGit's git common dirs mapping
            worktrees: FakeGit's worktrees mapping
        """
        self._repository_roots = repository_roots
        self._git_common_dirs = git_common_dirs
        self._worktrees = worktrees
