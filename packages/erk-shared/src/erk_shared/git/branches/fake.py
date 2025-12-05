"""Fake git branch operations for testing."""

import subprocess
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.branches.abc import GitBranches


class FakeGitBranches(GitBranches):
    """In-memory fake implementation of git branch operations.

    State Management:
    - current_branches: dict[Path, str | None] - Mapping of cwd -> current branch
    - trunk_branches: dict[Path, str] - Mapping of repo_root -> trunk branch
    - local_branches: dict[Path, list[str]] - Mapping of repo_root -> local branches
    - remote_branches: dict[Path, list[str]] - Mapping of repo_root -> remote branches
    - branch_heads: dict[str, str] - Mapping of branch name -> commit SHA
    - worktrees: dict[Path, list[WorktreeInfo]] - For checkout validation

    Mutation Tracking:
    - deleted_branches: list[str]
    - checked_out_branches: list[tuple[Path, str]]
    - detached_checkouts: list[tuple[Path, str]]
    - created_tracking_branches: list[tuple[str, str]]
    """

    def __init__(
        self,
        *,
        current_branches: dict[Path, str | None] | None = None,
        trunk_branches: dict[Path, str] | None = None,
        local_branches: dict[Path, list[str]] | None = None,
        remote_branches: dict[Path, list[str]] | None = None,
        branch_heads: dict[str, str] | None = None,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        delete_branch_raises: dict[str, Exception] | None = None,
        tracking_branch_failures: dict[str, str] | None = None,
    ) -> None:
        self._current_branches = current_branches or {}
        self._trunk_branches = trunk_branches or {}
        self._local_branches = local_branches or {}
        self._remote_branches = remote_branches or {}
        self._branch_heads = branch_heads or {}
        self._worktrees = worktrees or {}
        self._delete_branch_raises = delete_branch_raises or {}
        self._tracking_branch_failures = tracking_branch_failures or {}

        # Mutation tracking
        self._deleted_branches: list[str] = []
        self._checked_out_branches: list[tuple[Path, str]] = []
        self._detached_checkouts: list[tuple[Path, str]] = []
        self._created_tracking_branches: list[tuple[str, str]] = []

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        return self._current_branches.get(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name."""
        if repo_root in self._trunk_branches:
            return self._trunk_branches[repo_root]
        # Default to "main" if not configured
        return "main"

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists."""
        # Check trunk_branches first
        if repo_root in self._trunk_branches and self._trunk_branches[repo_root] == name:
            return name
        # Check local_branches as well
        if repo_root in self._local_branches and name in self._local_branches[repo_root]:
            return name
        error_msg = (
            f"Error: Configured trunk branch '{name}' does not exist in repository.\n"
            f"Update your configuration in pyproject.toml or create the branch."
        )
        raise RuntimeError(error_msg)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        return self._local_branches.get(repo_root, [])

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository (fake implementation)."""
        return self._remote_branches.get(repo_root, [])

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote (fake implementation).

        Returns True if the branch exists in the configured remote branches.
        Checks for the branch in format: remote/branch (e.g., origin/feature).
        """
        remote_branches = self._remote_branches.get(repo_root, [])
        remote_ref = f"{remote}/{branch}"
        return remote_ref in remote_branches

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

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out (no-op for fake)."""
        # Fake doesn't need to track created branches unless tests verify it
        pass

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

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Track which branches were deleted (mutates internal state).

        Raises configured exception if branch is in delete_branch_raises mapping.
        If delete_branch_raises contains a CalledProcessError, it is wrapped in
        RuntimeError to match run_subprocess_with_context behavior.
        """
        # Check if we should raise an exception for this branch
        if branch in self._delete_branch_raises:
            exc = self._delete_branch_raises[branch]
            # Wrap CalledProcessError in RuntimeError to match run_subprocess_with_context
            if isinstance(exc, subprocess.CalledProcessError):
                raise RuntimeError(f"Failed to delete branch {branch}") from exc
            raise exc

        self._deleted_branches.append(branch)

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

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        return self._branch_heads.get(branch)

    # Read-only properties for test assertions
    @property
    def deleted_branches(self) -> list[str]:
        """Get the list of branches that have been deleted."""
        return self._deleted_branches.copy()

    @property
    def checked_out_branches(self) -> list[tuple[Path, str]]:
        """Get list of branches checked out during test."""
        return self._checked_out_branches.copy()

    @property
    def detached_checkouts(self) -> list[tuple[Path, str]]:
        """Get list of detached HEAD checkouts during test."""
        return self._detached_checkouts.copy()

    @property
    def created_tracking_branches(self) -> list[tuple[str, str]]:
        """Get list of tracking branches created during test."""
        return self._created_tracking_branches.copy()
