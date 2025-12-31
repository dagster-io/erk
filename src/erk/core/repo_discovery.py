"""Repository discovery functionality.

Discovers git repository information from a given path without requiring
full ErkContext (enables config loading before context creation).
"""

from pathlib import Path

# Re-export context types from erk_shared for backwards compatibility
from erk_shared.context.types import NoRepoSentinel as NoRepoSentinel
from erk_shared.context.types import RepoContext as RepoContext
from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId


def in_erk_repo(repo_root: Path) -> bool:
    """Check if the given path is inside the erk development repository.

    This is used internally to detect when erk is running in its own development
    repo, where artifacts are read directly from source rather than installed.

    Args:
        repo_root: Repository root path to check

    Returns:
        True if this appears to be the erk development repo
    """
    return (repo_root / "packages" / "erk-shared").exists()


def discover_repo_or_sentinel(
    cwd: Path, erk_root: Path, git_ops: Git | None = None
) -> RepoContext | NoRepoSentinel:
    """Walk up from `cwd` to find a directory containing `.git`.

    Returns a RepoContext pointing to the repo root and the worktrees directory
    for this repository, or NoRepoSentinel if not inside a git repo.

    Note: For worktrees, `root` is the worktree directory (where git commands run),
    while `repo_name` is derived from the main repository (for consistent metadata paths).

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

    # root: the actual working tree root (where git commands should run)
    # main_repo_root: the main repository root (for deriving repo_name and metadata paths)
    root: Path | None = None
    main_repo_root: Path | None = None

    git_common_dir = ops.get_git_common_dir(cur)
    if git_common_dir is not None:
        # We're in a git repository (possibly a worktree)
        # git_common_dir points to the main repo's .git directory
        main_repo_root = git_common_dir.parent.resolve()
        # Use --show-toplevel to get the actual worktree root
        root = ops.get_repository_root(cur)
    else:
        for parent in [cur, *cur.parents]:
            git_path = parent / ".git"
            if not ops.path_exists(git_path):
                continue

            if ops.is_dir(git_path):
                root = parent
                main_repo_root = parent
                break

    if root is None or main_repo_root is None:
        return NoRepoSentinel(message="Not inside a git repository (no .git found up the tree)")

    # Use main_repo_root for repo_name to ensure consistent metadata paths across worktrees
    repo_name = main_repo_root.name
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
        main_repo_root=main_repo_root,
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
