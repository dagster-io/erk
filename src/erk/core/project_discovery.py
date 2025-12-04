"""Project discovery functionality.

Discovers project context within a git repository. A project is a subdirectory
identified by the presence of `.erk/project.toml`.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit


@dataclass(frozen=True)
class ProjectContext:
    """Represents a project within a git repository.

    A project is a subdirectory within a repo that has its own Claude Code context,
    identified by `.erk/project.toml`.
    """

    root: Path  # Absolute path to project directory (e.g., /code/internal/python_modules/dop)
    name: str  # Project name (defaults to directory name)
    path_from_repo: Path  # Relative path from repo root (e.g., python_modules/dop)


def discover_project(
    cwd: Path, repo_root: Path, git_ops: Git | None = None
) -> ProjectContext | None:
    """Walk up from `cwd` to `repo_root` looking for `.erk/project.toml`.

    Searches from the current directory up to (but not including) the repo root
    for a directory containing `.erk/project.toml`.

    Args:
        cwd: Current working directory to start search from
        repo_root: Git repository root (stop searching at this boundary)
        git_ops: Git operations interface (defaults to RealGit)

    Returns:
        ProjectContext if a project is found, None otherwise

    Example:
        cwd: /code/internal/python_modules/dagster-open-platform/src
        repo_root: /code/internal

        Walk up looking for .erk/project.toml:
        1. /code/internal/python_modules/dagster-open-platform/src/.erk/project.toml (not found)
        2. /code/internal/python_modules/dagster-open-platform/.erk/project.toml (found!)

        Result:
            ProjectContext(
                root=/code/internal/python_modules/dagster-open-platform,
                name="dagster-open-platform",
                path_from_repo=Path("python_modules/dagster-open-platform")
            )
    """
    ops = git_ops if git_ops is not None else RealGit()

    if not ops.path_exists(cwd):
        return None

    cur = cwd.resolve()
    repo_root_resolved = repo_root.resolve()

    # Walk up from cwd to repo_root (exclusive)
    for parent in [cur, *cur.parents]:
        # Stop at repo root - don't check repo root itself
        if parent == repo_root_resolved:
            break

        # Check if this directory is inside repo root
        try:
            parent.relative_to(repo_root_resolved)
        except ValueError:
            # parent is outside repo_root, stop searching
            break

        project_config_path = parent / ".erk" / "project.toml"
        if ops.path_exists(project_config_path):
            # Found project!
            project_name = parent.name
            path_from_repo = parent.relative_to(repo_root_resolved)

            return ProjectContext(
                root=parent,
                name=project_name,
                path_from_repo=path_from_repo,
            )

    return None
