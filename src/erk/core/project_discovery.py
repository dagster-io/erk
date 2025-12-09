"""Project discovery functionality.

Thin shim that imports from erk_shared and adds RealGit default for erk usage.
"""

from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit

# Re-export ProjectContext for backwards compatibility in erk codebase
# Use explicit `as` syntax to signal intentional re-export (PEP 484)
from erk_shared.project_discovery import ProjectContext as ProjectContext
from erk_shared.project_discovery import discover_project as _discover_project_base


def discover_project(
    cwd: Path, repo_root: Path, git_ops: Git | None = None
) -> ProjectContext | None:
    """Walk up from `cwd` to `repo_root` looking for `.erk/project.toml`.

    This is a thin wrapper that provides RealGit as the default git_ops.
    See erk_shared.project_discovery.discover_project for full documentation.

    Args:
        cwd: Current working directory to start search from
        repo_root: Git repository root (stop searching at this boundary)
        git_ops: Git operations interface (defaults to RealGit)

    Returns:
        ProjectContext if a project is found, None otherwise
    """
    ops = git_ops if git_ops is not None else RealGit()
    return _discover_project_base(cwd, repo_root, ops)
