"""Tests for worktree metadata storage."""

from pathlib import Path

from erk.core.worktree_metadata import (
    get_worktree_project,
    remove_worktree_metadata,
    set_worktree_project,
)


class TestGetWorktreeProject:
    """Tests for get_worktree_project function."""

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Returns None when worktrees.toml doesn't exist."""
        result = get_worktree_project(tmp_path, "feature-x")
        assert result is None

    def test_returns_none_when_worktree_not_in_file(self, tmp_path: Path) -> None:
        """Returns None when worktree not in file."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text("[other-wt]\nproject = 'some/path'\n", encoding="utf-8")

        result = get_worktree_project(tmp_path, "feature-x")
        assert result is None

    def test_returns_project_path(self, tmp_path: Path) -> None:
        """Returns project path when worktree has one."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text(
            "[feature-x]\nproject = 'python_modules/my-project'\n",
            encoding="utf-8",
        )

        result = get_worktree_project(tmp_path, "feature-x")
        assert result == Path("python_modules/my-project")

    def test_returns_none_when_no_project_key(self, tmp_path: Path) -> None:
        """Returns None when worktree section exists but has no project key."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text("[feature-x]\nother_key = 'value'\n", encoding="utf-8")

        result = get_worktree_project(tmp_path, "feature-x")
        assert result is None


class TestSetWorktreeProject:
    """Tests for set_worktree_project function."""

    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        """Creates worktrees.toml if it doesn't exist."""
        set_worktree_project(tmp_path, "feature-x", Path("python_modules/my-project"))

        worktrees_toml = tmp_path / "worktrees.toml"
        assert worktrees_toml.exists()
        assert "feature-x" in worktrees_toml.read_text(encoding="utf-8")

    def test_adds_worktree_to_existing_file(self, tmp_path: Path) -> None:
        """Adds worktree to existing file."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text("[other-wt]\nproject = 'other/path'\n", encoding="utf-8")

        set_worktree_project(tmp_path, "feature-x", Path("python_modules/my-project"))

        content = worktrees_toml.read_text(encoding="utf-8")
        assert "other-wt" in content
        assert "feature-x" in content

    def test_updates_existing_worktree(self, tmp_path: Path) -> None:
        """Updates existing worktree entry."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text("[feature-x]\nproject = 'old/path'\n", encoding="utf-8")

        set_worktree_project(tmp_path, "feature-x", Path("new/path"))

        result = get_worktree_project(tmp_path, "feature-x")
        assert result == Path("new/path")

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Can read back what was written."""
        project_path = Path("python_modules/dagster-open-platform")
        set_worktree_project(tmp_path, "feature-x", project_path)

        result = get_worktree_project(tmp_path, "feature-x")
        assert result == project_path


class TestRemoveWorktreeMetadata:
    """Tests for remove_worktree_metadata function."""

    def test_noop_when_file_missing(self, tmp_path: Path) -> None:
        """No error when file doesn't exist."""
        # Should not raise
        remove_worktree_metadata(tmp_path, "feature-x")

    def test_noop_when_worktree_not_in_file(self, tmp_path: Path) -> None:
        """No error when worktree not in file."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text("[other-wt]\nproject = 'path'\n", encoding="utf-8")

        remove_worktree_metadata(tmp_path, "feature-x")

        # other-wt should still be there
        assert "other-wt" in worktrees_toml.read_text(encoding="utf-8")

    def test_removes_worktree_entry(self, tmp_path: Path) -> None:
        """Removes worktree entry from file."""
        worktrees_toml = tmp_path / "worktrees.toml"
        worktrees_toml.write_text(
            "[feature-x]\nproject = 'path1'\n\n[other-wt]\nproject = 'path2'\n",
            encoding="utf-8",
        )

        remove_worktree_metadata(tmp_path, "feature-x")

        content = worktrees_toml.read_text(encoding="utf-8")
        assert "feature-x" not in content
        assert "other-wt" in content
