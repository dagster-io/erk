"""Fake implementation of git analysis operations for testing."""

from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class FakeGitAnalysisOps(GitAnalysisOps):
    """In-memory fake implementation for testing.

    Constructor Injection: pre-configured state passed via constructor.
    """

    def __init__(
        self,
        *,
        commits_ahead: dict[tuple[Path, str], int] | None = None,
        merge_bases: dict[tuple[Path, str, str], str | None] | None = None,
        diffs: dict[tuple[Path, str], str] | None = None,
    ) -> None:
        """Create FakeGitAnalysisOps with pre-configured state.

        Args:
            commits_ahead: Mapping of (cwd, base_branch) -> commit count
            merge_bases: Mapping of (repo_root, ref1, ref2) -> merge base SHA
            diffs: Mapping of (cwd, branch) -> diff string
        """
        self._commits_ahead = commits_ahead if commits_ahead is not None else {}
        self._merge_bases = merge_bases if merge_bases is not None else {}
        self._diffs = diffs if diffs is not None else {}

    # ============================================================================
    # Query Operations
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        return self._commits_ahead.get((cwd, base_branch), 0)

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs."""
        return self._merge_bases.get((repo_root, ref1, ref2))

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        return self._diffs.get((cwd, branch), "")

    # ============================================================================
    # Test Setup (FakeGit integration)
    # ============================================================================

    def link_state(
        self,
        *,
        commits_ahead: dict[tuple[Path, str], int],
        merge_bases: dict[tuple[Path, str, str], str | None],
        diffs: dict[tuple[Path, str], str],
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            commits_ahead: FakeGit's commits ahead mapping
            merge_bases: FakeGit's merge bases mapping
            diffs: FakeGit's diffs mapping
        """
        self._commits_ahead = commits_ahead
        self._merge_bases = merge_bases
        self._diffs = diffs
