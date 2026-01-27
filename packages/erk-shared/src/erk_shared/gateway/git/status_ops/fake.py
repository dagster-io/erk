"""Fake implementation of Git status operations for testing."""

from __future__ import annotations

from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps


class FakeGitStatusOps(GitStatusOps):
    """In-memory fake implementation of Git status operations.

    This fake accepts pre-configured state in its constructor.
    All operations are read-only queries, so no mutation tracking is needed.

    Constructor Injection:
    ---------------------
    - staged_repos: Set of repo roots that have staged changes
    - file_statuses: Mapping of cwd -> (staged, modified, untracked) files
    - merge_conflicts: Mapping of (base_branch, head_branch) -> has conflicts
    - conflicted_files: List of files with merge conflicts
    """

    def __init__(
        self,
        *,
        staged_repos: set[Path] | None = None,
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
        merge_conflicts: dict[tuple[str, str], bool] | None = None,
        conflicted_files: list[str] | None = None,
    ) -> None:
        """Create FakeGitStatusOps with pre-configured state.

        Args:
            staged_repos: Set of repo roots that should report staged changes
            file_statuses: Mapping of cwd -> (staged, modified, untracked) files
            merge_conflicts: Mapping of (base_branch, head_branch) -> has conflicts
            conflicted_files: List of files with merge conflicts
        """
        self._staged_repos = staged_repos if staged_repos is not None else set()
        self._file_statuses = file_statuses if file_statuses is not None else {}
        self._merge_conflicts = merge_conflicts if merge_conflicts is not None else {}
        self._conflicted_files = conflicted_files if conflicted_files is not None else []

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Report whether the repository has staged changes."""
        return repo_root in self._staged_repos

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        staged, modified, untracked = self._file_statuses.get(cwd, ([], [], []))
        return bool(staged or modified or untracked)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        return self._file_statuses.get(cwd, ([], [], []))

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        return self._merge_conflicts.get((base_branch, head_branch), False)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get list of files with merge conflicts."""
        return list(self._conflicted_files)

    # ============================================================================
    # Link State (for integration with FakeGit)
    # ============================================================================

    def link_state(
        self,
        *,
        staged_repos: set[Path],
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]],
        merge_conflicts: dict[tuple[str, str], bool],
        conflicted_files: list[str],
    ) -> None:
        """Link this fake's state to FakeGit's state dictionaries.

        This allows FakeGit to share mutable state with this subgateway,
        enabling tests that modify state via FakeGit to see changes
        reflected in status operations.

        Args:
            staged_repos: FakeGit's _repos_with_staged_changes set
            file_statuses: FakeGit's _file_statuses dict
            merge_conflicts: FakeGit's _merge_conflicts dict
            conflicted_files: FakeGit's _conflicted_files list
        """
        self._staged_repos = staged_repos
        self._file_statuses = file_statuses
        self._merge_conflicts = merge_conflicts
        self._conflicted_files = conflicted_files
