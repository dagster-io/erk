"""Repository discovery functionality.

Discovers git repository information from a given path without requiring
full ErkContext (enables config loading before context creation).
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId


@dataclass(frozen=True)
class RepoContext:
    """Represents a git repo root and its managed worktrees directory."""

    root: Path
    repo_name: str
    repo_dir: Path  # ~/.erk/repos/<repo-name>
    worktrees_dir: Path  # ~/.erk/repos/<repo-name>/worktrees
    github: GitHubRepoId | None = None  # None if not a GitHub repo or no remote


@dataclass(frozen=True)
class NoRepoSentinel:
    """Sentinel value indicating execution outside a git repository.

    Used when commands run outside git repositories (e.g., before init,
    in non-git directories). Commands that require repo context can check
    for this sentinel and fail fast.
    """

    message: str = "Not inside a git repository"


def discover_repo_or_sentinel(
    cwd: Path, erk_root: Path, git_ops: Git | None = None
) -> RepoContext | NoRepoSentinel:
    """Walk up from `cwd` to find a directory containing `.git`.

    Returns a RepoContext pointing to the repo root and the worktrees directory
    for this repository, or NoRepoSentinel if not inside a git repo.

    Note: Properly handles git worktrees by finding the main repository root,
    not the worktree's .git file.

    Args:
        cwd: Current working directory to start search from
        erk_root: Global erks root directory (from config)
        git_ops: Git operations interface (defaults to RealGit)

    Returns:
        RepoContext if inside a git repository, NoRepoSentinel otherwise
    """
    ops = git_ops if git_ops is not None else RealGit()

    if not ops.path_exists(cwd):
        return NoRepoSentinel(message=f"Start path '{cwd}' does not exist")

    cur = cwd.resolve()

    root: Path | None = None
    git_common_dir = ops.get_git_common_dir(cur)
    if git_common_dir is not None:
        root = git_common_dir.parent.resolve()
    else:
        for parent in [cur, *cur.parents]:
            git_path = parent / ".git"
            if not ops.path_exists(git_path):
                continue

            if ops.is_dir(git_path):
                root = parent
                break

    if root is None:
        return NoRepoSentinel(message="Not inside a git repository (no .git found up the tree)")

    repo_name = root.name
    repo_dir = erk_root / "repos" / repo_name
    worktrees_dir = repo_dir / "worktrees"

    # Extract GitHub identity from remote URL
    repo_id: GitHubRepoId | None = None
    try:
        remote_url = ops.get_remote_url(root, "origin")
        owner_repo = parse_git_remote_url(remote_url)
        repo_id = GitHubRepoId(owner=owner_repo[0], repo=owner_repo[1])
    except ValueError:
        # No origin remote or not a GitHub URL - continue without GitHub identity
        pass

    return RepoContext(
        root=root,
        repo_name=repo_name,
        repo_dir=repo_dir,
        worktrees_dir=worktrees_dir,
        github=repo_id,
    )


def ensure_erk_metadata_dir(repo: RepoContext) -> Path:
    """Ensure the erk metadata directory and worktrees subdirectory exist.

    Creates repo.repo_dir (~/.erk/repos/<repo-name>) and repo.worktrees_dir
    subdirectory if they don't exist.

    Args:
        repo: Repository context containing metadata paths

    Returns:
        Path to the erk metadata directory (repo.repo_dir), not git root
    """
    repo.repo_dir.mkdir(parents=True, exist_ok=True)
    repo.worktrees_dir.mkdir(parents=True, exist_ok=True)
    return repo.repo_dir
