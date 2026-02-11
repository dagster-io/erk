"""Tests for capability_check module."""

from pathlib import Path
from unittest.mock import patch

from erk.cli.capability_check import is_learned_docs_available


class TestIsLearnedDocsAvailable:
    """Tests for is_learned_docs_available()."""

    def test_returns_true_when_docs_learned_exists(self, tmp_path: Path) -> None:
        """Returns True when docs/learned/ exists in the repo root."""
        docs_dir = tmp_path / "docs" / "learned"
        docs_dir.mkdir(parents=True)

        with (
            patch("erk.cli.capability_check.RealGitRepoOps") as mock_repo_ops_cls,
        ):
            mock_repo_ops = mock_repo_ops_cls.return_value
            mock_repo_ops.get_git_common_dir.return_value = tmp_path / ".git"
            mock_repo_ops.get_repository_root.return_value = tmp_path

            result = is_learned_docs_available()

        assert result is True

    def test_returns_false_when_docs_learned_missing(self, tmp_path: Path) -> None:
        """Returns False when docs/learned/ does not exist."""
        with (
            patch("erk.cli.capability_check.RealGitRepoOps") as mock_repo_ops_cls,
        ):
            mock_repo_ops = mock_repo_ops_cls.return_value
            mock_repo_ops.get_git_common_dir.return_value = tmp_path / ".git"
            mock_repo_ops.get_repository_root.return_value = tmp_path

            result = is_learned_docs_available()

        assert result is False

    def test_returns_false_outside_git_repo(self) -> None:
        """Returns False when not in a git repository."""
        with (
            patch("erk.cli.capability_check.RealGitRepoOps") as mock_repo_ops_cls,
        ):
            mock_repo_ops = mock_repo_ops_cls.return_value
            mock_repo_ops.get_git_common_dir.return_value = None

            result = is_learned_docs_available()

        assert result is False
        mock_repo_ops.get_repository_root.assert_not_called()
