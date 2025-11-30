"""Fake git operations for testing.

FakeGit is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path

import click
from erk_shared.git.abc import BranchSyncInfo, Git, WorktreeInfo


class FakeGit(Git):
    """In-memory fake implementation of git operations.

    State Management:
    -----------------
    This fake maintains mutable state to simulate git's stateful behavior.
    Operations like add_worktree, checkout_branch modify internal state.
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
    - deleted_branches: Branches deleted via delete_branch() or delete_branch_with_graphite()
    - added_worktrees: Worktrees added via add_worktree()
    - removed_worktrees: Worktrees removed via remove_worktree()
    - checked_out_branches: Branches checked out via checkout_branch()

    Examples:
    ---------
        # Initial state via constructor
        git_ops = FakeGit(
            worktrees={repo: [WorktreeInfo(path=wt1, branch="main")]},
            current_branches={wt1: "main"},
            git_common_dirs={repo: repo / ".git"},
        )

        # Mutation through operation
        git_ops.add_worktree(repo, wt2, branch="feature")

        # Verify mutation
        assert len(git_ops.list_worktrees(repo)) == 2
        assert (wt2, "feature") in git_ops.added_worktrees

        # Verify sequence of operations
        git_ops.checkout_branch(repo, "feature")
        git_ops.delete_branch_with_graphite(repo, "old-feature", force=True)
        assert (repo, "feature") in git_ops.checked_out_branches
        assert "old-feature" in git_ops.deleted_branches
    """

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        current_branches: dict[Path, str | None] | None = None,
        default_branches: dict[Path, str] | None = None,
        trunk_branches: dict[Path, str] | None = None,
        git_common_dirs: dict[Path, Path] | None = None,
        branch_heads: dict[str, str] | None = None,
        commit_messages: dict[str, str] | None = None,
        staged_repos: set[Path] | None = None,
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
        ahead_behind: dict[tuple[Path, str], tuple[int, int]] | None = None,
        branch_sync_info: dict[str, BranchSyncInfo] | None = None,
        recent_commits: dict[Path, list[dict[str, str]]] | None = None,
        existing_paths: set[Path] | None = None,
        file_contents: dict[Path, str] | None = None,
        delete_branch_raises: dict[str, Exception] | None = None,
        local_branches: dict[Path, list[str]] | None = None,
        remote_branches: dict[Path, list[str]] | None = None,
        tracking_branch_failures: dict[str, str] | None = None,
        dirty_worktrees: set[Path] | None = None,
        branch_issues: dict[str, int] | None = None,
    ) -> None:
        """Create FakeGit with pre-configured state.

        Args:
            worktrees: Mapping of repo_root -> list of worktrees
            current_branches: Mapping of cwd -> current branch
            default_branches: Mapping of repo_root -> default branch
            trunk_branches: Mapping of repo_root -> trunk branch name
            git_common_dirs: Mapping of cwd -> git common directory
            branch_heads: Mapping of branch name -> commit SHA
            commit_messages: Mapping of commit SHA -> commit message
            staged_repos: Set of repo roots that should report staged changes
            file_statuses: Mapping of cwd -> (staged, modified, untracked) files
            ahead_behind: Mapping of (cwd, branch) -> (ahead, behind) counts
            branch_sync_info: Mapping of branch name -> BranchSyncInfo for batch queries
            recent_commits: Mapping of cwd -> list of commit info dicts
            existing_paths: Set of paths that should be treated as existing (for pure mode)
            file_contents: Mapping of path -> file content (for commands that read files)
            delete_branch_raises: Mapping of branch name -> exception to raise on delete
            local_branches: Mapping of repo_root -> list of local branch names
            remote_branches: Mapping of repo_root -> list of remote branch names
                (with prefix like 'origin/branch-name')
            tracking_branch_failures: Mapping of branch name -> error message to raise
                when create_tracking_branch is called for that branch
            dirty_worktrees: Set of worktree paths that have uncommitted/staged/untracked changes
            branch_issues: Mapping of branch name -> GitHub issue number
        """
        self._worktrees = worktrees or {}
        self._current_branches = current_branches or {}
        self._default_branches = default_branches or {}
        self._trunk_branches = trunk_branches or {}
        self._git_common_dirs = git_common_dirs or {}
        self._branch_heads = branch_heads or {}
        self._commit_messages = commit_messages or {}
        self._repos_with_staged_changes: set[Path] = staged_repos or set()
        self._file_statuses = file_statuses or {}
        self._ahead_behind = ahead_behind or {}
        self._branch_sync_info = branch_sync_info or {}
        self._recent_commits = recent_commits or {}
        self._existing_paths = existing_paths or set()
        self._file_contents = file_contents or {}
        self._delete_branch_raises = delete_branch_raises or {}
        self._local_branches = local_branches or {}
        self._remote_branches = remote_branches or {}
        self._tracking_branch_failures = tracking_branch_failures or {}
        self._dirty_worktrees = dirty_worktrees or set()
        self._branch_issues = branch_issues or {}

        # Mutation tracking
        self._deleted_branches: list[str] = []
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._removed_worktrees: list[Path] = []
        self._checked_out_branches: list[tuple[Path, str]] = []
        self._detached_checkouts: list[tuple[Path, str]] = []
        self._fetched_branches: list[tuple[str, str]] = []
        self._pulled_branches: list[tuple[str, str, bool]] = []
        self._chdir_history: list[Path] = []
        self._created_tracking_branches: list[tuple[str, str]] = []
        self._staged_files: list[str] = []
        self._commits: list[tuple[Path, str, list[str], bool]] = []
        self._pushed_branches: list[tuple[str, str, bool]] = []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        return self._worktrees.get(repo_root, [])

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        return self._current_branches.get(cwd)

    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect the default branch."""
        # If configured trunk is provided, validate it exists
        if configured is not None:
            is_valid = (
                repo_root in self._default_branches
                and self._default_branches[repo_root] == configured
            )
            if is_valid:
                return configured
            # For testing, we check if ANY branch with that name exists
            # In a real fake, we'd track all branches, but for simplicity
            # we just validate against default
            click.echo(
                f"Error: Configured trunk branch '{configured}' does not exist in repository.\n"
                f"Update your configuration in pyproject.toml or create the branch.",
                err=True,
            )
            raise SystemExit(1)

        # Auto-detection path
        if repo_root in self._default_branches:
            return self._default_branches[repo_root]
        click.echo("Error: Could not find 'main' or 'master' branch.", err=True)
        raise SystemExit(1)

    def get_trunk_branch(self, repo_root: Path) -> str:
        """Get the trunk branch name for the repository."""
        if repo_root in self._trunk_branches:
            return self._trunk_branches[repo_root]
        # Default to "main" if not configured
        return "main"

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        return self._local_branches.get(repo_root, [])

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository (fake implementation)."""
        return self._remote_branches.get(repo_root, [])

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch (fake implementation)."""
        import subprocess

        # Check if this branch should fail
        if branch in self._tracking_branch_failures:
            error_msg = self._tracking_branch_failures[branch]
            raise subprocess.CalledProcessError(
                returncode=1, cmd=["git", "branch", "--track", branch, remote_ref], stderr=error_msg
            )

        # Track this mutation
        self._created_tracking_branches.append((branch, remote_ref))

        # In the fake, we simulate branch creation by adding to local branches
        if repo_root not in self._local_branches:
            self._local_branches[repo_root] = []
        if branch not in self._local_branches[repo_root]:
            self._local_branches[repo_root].append(branch)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        return self._git_common_dirs.get(cwd)

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

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch (mutates internal state).

        Validates that the branch is not already checked out in another worktree,
        matching Git's behavior.
        """
        # Check if branch is already checked out in a different worktree
        for _repo_root, worktrees in self._worktrees.items():
            for wt in worktrees:
                if wt.branch == branch and wt.path.resolve() != cwd.resolve():
                    msg = f"fatal: '{branch}' is already checked out at '{wt.path}'"
                    raise RuntimeError(msg)

        self._current_branches[cwd] = branch
        # Update worktree branch in the worktrees list
        for repo_root, worktrees in self._worktrees.items():
            for i, wt in enumerate(worktrees):
                if wt.path.resolve() == cwd.resolve():
                    self._worktrees[repo_root][i] = WorktreeInfo(
                        path=wt.path, branch=branch, is_root=wt.is_root
                    )
                    break
        # Track the checkout
        self._checked_out_branches.append((cwd, branch))

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD (mutates internal state)."""
        # Detached HEAD means no branch is checked out (branch=None)
        self._current_branches[cwd] = None
        # Update worktree to show detached HEAD state
        for repo_root, worktrees in self._worktrees.items():
            for i, wt in enumerate(worktrees):
                if wt.path.resolve() == cwd.resolve():
                    self._worktrees[repo_root][i] = WorktreeInfo(
                        path=wt.path, branch=None, is_root=wt.is_root
                    )
                    break
        # Track the detached checkout
        self._detached_checkouts.append((cwd, ref))

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out (no-op for fake)."""
        # Fake doesn't need to track created branches unless tests verify it
        pass

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch (mutates internal state for test assertions)."""
        # Check if we should raise an exception for this branch
        if branch_name in self._delete_branch_raises:
            raise self._delete_branch_raises[branch_name]

        self._deleted_branches.append(branch_name)

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Track which branches were deleted (mutates internal state).

        Raises configured exception if branch is in delete_branch_raises mapping.
        """
        # Check if we should raise an exception for this branch
        if branch in self._delete_branch_raises:
            raise self._delete_branch_raises[branch]

        self._deleted_branches.append(branch)

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

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        return self._branch_heads.get(branch)

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

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote (fake implementation).

        Returns True if the branch exists in the configured remote branches.
        Checks for the branch in format: remote/branch (e.g., origin/feature).
        """
        remote_branches = self._remote_branches.get(repo_root, [])
        remote_ref = f"{remote}/{branch}"
        return remote_ref in remote_branches

    @property
    def deleted_branches(self) -> list[str]:
        """Get the list of branches that have been deleted.

        This property is for test assertions only.
        """
        return self._deleted_branches.copy()

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
    def checked_out_branches(self) -> list[tuple[Path, str]]:
        """Get list of branches checked out during test.

        Returns list of (cwd, branch) tuples.
        This property is for test assertions only.
        """
        return self._checked_out_branches.copy()

    @property
    def detached_checkouts(self) -> list[tuple[Path, str]]:
        """Get list of detached HEAD checkouts during test.

        Returns list of (cwd, ref) tuples.
        This property is for test assertions only.
        """
        return self._detached_checkouts.copy()

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

    @property
    def created_tracking_branches(self) -> list[tuple[str, str]]:
        """Get list of tracking branches created during test.

        Returns list of (branch, remote_ref) tuples.
        This property is for test assertions only.
        """
        return self._created_tracking_branches.copy()

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

        Simulates fetching a PR ref by creating a local branch. In real git,
        this would fetch refs/pull/<number>/head and create the branch.
        """
        # Track the fetch for test assertions
        self._fetched_branches.append((remote, f"pull/{pr_number}/head"))

        # In the fake, we simulate branch creation by adding to local branches
        if repo_root not in self._local_branches:
            self._local_branches[repo_root] = []
        if local_branch not in self._local_branches[repo_root]:
            self._local_branches[repo_root].append(local_branch)

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Record staged files for commit."""
        self._staged_files.extend(paths)

    def commit(self, cwd: Path, message: str, *, allow_empty: bool = False) -> None:
        """Record commit with staged changes."""
        self._commits.append((cwd, message, list(self._staged_files), allow_empty))
        self._staged_files = []  # Clear staged files after commit

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
    def commits(self) -> list[tuple[Path, str, list[str], bool]]:
        """Read-only access to commits for test assertions.

        Returns list of (cwd, message, staged_files, allow_empty) tuples.
        """
        return self._commits

    @property
    def pushed_branches(self) -> list[tuple[str, str, bool]]:
        """Read-only access to pushed branches for test assertions.

        Returns list of (remote, branch, set_upstream) tuples.
        """
        return self._pushed_branches
