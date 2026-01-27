"""Fake git operations for testing.

FakeGit is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from erk_shared.gateway.git.abc import (
    BranchDivergence,
    BranchSyncInfo,
    Git,
    RebaseResult,
    WorktreeInfo,
)
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.fake import FakeGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.fake import CommitRecord, FakeGitCommitOps
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.fake import FakeGitRebaseOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.fake import FakeGitRemoteOps
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.fake import FakeGitStatusOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.fake import FakeWorktree


class PushedBranch(NamedTuple):
    """Record of a branch push operation.

    Attributes:
        remote: Remote name (e.g., "origin")
        branch: Branch name that was pushed
        set_upstream: Whether -u flag was used to set upstream tracking
        force: Whether --force flag was used for force push
    """

    remote: str
    branch: str
    set_upstream: bool
    force: bool


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
    - deleted_branches: Branches deleted via delete_branch()
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
        git_ops.worktree.add_worktree(repo, wt2, branch="feature")

        # Verify mutation
        assert len(git_ops.worktree.list_worktrees(repo)) == 2
        assert (wt2, "feature") in git_ops.added_worktrees

        # Verify sequence of operations
        git_ops.checkout_branch(repo, "feature")
        git_ops.delete_branch(repo, "old-feature", force=True)
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
        behind_commit_authors: dict[tuple[Path, str], list[str]] | None = None,
        branch_sync_info: dict[Path, dict[str, BranchSyncInfo]] | None = None,
        recent_commits: dict[Path, list[dict[str, str]]] | None = None,
        existing_paths: set[Path] | None = None,
        file_contents: dict[Path, str] | None = None,
        delete_branch_raises: dict[str, Exception] | None = None,
        local_branches: dict[Path, list[str]] | None = None,
        remote_branches: dict[Path, list[str]] | None = None,
        tracking_branch_failures: dict[str, str] | None = None,
        dirty_worktrees: set[Path] | None = None,
        branch_last_commit_times: dict[tuple[Path, str, str], str | None] | None = None,
        repository_roots: dict[Path, Path] | None = None,
        diff_to_branch: dict[tuple[Path, str], str] | None = None,
        merge_conflicts: dict[tuple[str, str], bool] | None = None,
        commits_ahead: dict[tuple[Path, str], int] | None = None,
        remote_urls: dict[tuple[Path, str], str] | None = None,
        add_all_raises: Exception | None = None,
        fetch_branch_raises: Exception | None = None,
        pull_branch_raises: Exception | None = None,
        branch_issues: dict[str, int | None] | None = None,
        conflicted_files: list[str] | None = None,
        rebase_in_progress: bool | Callable[[Path], bool] = False,
        rebase_continue_raises: Exception | None = None,
        rebase_continue_clears_rebase: bool = False,
        commit_messages_since: dict[tuple[Path, str], list[str]] | None = None,
        head_commit_messages_full: dict[Path, str] | None = None,
        git_user_name: str | None = None,
        branch_commits_with_authors: dict[tuple[Path, str, str, int], list[dict[str, str]]]
        | None = None,
        push_to_remote_raises: Exception | None = None,
        existing_tags: set[str] | None = None,
        branch_divergence: dict[tuple[Path, str, str], BranchDivergence] | None = None,
        rebase_onto_result: RebaseResult | None = None,
        rebase_abort_raises: Exception | None = None,
        pull_rebase_raises: Exception | None = None,
        merge_bases: dict[tuple[str, str], str] | None = None,
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
            behind_commit_authors: Mapping of (cwd, branch) -> list of author names
                for commits on remote but not locally
            branch_sync_info: Mapping of repo_root -> dict of branch name -> BranchSyncInfo
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
            branch_last_commit_times: Mapping of (repo_root, branch, trunk) -> ISO 8601 timestamp
            repository_roots: Mapping of cwd -> repository root path
            diff_to_branch: Mapping of (cwd, branch) -> diff output
            merge_conflicts: Mapping of (base_branch, head_branch) -> has conflicts bool
            commits_ahead: Mapping of (cwd, base_branch) -> commit count
            remote_urls: Mapping of (repo_root, remote_name) -> remote URL
            add_all_raises: Exception to raise when add_all() is called
            fetch_branch_raises: Exception to raise when fetch_branch() is called
            pull_branch_raises: Exception to raise when pull_branch() is called
            branch_issues: Mapping of branch name -> issue number for get_branch_issue()
            conflicted_files: List of file paths with merge conflicts
            rebase_in_progress: Whether a rebase is currently in progress.
                Can be a bool or a callable(cwd) -> bool for dynamic behavior.
            rebase_continue_raises: Exception to raise when rebase_continue() is called
            rebase_continue_clears_rebase: If True, rebase_continue() clears the rebase state
            commit_messages_since: Mapping of (cwd, base_branch) -> list of commit messages
            head_commit_messages_full: Mapping of cwd -> full commit message for HEAD
            git_user_name: Configured git user.name to return from get_git_user_name()
            branch_commits_with_authors: Mapping of (repo_root, branch, trunk, limit)
                -> commit dicts with keys: sha, author, timestamp
            push_to_remote_raises: Exception to raise when push_to_remote() is called
            existing_tags: Set of tag names that exist in the repository
            branch_divergence: Mapping of (cwd, branch, remote) -> BranchDivergence
                for is_branch_diverged_from_remote()
            rebase_onto_result: Result to return from rebase_onto(). Defaults to success.
            rebase_abort_raises: Exception to raise when rebase_abort() is called
            pull_rebase_raises: Exception to raise when pull_rebase() is called
            merge_bases: Mapping of (ref1, ref2) -> merge base commit SHA for
                get_merge_base(). Keys are ordered pairs, so (A, B) and (B, A)
                are both checked.
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
        self._behind_commit_authors = behind_commit_authors or {}
        self._branch_sync_info = branch_sync_info or {}
        self._recent_commits = recent_commits or {}
        self._existing_paths = existing_paths or set()
        self._file_contents = file_contents or {}
        self._delete_branch_raises = delete_branch_raises or {}
        self._local_branches = local_branches or {}
        self._remote_branches = remote_branches or {}
        self._tracking_branch_failures = tracking_branch_failures or {}
        self._dirty_worktrees = dirty_worktrees or set()
        self._branch_last_commit_times = branch_last_commit_times or {}
        self._repository_roots = repository_roots or {}
        self._diff_to_branch = diff_to_branch or {}
        self._merge_conflicts = merge_conflicts or {}
        self._commits_ahead = commits_ahead or {}
        self._remote_urls = remote_urls or {}
        self._add_all_raises = add_all_raises
        self._fetch_branch_raises = fetch_branch_raises
        self._pull_branch_raises = pull_branch_raises
        self._branch_issues = branch_issues or {}
        self._conflicted_files = conflicted_files or []
        self._rebase_in_progress = rebase_in_progress
        self._rebase_continue_raises = rebase_continue_raises
        self._rebase_continue_clears_rebase = rebase_continue_clears_rebase
        self._commit_messages_since = commit_messages_since or {}
        self._head_commit_messages_full = head_commit_messages_full or {}
        self._git_user_name = git_user_name
        self._branch_commits_with_authors = branch_commits_with_authors or {}
        self._push_to_remote_raises = push_to_remote_raises
        self._existing_tags: set[str] = existing_tags or set()
        self._branch_divergence = branch_divergence or {}
        self._rebase_onto_result = rebase_onto_result
        self._rebase_abort_raises = rebase_abort_raises
        self._pull_rebase_raises = pull_rebase_raises
        self._merge_bases = merge_bases or {}

        # Mutation tracking
        self._deleted_branches: list[str] = []
        self._checked_out_branches: list[tuple[Path, str]] = []
        self._detached_checkouts: list[tuple[Path, str]] = []
        self._fetched_branches: list[tuple[str, str]] = []
        self._pulled_branches: list[tuple[str, str, bool]] = []
        self._created_tracking_branches: list[tuple[str, str]] = []
        self._staged_files: list[str] = []
        self._commits: list[CommitRecord] = []
        self._pushed_branches: list[PushedBranch] = []
        self._created_branches: list[
            tuple[Path, str, str, bool]
        ] = []  # (cwd, branch_name, start_point, force)
        self._rebase_continue_calls: list[Path] = []
        self._config_settings: list[tuple[str, str, str]] = []  # (key, value, scope)
        self._created_tags: list[tuple[str, str]] = []  # (tag_name, message)
        self._pushed_tags: list[tuple[str, str]] = []  # (remote, tag_name)
        self._rebase_onto_calls: list[tuple[Path, str]] = []  # (cwd, target_ref)
        self._rebase_abort_calls: list[Path] = []
        self._pull_rebase_calls: list[tuple[Path, str, str]] = []  # (cwd, remote, branch)

        # Worktree subgateway
        self._worktree_gateway = FakeWorktree(
            worktrees=self._worktrees,
            existing_paths=self._existing_paths,
            dirty_worktrees=self._dirty_worktrees,
        )

        # Branch operations subgateway - linked to FakeGit's state
        self._branch_gateway = FakeGitBranchOps(
            worktrees=self._worktrees,
            current_branches=self._current_branches,
            local_branches=self._local_branches,
            remote_branches=self._remote_branches,
            branch_heads=self._branch_heads,
            trunk_branches=self._trunk_branches,
            ahead_behind=self._ahead_behind,
            branch_divergence=self._branch_divergence,
            branch_sync_info=self._branch_sync_info,
            branch_issues=self._branch_issues,
            behind_commit_authors=self._behind_commit_authors,
            branch_last_commit_times=self._branch_last_commit_times,
            branch_commits_with_authors=self._branch_commits_with_authors,
            delete_branch_raises=self._delete_branch_raises,
            tracking_branch_failures=self._tracking_branch_failures,
        )
        # Link mutation tracking so FakeGit properties see mutations from FakeGitBranchOps
        self._branch_gateway.link_mutation_tracking(
            created_branches=self._created_branches,
            deleted_branches=self._deleted_branches,
            checked_out_branches=self._checked_out_branches,
            detached_checkouts=self._detached_checkouts,
            created_tracking_branches=self._created_tracking_branches,
        )

        # Remote operations subgateway - linked to FakeGit's state
        self._remote_gateway = FakeGitRemoteOps(
            remote_urls=self._remote_urls,
            fetch_branch_raises=self._fetch_branch_raises,
            pull_branch_raises=self._pull_branch_raises,
            push_to_remote_raises=self._push_to_remote_raises,
            pull_rebase_raises=self._pull_rebase_raises,
        )
        # Link mutation tracking so FakeGit properties see mutations from FakeGitRemoteOps
        self._remote_gateway.link_mutation_tracking(
            fetched_branches=self._fetched_branches,
            pulled_branches=self._pulled_branches,
            pushed_branches=self._pushed_branches,
            pull_rebase_calls=self._pull_rebase_calls,
        )

        # Commit operations subgateway - linked to FakeGit's state
        self._commit_gateway = FakeGitCommitOps(
            commit_messages=self._commit_messages,
            recent_commits=self._recent_commits,
            commit_messages_since=self._commit_messages_since,
            head_commit_messages_full=self._head_commit_messages_full,
            commits_ahead=self._commits_ahead,
            add_all_raises=self._add_all_raises,
            dirty_worktrees=self._dirty_worktrees,
        )
        # Link mutation tracking so FakeGit properties see mutations from FakeGitCommitOps
        self._commit_gateway.link_mutation_tracking(
            staged_files=self._staged_files,
            commits=self._commits,
        )
        # Link mutable state so changes propagate back to FakeGit
        self._commit_gateway.link_state(
            commits_ahead=self._commits_ahead,
            dirty_worktrees=self._dirty_worktrees,
        )

        # Status operations subgateway - linked to FakeGit's state
        self._status_gateway = FakeGitStatusOps(
            staged_repos=self._repos_with_staged_changes,
            file_statuses=self._file_statuses,
            merge_conflicts=self._merge_conflicts,
            conflicted_files=self._conflicted_files,
        )
        # Link state so FakeGit modifications are visible to status subgateway
        self._status_gateway.link_state(
            staged_repos=self._repos_with_staged_changes,
            file_statuses=self._file_statuses,
            merge_conflicts=self._merge_conflicts,
            conflicted_files=self._conflicted_files,
        )

        # Rebase operations subgateway - linked to FakeGit's state
        self._rebase_gateway = FakeGitRebaseOps(
            rebase_in_progress=rebase_in_progress,
            rebase_onto_result=rebase_onto_result,
            rebase_continue_raises=rebase_continue_raises,
            rebase_continue_clears_rebase=rebase_continue_clears_rebase,
            rebase_abort_raises=rebase_abort_raises,
        )
        # Link mutation tracking
        self._rebase_gateway.link_mutation_tracking(
            rebase_onto_calls=self._rebase_onto_calls,
            rebase_continue_calls=self._rebase_continue_calls,
            rebase_abort_calls=self._rebase_abort_calls,
        )

    @property
    def worktree(self) -> Worktree:
        """Access worktree operations subgateway."""
        return self._worktree_gateway

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        return self._branch_gateway

    @property
    def remote(self) -> GitRemoteOps:
        """Access remote operations subgateway."""
        return self._remote_gateway

    @property
    def commit(self) -> GitCommitOps:
        """Access commit operations subgateway."""
        return self._commit_gateway

    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway."""
        return self._status_gateway

    @property
    def rebase(self) -> GitRebaseOps:
        """Access rebase operations subgateway."""
        return self._rebase_gateway

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

    @property
    def deleted_branches(self) -> list[str]:
        """Get the list of branches that have been deleted.

        This property is for test assertions only.
        """
        return self._deleted_branches.copy()

    @property
    def created_branches(self) -> list[tuple[Path, str, str, bool]]:
        """Get list of branches created during test.

        Returns list of (cwd, branch_name, start_point, force) tuples.
        This property is for test assertions only.
        """
        return self._created_branches.copy()

    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        """Get list of worktrees added during test.

        Returns list of (path, branch) tuples.
        This property is for test assertions only.
        """
        return self._worktree_gateway.added_worktrees

    @property
    def removed_worktrees(self) -> list[Path]:
        """Get list of worktrees removed during test.

        This property is for test assertions only.
        """
        return self._worktree_gateway.removed_worktrees

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
        return self._worktree_gateway.chdir_history

    @property
    def created_tracking_branches(self) -> list[tuple[str, str]]:
        """Get list of tracking branches created during test.

        Returns list of (branch, remote_ref) tuples.
        This property is for test assertions only.
        """
        return self._created_tracking_branches.copy()

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

    @property
    def staged_files(self) -> list[str]:
        """Read-only access to currently staged files for test assertions."""
        return self._staged_files

    @property
    def commits(self) -> list[CommitRecord]:
        """Read-only access to commits for test assertions.

        Returns list of CommitRecord objects with cwd, message, and staged_files.
        """
        return list(self._commits)

    @property
    def pushed_branches(self) -> list[PushedBranch]:
        """Read-only access to pushed branches for test assertions.

        Returns list of PushedBranch named tuples with fields:
        remote, branch, set_upstream, force.
        """
        return self._pushed_branches

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

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """Record git config set for test assertions."""
        self._config_settings.append((key, value, scope))

    @property
    def config_settings(self) -> list[tuple[str, str, str]]:
        """Get list of config settings applied during test.

        Returns list of (key, value, scope) tuples.
        This property is for test assertions only.
        """
        return self._config_settings.copy()

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        return self._git_user_name

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists in the fake state."""
        return tag_name in self._existing_tags

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag (mutates internal state)."""
        self._existing_tags.add(tag_name)
        self._created_tags.append((tag_name, message))

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote (tracks mutation)."""
        self._pushed_tags.append((remote, tag_name))

    @property
    def created_tags(self) -> list[tuple[str, str]]:
        """Get list of tags created during test.

        Returns list of (tag_name, message) tuples.
        This property is for test assertions only.
        """
        return self._created_tags.copy()

    @property
    def pushed_tags(self) -> list[tuple[str, str]]:
        """Get list of tags pushed during test.

        Returns list of (remote, tag_name) tuples.
        This property is for test assertions only.
        """
        return self._pushed_tags.copy()

    @property
    def pull_rebase_calls(self) -> list[tuple[Path, str, str]]:
        """Get list of pull_rebase calls for test assertions.

        Returns list of (cwd, remote, branch) tuples.
        This property is for test assertions only.
        """
        return list(self._pull_rebase_calls)

    @property
    def rebase_onto_calls(self) -> list[tuple[Path, str]]:
        """Get list of rebase_onto calls for test assertions.

        Returns list of (cwd, target_ref) tuples.
        This property is for test assertions only.
        """
        return self._rebase_gateway.rebase_onto_calls

    @property
    def rebase_abort_calls(self) -> list[Path]:
        """Get list of rebase_abort calls for test assertions.

        This property is for test assertions only.
        """
        return self._rebase_gateway.rebase_abort_calls

    @property
    def rebase_continue_calls(self) -> list[Path]:
        """Get list of rebase_continue calls for test assertions.

        This property is for test assertions only.
        """
        return self._rebase_gateway.rebase_continue_calls

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs.

        Checks both (ref1, ref2) and (ref2, ref1) key orderings.
        """
        if (ref1, ref2) in self._merge_bases:
            return self._merge_bases[(ref1, ref2)]
        if (ref2, ref1) in self._merge_bases:
            return self._merge_bases[(ref2, ref1)]
        return None

    def create_linked_branch_ops(self) -> FakeGitBranchOps:
        """Return the FakeGitBranchOps linked to this FakeGit's state.

        The returned FakeGitBranchOps shares mutable state and mutation tracking
        with this FakeGit instance. This allows tests to check FakeGit properties
        like deleted_branches while mutations happen through BranchManager.

        Returns:
            FakeGitBranchOps with linked state and mutation tracking

        Note:
            This method now returns the same instance as self.branch, which is
            already linked during __init__.
        """
        return self._branch_gateway
