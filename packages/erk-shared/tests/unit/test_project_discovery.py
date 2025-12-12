"""Tests for project discovery functionality in erk_shared."""

from pathlib import Path

import pytest

from erk_shared.git.fake import FakeGit
from erk_shared.project_discovery import ProjectContext, discover_project


def test_finds_project_in_current_directory(tmp_path: Path) -> None:
    """Project is found when cwd is the project root."""
    repo_root = tmp_path / "repo"
    project_root = repo_root / "python_modules" / "my-project"
    project_config = project_root / ".erk" / "project.toml"
    project_config.parent.mkdir(parents=True)
    project_config.write_text("# project config", encoding="utf-8")

    git = FakeGit()
    result = discover_project(project_root, repo_root, git)

    assert result is not None
    assert result.root == project_root
    assert result.name == "my-project"
    assert result.path_from_repo == Path("python_modules/my-project")


def test_finds_project_from_subdirectory(tmp_path: Path) -> None:
    """Project is found when cwd is inside the project."""
    repo_root = tmp_path / "repo"
    project_root = repo_root / "python_modules" / "my-project"
    project_config = project_root / ".erk" / "project.toml"
    project_config.parent.mkdir(parents=True)
    project_config.write_text("# project config", encoding="utf-8")

    # cwd is inside the project
    cwd = project_root / "src" / "mypackage"
    cwd.mkdir(parents=True)

    git = FakeGit()
    result = discover_project(cwd, repo_root, git)

    assert result is not None
    assert result.root == project_root
    assert result.name == "my-project"
    assert result.path_from_repo == Path("python_modules/my-project")


def test_returns_none_when_no_project(tmp_path: Path) -> None:
    """No project found when .erk/project.toml doesn't exist."""
    repo_root = tmp_path / "repo"
    cwd = repo_root / "some" / "directory"
    cwd.mkdir(parents=True)

    git = FakeGit()
    result = discover_project(cwd, repo_root, git)

    assert result is None


def test_returns_none_at_repo_root(tmp_path: Path) -> None:
    """No project found when cwd is the repo root (not a project)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    git = FakeGit()
    result = discover_project(repo_root, repo_root, git)

    assert result is None


def test_stops_at_repo_root_boundary(tmp_path: Path) -> None:
    """Search stops at repo root and doesn't find project.toml in repo root."""
    repo_root = tmp_path / "repo"
    # Put project.toml in repo root (should NOT be found)
    repo_config = repo_root / ".erk" / "project.toml"
    repo_config.parent.mkdir(parents=True)
    repo_config.write_text("# should not be found", encoding="utf-8")

    cwd = repo_root / "some" / "directory"
    cwd.mkdir(parents=True)

    git = FakeGit()
    result = discover_project(cwd, repo_root, git)

    # Should NOT find the project.toml in repo root
    assert result is None


def test_returns_none_for_nonexistent_cwd(tmp_path: Path) -> None:
    """Returns None when cwd doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    nonexistent = repo_root / "does" / "not" / "exist"

    git = FakeGit()
    result = discover_project(nonexistent, repo_root, git)

    assert result is None


class TestProjectContext:
    """Tests for ProjectContext dataclass."""

    def test_frozen(self) -> None:
        """ProjectContext is immutable."""
        ctx = ProjectContext(
            root=Path("/repo/project"),
            name="project",
            path_from_repo=Path("project"),
        )

        with pytest.raises(AttributeError):
            ctx.name = "new-name"  # type: ignore[misc]
