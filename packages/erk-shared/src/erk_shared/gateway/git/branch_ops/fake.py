"""Fake Git branch operations for testing."""

from __future__ import annotations

import subprocess
from pathlib import Path

from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo, WorktreeInfo
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps


class FakeGitBranchOps(GitBranchOps):
    """In-memory fake implementation of Git branch operations.

    State Management:
    -----------------
    This fake maintains mutable state to simulate git's stateful behavior.
    Operations like create_branch, checkout_branch modify internal state.
    State changes are visible to subsequent method calls within the same test.

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - created_branches: Branches created via create_branch()
    - deleted_branches: Branches deleted via delete_branch()
    - checked_out_branches: Branches checked out via checkout_branch()
    - detached_checkouts: Refs checked out via checkout_detached()
    - created_tracking_branches: Tracking branches created via create_tracking_branch()
    """

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        current_branches: dict[Path, str | None] | None = None,
        local_branches: dict[Path, list[str]] | None = None,
        remote_branches: dict[Path, list[str]] | None = None,
        branch_heads: dict[str, str] | None = None,
        trunk_branches: dict[Path, str] | None = None,
        ahead_behind: dict[tuple[Path, str], tuple[int, int]] | None = None,
        branch_divergence: dict[tuple[Path, str, str], BranchDivergence] | None = None,
        branch_sync_info: dict[Path, dict[str, BranchSyncInfo]] | None = None,
        branch_issues: dict[str, int | None] | None = None,
        behind_commit_authors: dict[tuple[Path, str], list[str]] | None = None,
        branch_last_commit_times: dict[tuple[Path, str, str], str | None] | None = None,
        branch_commits_with_authors: dict[tuple[Path, str, str, int], list[dict[str, str]]]
        | None = None,
        delete_branch_raises: dict[str, Exception] | None = None,
        tracking_branch_failures: dict[str, str] | None = None,
    ) -> None:
        """Create FakeGitBranchOps with pre-configured state.

        Args:
            worktrees: Mapping of repo_root -> list of worktrees (for checkout validation)
            current_branches: Mapping of cwd -> current branch (updated by checkout)
            local_branches: Mapping of repo_root -> list of local branch names
            remote_branches: Mapping of repo_root -> list of remote branch names
            branch_heads: Mapping of branch name -> commit SHA
            trunk_branches: Mapping of repo_root -> trunk branch name
            ahead_behind: Mapping of (cwd, branch) -> (ahead, behind) tuple
            branch_divergence: Mapping of (cwd, branch, remote) -> BranchDivergence
            branch_sync_info: Mapping of repo_root -> dict of branch -> BranchSyncInfo
            branch_issues: Mapping of branch name -> issue number
            behind_commit_authors: Mapping of (cwd, branch) -> list of author names
            branch_last_commit_times: Mapping of (repo_root, branch, trunk) -> timestamp
            branch_commits_with_authors: Mapping of (repo_root, branch, trunk, limit) -> commits
            delete_branch_raises: Mapping of branch name -> exception to raise on delete
            tracking_branch_failures: Mapping of branch name -> error message to raise
                when create_tracking_branch is called for that branch
        """
        self._worktrees = worktrees if worktrees is not None else {}
        self._current_branches = current_branches if current_branches is not None else {}
        self._local_branches = local_branches if local_branches is not None else {}
        self._remote_branches = remote_branches if remote_branches is not None else {}
        self._branch_heads = branch_heads if branch_heads is not None else {}
        self._trunk_branches = trunk_branches if trunk_branches is not None else {}
        self._ahead_behind = ahead_behind if ahead_behind is not None else {}
        self._branch_divergence = branch_divergence if branch_divergence is not None else {}
        self._branch_sync_info = branch_sync_info if branch_sync_info is not None else {}
        self._branch_issues = branch_issues if branch_issues is not None else {}
        self._behind_commit_authors = (
            behind_commit_authors if behind_commit_authors is not None else {}
        )
        self._branch_last_commit_times = (
            branch_last_commit_times if branch_last_commit_times is not None else {}
        )
        self._branch_commits_with_authors = (
            branch_commits_with_authors if branch_commits_with_authors is not None else {}
        )
        self._delete_branch_raises = (
            delete_branch_raises if delete_branch_raises is not None else {}
        )
        self._tracking_branch_failures = (
            tracking_branch_failures if tracking_branch_failures is not None else {}
        )

        # Mutation tracking
        self._created_branches: list[
            tuple[Path, str, str, bool]
        ] = []  # (cwd, branch_name, start_point, force)
        self._deleted_branches: list[str] = []
        self._checked_out_branches: list[tuple[Path, str]] = []
        self._detached_checkouts: list[tuple[Path, str]] = []
        self._created_tracking_branches: list[tuple[str, str]] = []  # (branch, remote_ref)

    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Create a new branch without checking it out.

        Tracks the branch creation for test assertions via created_branches property.
        """
        self._created_branches.append((cwd, branch_name, start_point, force))

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch (mutates internal state for test assertions).

        If delete_branch_raises contains a CalledProcessError, it is wrapped in
        RuntimeError to match run_subprocess_with_context behavior.
        """
        # Check if we should raise an exception for this branch
        if branch_name in self._delete_branch_raises:
            exc = self._delete_branch_raises[branch_name]
            # Wrap CalledProcessError in RuntimeError to match run_subprocess_with_context
            if isinstance(exc, subprocess.CalledProcessError):
                raise RuntimeError(f"Failed to delete branch {branch_name}") from exc
            raise exc

        self._deleted_branches.append(branch_name)

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

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch (fake implementation)."""
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

    @property
    def created_branches(self) -> list[tuple[Path, str, str, bool]]:
        """Get list of branches created during test.

        Returns list of (cwd, branch_name, start_point, force) tuples.
        This property is for test assertions only.
        """
        return self._created_branches.copy()

    @property
    def deleted_branches(self) -> list[str]:
        """Get the list of branches that have been deleted.

        This property is for test assertions only.
        """
        return self._deleted_branches.copy()

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
    def created_tracking_branches(self) -> list[tuple[str, str]]:
        """Get list of tracking branches created during test.

        Returns list of (branch, remote_ref) tuples.
        This property is for test assertions only.
        """
        return self._created_tracking_branches.copy()

    # Methods to share state with FakeGit
    def link_state_from_git(
        self,
        worktrees: dict[Path, list[WorktreeInfo]],
        current_branches: dict[Path, str | None],
        local_branches: dict[Path, list[str]],
        remote_branches: dict[Path, list[str]],
        branch_heads: dict[str, str],
        trunk_branches: dict[Path, str],
        ahead_behind: dict[tuple[Path, str], tuple[int, int]],
        branch_divergence: dict[tuple[Path, str, str], BranchDivergence],
        branch_sync_info: dict[Path, dict[str, BranchSyncInfo]],
        branch_issues: dict[str, int | None],
        behind_commit_authors: dict[tuple[Path, str], list[str]],
        branch_last_commit_times: dict[tuple[Path, str, str], str | None],
        branch_commits_with_authors: dict[tuple[Path, str, str, int], list[dict[str, str]]],
    ) -> None:
        """Link mutable state from FakeGit to keep in sync.

        This allows FakeGitBranchOps to operate on the same state as FakeGit
        when both are used together.

        Args:
            worktrees: Reference to FakeGit's worktrees dict
            current_branches: Reference to FakeGit's current_branches dict
            local_branches: Reference to FakeGit's local_branches dict
            remote_branches: Reference to FakeGit's remote_branches dict
            branch_heads: Reference to FakeGit's branch_heads dict
            trunk_branches: Reference to FakeGit's trunk_branches dict
            ahead_behind: Reference to FakeGit's ahead_behind dict
            branch_divergence: Reference to FakeGit's branch_divergence dict
            branch_sync_info: Reference to FakeGit's branch_sync_info dict
            branch_issues: Reference to FakeGit's branch_issues dict
            behind_commit_authors: Reference to FakeGit's behind_commit_authors dict
            branch_last_commit_times: Reference to FakeGit's branch_last_commit_times dict
            branch_commits_with_authors: Reference to FakeGit's branch_commits_with_authors dict
        """
        self._worktrees = worktrees
        self._current_branches = current_branches
        self._local_branches = local_branches
        self._remote_branches = remote_branches
        self._branch_heads = branch_heads
        self._trunk_branches = trunk_branches
        self._ahead_behind = ahead_behind
        self._branch_divergence = branch_divergence
        self._branch_sync_info = branch_sync_info
        self._branch_issues = branch_issues
        self._behind_commit_authors = behind_commit_authors
        self._branch_last_commit_times = branch_last_commit_times
        self._branch_commits_with_authors = branch_commits_with_authors

    def link_mutation_tracking(
        self,
        created_branches: list[tuple[Path, str, str, bool]],
        deleted_branches: list[str],
        checked_out_branches: list[tuple[Path, str]],
        detached_checkouts: list[tuple[Path, str]],
        created_tracking_branches: list[tuple[str, str]],
    ) -> None:
        """Link mutation tracking lists to allow shared tracking with FakeGit.

        This allows FakeGit.deleted_branches (etc.) to see mutations made
        via FakeGitBranchOps when used via BranchManager.

        Args:
            created_branches: Reference to FakeGit's created_branches list
            deleted_branches: Reference to FakeGit's deleted_branches list
            checked_out_branches: Reference to FakeGit's checked_out_branches list
            detached_checkouts: Reference to FakeGit's detached_checkouts list
            created_tracking_branches: Reference to FakeGit's created_tracking_branches list
        """
        self._created_branches = created_branches
        self._deleted_branches = deleted_branches
        self._checked_out_branches = checked_out_branches
        self._detached_checkouts = detached_checkouts
        self._created_tracking_branches = created_tracking_branches

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        return self._current_branches.get(cwd)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        return self._local_branches.get(repo_root, [])

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository."""
        return self._remote_branches.get(repo_root, [])

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        return self._branch_heads.get(branch)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name."""
        return self._trunk_branches.get(repo_root, "main")

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists.

        Raises:
            RuntimeError: If the specified branch doesn't exist
        """
        branches = self._local_branches.get(repo_root, [])
        if name not in branches:
            error_msg = (
                f"Error: Configured trunk branch '{name}' does not exist in repository.\n"
                f"Update your configuration in pyproject.toml or create the branch."
            )
            raise RuntimeError(error_msg)
        return name

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        remote_branches = self._remote_branches.get(repo_root, [])
        remote_ref = f"{remote}/{branch}"
        return remote_ref in remote_branches

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch."""
        return self._ahead_behind.get((cwd, branch), (0, 0))

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches."""
        return self._branch_sync_info.get(repo_root, {})

    def is_branch_diverged_from_remote(
        self, cwd: Path, branch: str, remote: str
    ) -> BranchDivergence:
        """Check if a local branch has diverged from its remote tracking branch."""
        return self._branch_divergence.get(
            (cwd, branch, remote), BranchDivergence(is_diverged=False, ahead=0, behind=0)
        )

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Extract GitHub issue number from branch name."""
        # Check pre-configured mapping first
        if branch in self._branch_issues:
            return self._branch_issues[branch]

        # Fall back to real parsing logic
        from erk_shared.naming import extract_leading_issue_number

        return extract_leading_issue_number(branch)

    def get_behind_commit_authors(self, cwd: Path, branch: str) -> list[str]:
        """Get authors of commits on remote that are not in local branch."""
        return self._behind_commit_authors.get((cwd, branch), [])

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get the author date of the most recent commit unique to a branch."""
        return self._branch_last_commit_times.get((repo_root, branch, trunk))

    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int
    ) -> list[dict[str, str]]:
        """Get commits on branch not on trunk, with author and timestamp."""
        return self._branch_commits_with_authors.get((repo_root, branch, trunk, limit), [])
