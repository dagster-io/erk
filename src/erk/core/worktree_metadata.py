"""Worktree metadata storage.

Manages `~/.erk/repos/{repo}/worktrees.toml` which stores per-worktree metadata
like project associations.

Example worktrees.toml:
    [feature-x]
    project = "python_modules/dagster-open-platform"

    [another-wt]
    project = "python_modules/another-project"
"""

from pathlib import Path

import tomlkit
from erk_shared.git.abc import Git


def get_worktree_project(
    repo_dir: Path, worktree_name: str, git_ops: Git | None = None
) -> Path | None:
    """Get the project path for a worktree.

    Args:
        repo_dir: The erk repo metadata directory (~/.erk/repos/<repo-name>)
        worktree_name: Name of the worktree
        git_ops: Optional Git operations interface for path checking (uses .exists() if None)

    Returns:
        Relative path from repo root to project directory, or None if no project associated
    """
    worktrees_toml = repo_dir / "worktrees.toml"

    # Check existence using git_ops if provided (for test compatibility with fakes)
    if git_ops is not None:
        if not git_ops.path_exists(worktrees_toml):
            return None
    else:
        if not worktrees_toml.exists():
            return None

    data = tomlkit.loads(worktrees_toml.read_text(encoding="utf-8"))

    if worktree_name not in data:
        return None

    worktree_data = data[worktree_name]
    if not isinstance(worktree_data, dict):
        return None

    project = worktree_data.get("project")
    if project is None:
        return None

    return Path(str(project))


def set_worktree_project(repo_dir: Path, worktree_name: str, project_path: Path) -> None:
    """Set the project path for a worktree.

    Creates or updates the worktrees.toml file.

    Args:
        repo_dir: The erk repo metadata directory (~/.erk/repos/<repo-name>)
        worktree_name: Name of the worktree
        project_path: Relative path from repo root to project directory
    """
    worktrees_toml = repo_dir / "worktrees.toml"

    # Load existing or create new
    if worktrees_toml.exists():
        data = tomlkit.loads(worktrees_toml.read_text(encoding="utf-8"))
    else:
        data = tomlkit.document()

    # Ensure worktree section exists
    if worktree_name not in data:
        data[worktree_name] = tomlkit.table()  # type: ignore[index]

    # Set project path
    data[worktree_name]["project"] = str(project_path)  # type: ignore[index]

    # Write back
    worktrees_toml.write_text(tomlkit.dumps(data), encoding="utf-8")


def remove_worktree_metadata(repo_dir: Path, worktree_name: str) -> None:
    """Remove metadata for a worktree.

    Called when a worktree is deleted.

    Args:
        repo_dir: The erk repo metadata directory (~/.erk/repos/<repo-name>)
        worktree_name: Name of the worktree to remove
    """
    worktrees_toml = repo_dir / "worktrees.toml"

    if not worktrees_toml.exists():
        return

    data = tomlkit.loads(worktrees_toml.read_text(encoding="utf-8"))

    if worktree_name in data:
        del data[worktree_name]
        worktrees_toml.write_text(tomlkit.dumps(data), encoding="utf-8")
