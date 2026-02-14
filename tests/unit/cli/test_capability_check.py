"""Tests for capability_check module."""

from pathlib import Path

from erk.cli.capability_check import is_learned_docs_available
from erk_shared.gateway.git.repo_ops.fake import FakeGitRepoOps


class TestIsLearnedDocsAvailable:
    """Tests for is_learned_docs_available()."""

    def test_returns_true_when_docs_learned_exists(self, tmp_path: Path) -> None:
        """Returns True when docs/learned/ exists in the repo root."""
        docs_dir = tmp_path / "docs" / "learned"
        docs_dir.mkdir(parents=True)

        repo_ops = FakeGitRepoOps(
            git_common_dirs={tmp_path: tmp_path / ".git"},
            repository_roots={tmp_path: tmp_path},
        )

        result = is_learned_docs_available(repo_ops=repo_ops, cwd=tmp_path)

        assert result is True

    def test_returns_false_when_docs_learned_missing(self, tmp_path: Path) -> None:
        """Returns False when docs/learned/ does not exist."""
        repo_ops = FakeGitRepoOps(
            git_common_dirs={tmp_path: tmp_path / ".git"},
            repository_roots={tmp_path: tmp_path},
        )

        result = is_learned_docs_available(repo_ops=repo_ops, cwd=tmp_path)

        assert result is False

    def test_returns_false_outside_git_repo(self, tmp_path: Path) -> None:
        """Returns False when not in a git repository."""
        repo_ops = FakeGitRepoOps()

        result = is_learned_docs_available(repo_ops=repo_ops, cwd=tmp_path)

        assert result is False
