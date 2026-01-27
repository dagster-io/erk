"""Fake implementation of git repository operations for testing."""

import subprocess
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
        git_common_dirs: dict[Path, Path | None] | None = None,
    ) -> None:
        """Create FakeGitRepoOps with pre-configured state.

        Args:
            repository_roots: Mapping of cwd -> repo root
            git_common_dirs: Mapping of cwd -> git common dir (None if not in repo)
        """
        self._repository_roots = repository_roots if repository_roots is not None else {}
        self._git_common_dirs = git_common_dirs if git_common_dirs is not None else {}

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        if cwd in self._repository_roots:
            return self._repository_roots[cwd]
        # Walk up to find a configured root
        for path in [cwd, *list(cwd.parents)]:
            if path in self._repository_roots:
                return self._repository_roots[path]
        msg = "git rev-parse --show-toplevel"
        raise subprocess.CalledProcessError(128, msg)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        if cwd in self._git_common_dirs:
            return self._git_common_dirs[cwd]
        # Walk up to find a configured common dir
        for path in list(cwd.parents):
            if path in self._git_common_dirs:
                return self._git_common_dirs[path]
        return None

    # ============================================================================
    # Test Setup (FakeGit integration)
    # ============================================================================

    def link_state(
        self,
        *,
        repository_roots: dict[Path, Path],
        git_common_dirs: dict[Path, Path | None],
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            repository_roots: FakeGit's repository roots mapping
            git_common_dirs: FakeGit's git common dirs mapping
        """
        self._repository_roots = repository_roots
        self._git_common_dirs = git_common_dirs
