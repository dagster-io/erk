"""Fake git operations for testing.

FakeGit is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path

from erk_shared.git.abc import BranchSyncInfo, Git, WorktreeInfo
from erk_shared.git.branches.abc import GitBranches


class FakeGit(Git):
    """In-memory fake implementation of git operations.

    State Management:
    -----------------
    This fake maintains mutable state to simulate git's stateful behavior.
    Operations like add_worktree, remove_worktree modify internal state.
    State changes are visible to subsequent method calls within the same test.

    When to Use Mutation:
    --------------------
    - Operations that simulate stateful external systems (git, databases)
    - When tests need to verify sequences of operations
    - When simulating side effects visible to production code

    Constructor Injection:
    ---------------------
    All INITIAL state is provided via constructor (immutable after construction).
    Runtime mutations occur through operation methods.
    Tests should construct fakes with complete initial state.

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - added_worktrees: Worktrees added via add_worktree()
    - removed_worktrees: Worktrees removed via remove_worktree()

    Examples:
    ---------
        # Initial state via constructor
        git_ops = FakeGit(
            worktrees={repo: [WorktreeInfo(path=wt1, branch="main")]},
            git_common_dirs={repo: repo / ".git"},
        )

        # Mutation through operation
        git_ops.add_worktree(repo, wt2, branch="feature")

        # Verify mutation
        assert len(git_ops.list_worktrees(repo)) == 2
        assert (wt2, "feature") in git_ops.added_worktrees
    """

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        default_branches: dict[Path, str] | None = None,
        git_common_dirs: dict[Path, Path] | None = None,
        commit_messages: dict[str, str] | None = None,
        staged_repos: set[Path] | None = None,
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
        ahead_behind: dict[tuple[Path, str], tuple[int, int]] | None = None,
        branch_sync_info: dict[str, BranchSyncInfo] | None = None,
        recent_commits: dict[Path, list[dict[str, str]]] | None = None,
        existing_paths: set[Path] | None = None,
        file_contents: dict[Path, str] | None = None,
        remote_branches: dict[Path, list[str]] | None = None,
        dirty_worktrees: set[Path] | None = None,
        branch_issues: dict[str, int] | None = None,
        branch_last_commit_times: dict[str, str] | None = None,
        repository_roots: dict[Path, Path] | None = None,
        diff_to_branch: dict[tuple[Path, str], str] | None = None,
        merge_conflicts: dict[tuple[str, str], bool] | None = None,
        commits_ahead: dict[tuple[Path, str], int] | None = None,
        remote_urls: dict[tuple[Path, str], str] | None = None,
        add_all_raises: Exception | None = None,
        pull_branch_raises: Exception | None = None,
        git_branches: GitBranches | None = None,
    ) -> None:
        """Create FakeGit with pre-configured state.

        Args:
            worktrees: Mapping of repo_root -> list of worktrees
            default_branches: Mapping of repo_root -> default branch
            git_common_dirs: Mapping of cwd -> git common directory
            commit_messages: Mapping of commit SHA -> commit message
            staged_repos: Set of repo roots that should report staged changes
            file_statuses: Mapping of cwd -> (staged, modified, untracked) files
            ahead_behind: Mapping of (cwd, branch) -> (ahead, behind) counts
            branch_sync_info: Mapping of branch name -> BranchSyncInfo for batch queries
            recent_commits: Mapping of cwd -> list of commit info dicts
            existing_paths: Set of paths that should be treated as existing (for pure mode)
            file_contents: Mapping of path -> file content (for commands that read files)
            remote_branches: Mapping of repo_root -> list of remote branch names
                (with prefix like 'origin/branch-name')
            dirty_worktrees: Set of worktree paths that have uncommitted/staged/untracked changes
            branch_issues: Mapping of branch name -> GitHub issue number
            branch_last_commit_times: Mapping of branch name -> ISO 8601 timestamp for last commit
            repository_roots: Mapping of cwd -> repository root path
            diff_to_branch: Mapping of (cwd, branch) -> diff output
            merge_conflicts: Mapping of (base_branch, head_branch) -> has conflicts bool
            commits_ahead: Mapping of (cwd, base_branch) -> commit count
            remote_urls: Mapping of (repo_root, remote_name) -> remote URL
            add_all_raises: Exception to raise when add_all() is called
            pull_branch_raises: Exception to raise when pull_branch() is called
            git_branches: GitBranches instance for branch operations (optional, for delegation)
        """
        self._worktrees = worktrees or {}
        self._default_branches = default_branches or {}
        self._git_common_dirs = git_common_dirs or {}
        self._commit_messages = commit_messages or {}
        self._repos_with_staged_changes: set[Path] = staged_repos or set()
        self._file_statuses = file_statuses or {}
        self._ahead_behind = ahead_behind or {}
        self._branch_sync_info = branch_sync_info or {}
        self._recent_commits = recent_commits or {}
        self._existing_paths = existing_paths or set()
        self._file_contents = file_contents or {}
        self._remote_branches = remote_branches or {}
        self._dirty_worktrees = dirty_worktrees or set()
        self._branch_issues = branch_issues or {}
        self._branch_last_commit_times = branch_last_commit_times or {}
        self._repository_roots = repository_roots or {}
        self._diff_to_branch = diff_to_branch or {}
        self._merge_conflicts = merge_conflicts or {}
        self._commits_ahead = commits_ahead or {}
        self._remote_urls = remote_urls or {}
        self._add_all_raises = add_all_raises
        self._pull_branch_raises = pull_branch_raises
        self._git_branches = git_branches

        # Mutation tracking
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._removed_worktrees: list[Path] = []
        self._fetched_branches: list[tuple[str, str]] = []
        self._pulled_branches: list[tuple[str, str, bool]] = []
        self._chdir_history: list[Path] = []
        self._staged_files: list[str] = []
        self._commits: list[tuple[Path, str, list[str]]] = []
        self._pushed_branches: list[tuple[str, str, bool]] = []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository.

        Mimics `git worktree list` behavior:
        - Can be called from any worktree path or the main repo root
        - Returns the same worktree list regardless of which path is used
        - Handles symlink resolution differences (e.g., /var vs /private/var on macOS)
        """
        resolved_root = repo_root.resolve()

        # Check exact match first (with symlink resolution)
        for key, worktree_list in self._worktrees.items():
            if key.resolve() == resolved_root:
                return worktree_list

        # Check if repo_root is one of the worktree paths in any list
        for worktree_list in self._worktrees.values():
            for wt_info in worktree_list:
                if wt_info.path.resolve() == resolved_root:
                    return worktree_list

        return []

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory.

        Mimics `git rev-parse --git-common-dir` behavior:
        1. First checks explicit mapping for cwd or ancestors
        2. Handles symlink resolution differences (e.g., /var vs /private/var on macOS)
        3. Returns None if not in a git repository
        """
        # Build a resolved-key lookup for symlink handling
        resolved_lookup = {k.resolve(): v for k, v in self._git_common_dirs.items()}
        resolved_cwd = cwd.resolve()

        # Check exact match first
        if resolved_cwd in resolved_lookup:
            return resolved_lookup[resolved_cwd]

        # Walk up parent directories to find a match
        for parent in resolved_cwd.parents:
            if parent in resolved_lookup:
                return resolved_lookup[parent]

        return None

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Report whether the repository has staged changes."""
        return repo_root in self._repos_with_staged_changes

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        staged, modified, untracked = self._file_statuses.get(cwd, ([], [], []))
        return bool(staged or modified or untracked)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree has no uncommitted changes, staged changes, or untracked files."""
        # Check if path exists (LBYL pattern)
        if worktree_path not in self._existing_paths:
            return False

        # Check if worktree is marked as dirty
        if worktree_path in self._dirty_worktrees:
            return False

        return True

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None = None,
        ref: str | None = None,
        create_branch: bool = False,
    ) -> None:
        """Add a new worktree (mutates internal state and creates directory)."""
        if repo_root not in self._worktrees:
            self._worktrees[repo_root] = []
        # New worktrees are never the root worktree
        self._worktrees[repo_root].append(WorktreeInfo(path=path, branch=branch, is_root=False))
        # Create the worktree directory to simulate git worktree add behavior
        path.mkdir(parents=True, exist_ok=True)
        # Add to existing paths for pure mode tests
        self._existing_paths.add(path)
        # Track the addition
        self._added_worktrees.append((path, branch))

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree (mutates internal state and simulates filesystem move)."""
        if repo_root in self._worktrees:
            for i, wt in enumerate(self._worktrees[repo_root]):
                if wt.path == old_path:
                    self._worktrees[repo_root][i] = WorktreeInfo(
                        path=new_path, branch=wt.branch, is_root=wt.is_root
                    )
                    break
        # Update existing_paths for pure test mode
        if old_path in self._existing_paths:
            self._existing_paths.discard(old_path)
            self._existing_paths.add(new_path)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool = False) -> None:
        """Remove a worktree (mutates internal state)."""
        if repo_root in self._worktrees:
            self._worktrees[repo_root] = [
                wt for wt in self._worktrees[repo_root] if wt.path != path
            ]
        # Track the removal
        self._removed_worktrees.append(path)
        # Remove from existing_paths so path_exists() returns False after deletion
        self._existing_paths.discard(path)

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata (no-op for in-memory fake)."""
        pass

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name in fake data."""
        worktrees = self.list_worktrees(repo_root)
        for wt in worktrees:
            if wt.branch == branch:
                return wt.path
        return None

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the commit message for a given commit SHA."""
        return self._commit_messages.get(commit_sha)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        return self._file_statuses.get(cwd, ([], [], []))

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch."""
        return self._ahead_behind.get((cwd, branch), (0, 0))

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches (fake implementation)."""
        return self._branch_sync_info.copy()

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information."""
        commits = self._recent_commits.get(cwd, [])
        return commits[:limit]

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote (tracks mutation)."""
        self._fetched_branches.append((remote, branch))

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote (tracks mutation)."""
        self._pulled_branches.append((remote, branch, ff_only))
        if self._pull_branch_raises is not None:
            raise self._pull_branch_raises

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote (fake implementation).

        Returns True if the branch exists in the configured remote branches.
        Checks for the branch in format: remote/branch (e.g., origin/feature).
        """
        remote_branches = self._remote_branches.get(repo_root, [])
        remote_ref = f"{remote}/{branch}"
        return remote_ref in remote_branches

    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        """Get list of worktrees added during test.

        Returns list of (path, branch) tuples.
        This property is for test assertions only.
        """
        return self._added_worktrees.copy()

    @property
    def removed_worktrees(self) -> list[Path]:
        """Get list of worktrees removed during test.

        This property is for test assertions only.
        """
        return self._removed_worktrees.copy()

    @property
    def fetched_branches(self) -> list[tuple[str, str]]:
        """Get list of branches fetched during test.

        Returns list of (remote, branch) tuples.
        This property is for test assertions only.
        """
        return self._fetched_branches.copy()

    @property
    def pulled_branches(self) -> list[tuple[str, str, bool]]:
        """Get list of branches pulled during test.

        Returns list of (remote, branch, ff_only) tuples.
        This property is for test assertions only.
        """
        return self._pulled_branches.copy()

    @property
    def chdir_history(self) -> list[Path]:
        """Get list of directories changed to during test.

        Returns list of Path objects passed to safe_chdir().
        This property is for test assertions only.
        """
        return self._chdir_history.copy()

    def _is_parent(self, parent: Path, child: Path) -> bool:
        """Check if parent is an ancestor of child."""
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    def path_exists(self, path: Path) -> bool:
        """Check if path should be treated as existing.

        Used in erk_inmem_env to simulate filesystem checks without
        actual filesystem I/O. Paths in existing_paths are treated as
        existing even though they're sentinel paths.

        For erk_isolated_fs_env (real directories), falls back to
        checking the real filesystem for paths within known worktrees.
        """
        from tests.test_utils.paths import SentinelPath

        # First check if path is explicitly marked as existing
        if path in self._existing_paths:
            return True

        # Don't check real filesystem for sentinel paths (pure test mode)
        if isinstance(path, SentinelPath):
            return False

        # For real filesystem tests, check if path is under any existing path
        for existing_path in self._existing_paths:
            try:
                # Check if path is relative to existing_path
                path.relative_to(existing_path)
                # If we get here, path is under existing_path
                # Check if it actually exists on real filesystem
                return path.exists()
            except (ValueError, OSError, RuntimeError):
                # Not relative to this existing_path or error checking, continue
                continue

        # Fallback: if no existing_paths configured and path is not under any known path,
        # check real filesystem. This handles tests that create real files but don't
        # set up existing_paths (like some unit tests).
        # This fallback won't interfere with tests that explicitly set existing_paths
        # (like the init test) because those will either find the path in existing_paths
        # or not find it as a child of any existing_path.
        if not self._existing_paths or not any(
            self._is_parent(ep, path) for ep in self._existing_paths
        ):
            try:
                return path.exists()
            except (OSError, RuntimeError):
                return False

        return False

    def is_dir(self, path: Path) -> bool:
        """Check if path should be treated as a directory.

        For testing purposes, paths in existing_paths that represent
        git directories (.git) or worktree directories are treated as
        directories. This is used primarily for distinguishing .git
        directories (normal repos) from .git files (worktrees).

        Returns True if path exists and is likely a directory.
        """
        if path not in self._existing_paths:
            return False
        # If it's a .git path, treat it as a directory
        # (worktrees would have .git as a file, which wouldn't be in existing_paths)
        return True

    def safe_chdir(self, path: Path) -> bool:
        """Change directory if path exists, handling sentinel paths.

        For sentinel paths (pure test mode), returns False without changing directory.
        For real filesystem paths, changes directory if path exists and returns True.

        Tracks successful directory changes in chdir_history for test assertions.
        """
        import os

        from tests.test_utils.paths import SentinelPath

        # Check if path should be treated as existing
        if not self.path_exists(path):
            return False

        # Don't try to chdir to sentinel paths - they're not real filesystem paths
        if isinstance(path, SentinelPath):
            # Track the attempt even for sentinel paths (tests need to verify intent)
            self._chdir_history.append(path)
            return False

        # For real filesystem paths, change directory
        os.chdir(path)
        self._chdir_history.append(path)
        return True

    def read_file(self, path: Path) -> str:
        """Read file content from in-memory store.

        Used in erk_inmem_env for commands that need to read files
        (e.g., plan files, config files) without actual filesystem I/O.

        Raises:
            FileNotFoundError: If path not in file_contents mapping.
        """
        if path not in self._file_contents:
            raise FileNotFoundError(f"No content for {path}")
        return self._file_contents[path]

    def set_branch_issue(self, repo_root: Path, branch: str, issue_number: int) -> None:
        """Record branch-issue association in fake storage."""
        self._branch_issues[branch] = issue_number

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get branch-issue association from fake storage."""
        return self._branch_issues.get(branch)

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Record PR ref fetch in fake storage (mutates internal state).

        Simulates fetching a PR ref. In real git, this would fetch
        refs/pull/<number>/head and create the branch.
        """
        # Track the fetch for test assertions
        self._fetched_branches.append((remote, f"pull/{pr_number}/head"))

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Record staged files for commit."""
        self._staged_files.extend(paths)

    def commit(self, cwd: Path, message: str) -> None:
        """Record commit with staged changes.

        Also updates commits_ahead for the parent branch if state is tracked.
        This ensures that test scenarios where uncommitted changes are committed
        result in the expected commit count increase.
        """
        self._commits.append((cwd, message, list(self._staged_files)))
        self._staged_files = []  # Clear staged files after commit

        # Update commits_ahead for all tracked parent branches at this cwd
        for (path, base_branch), count in list(self._commits_ahead.items()):
            if path == cwd:
                self._commits_ahead[(cwd, base_branch)] = count + 1

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Record push to remote."""
        self._pushed_branches.append((remote, branch, set_upstream))

    @property
    def staged_files(self) -> list[str]:
        """Read-only access to currently staged files for test assertions."""
        return self._staged_files

    @property
    def commits(self) -> list[tuple[Path, str, list[str]]]:
        """Read-only access to commits for test assertions.

        Returns list of (cwd, message, staged_files) tuples.
        """
        return self._commits

    @property
    def pushed_branches(self) -> list[tuple[str, str, bool]]:
        """Read-only access to pushed branches for test assertions.

        Returns list of (remote, branch, set_upstream) tuples.
        """
        return self._pushed_branches

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get the author date of the most recent commit unique to a branch."""
        return self._branch_last_commit_times.get(branch)

    def add_all(self, cwd: Path) -> None:
        """Stage all changes for commit (git add -A).

        Raises configured exception if add_all_raises was set.
        """
        if self._add_all_raises is not None:
            raise self._add_all_raises

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend the current commit with a new message."""
        # In the fake, replace last commit message if commits exist
        if self._commits:
            last_commit = self._commits[-1]
            self._commits[-1] = (last_commit[0], message, last_commit[2])

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        return self._commits_ahead.get((cwd, base_branch), 0)

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory.

        Mimics `git rev-parse --show-toplevel` behavior:
        1. First checks explicit repository_roots mapping
        2. Falls back to finding the deepest worktree path that contains cwd
        3. Falls back to deriving root from git_common_dirs (parent of .git directory)
        4. Returns cwd as last resort if no match found
        5. Handles symlink resolution differences (e.g., /var vs /private/var on macOS)
        """
        resolved_cwd = cwd.resolve()

        # Check explicit mapping first (with symlink resolution)
        resolved_roots = {k.resolve(): v for k, v in self._repository_roots.items()}
        if resolved_cwd in resolved_roots:
            return resolved_roots[resolved_cwd]

        # Infer from worktrees: find the deepest worktree path that contains cwd
        # This mimics git --show-toplevel returning the worktree root from subdirectories
        best_match: Path | None = None
        for worktree_list in self._worktrees.values():
            for wt_info in worktree_list:
                wt_path = wt_info.path.resolve()
                # Check if cwd is the worktree path or a subdirectory of it
                if resolved_cwd == wt_path or wt_path in resolved_cwd.parents:
                    # Prefer deeper paths (more specific match)
                    if best_match is None or len(wt_path.parts) > len(best_match.parts):
                        best_match = wt_path

        if best_match is not None:
            return best_match

        # Fallback: derive from git_common_dirs (parent of .git directory is repo root)
        # This handles the case where we're in a subdirectory of a normal repo (not a worktree)
        git_common_dir = self.get_git_common_dir(cwd)
        if git_common_dir is not None:
            # For normal repos, git_common_dir is the .git directory
            # Its parent is the repository root
            return git_common_dir.parent

        # Last resort: return cwd itself
        return cwd

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        return self._diff_to_branch.get((cwd, branch), "")

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        return self._merge_conflicts.get((base_branch, head_branch), False)

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote.

        Raises:
            ValueError: If remote doesn't exist or has no URL
        """
        url = self._remote_urls.get((repo_root, remote))
        if url is None:
            raise ValueError(f"Remote '{remote}' not found in repository")
        return url

    # Branch operation delegation methods
    # These delegate to self._git_branches if available, for backward compatibility
    # during the migration to separate GitBranches integration

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch.

        Delegates to GitBranches if available.
        """
        if self._git_branches is None:
            raise AttributeError(
                "get_current_branch requires git_branches parameter to be provided to FakeGit"
            )
        return self._git_branches.get_current_branch(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name.

        Delegates to GitBranches if available.
        """
        if self._git_branches is None:
            raise AttributeError(
                "detect_trunk_branch requires git_branches parameter to be provided to FakeGit"
            )
        return self._git_branches.detect_trunk_branch(repo_root)
