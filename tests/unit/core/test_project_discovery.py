"""Tests for project discovery functionality."""

from pathlib import Path

import pytest
from erk_shared.git.fake import FakeGit

from erk.core.project_discovery import ProjectContext, discover_project


class TestDiscoverProject:
    """Tests for discover_project function."""

    def test_finds_project_in_current_directory(self, tmp_path: Path) -> None:
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

    def test_finds_project_from_subdirectory(self, tmp_path: Path) -> None:
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

    def test_returns_none_when_no_project(self, tmp_path: Path) -> None:
        """No project found when .erk/project.toml doesn't exist."""
        repo_root = tmp_path / "repo"
        cwd = repo_root / "some" / "directory"
        cwd.mkdir(parents=True)

        git = FakeGit()
        result = discover_project(cwd, repo_root, git)

        assert result is None

    def test_returns_none_at_repo_root(self, tmp_path: Path) -> None:
        """No project found when cwd is the repo root (not a project)."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir(parents=True)

        git = FakeGit()
        result = discover_project(repo_root, repo_root, git)

        assert result is None

    def test_stops_at_repo_root_boundary(self, tmp_path: Path) -> None:
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

    def test_finds_nearest_project(self, tmp_path: Path) -> None:
        """Finds the nearest project when nested projects exist."""
        repo_root = tmp_path / "repo"

        # Outer project
        outer_project = repo_root / "projects"
        outer_config = outer_project / ".erk" / "project.toml"
        outer_config.parent.mkdir(parents=True)
        outer_config.write_text("# outer", encoding="utf-8")

        # Inner project (nested)
        inner_project = outer_project / "subproject"
        inner_config = inner_project / ".erk" / "project.toml"
        inner_config.parent.mkdir(parents=True)
        inner_config.write_text("# inner", encoding="utf-8")

        # cwd is inside inner project
        cwd = inner_project / "src"
        cwd.mkdir(parents=True)

        git = FakeGit()
        result = discover_project(cwd, repo_root, git)

        # Should find the inner (nearest) project
        assert result is not None
        assert result.root == inner_project
        assert result.name == "subproject"

    def test_returns_none_for_nonexistent_cwd(self, tmp_path: Path) -> None:
        """Returns None when cwd doesn't exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir(parents=True)
        nonexistent = repo_root / "does" / "not" / "exist"

        git = FakeGit()
        result = discover_project(nonexistent, repo_root, git)

        assert result is None

    def test_path_from_repo_is_relative(self, tmp_path: Path) -> None:
        """path_from_repo is always relative."""
        repo_root = tmp_path / "repo"
        project_root = repo_root / "deep" / "nested" / "project"
        project_config = project_root / ".erk" / "project.toml"
        project_config.parent.mkdir(parents=True)
        project_config.write_text("# config", encoding="utf-8")

        git = FakeGit()
        result = discover_project(project_root, repo_root, git)

        assert result is not None
        assert not result.path_from_repo.is_absolute()
        assert result.path_from_repo == Path("deep/nested/project")


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
