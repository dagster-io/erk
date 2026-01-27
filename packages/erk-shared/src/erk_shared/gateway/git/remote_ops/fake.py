"""Fake implementation of Git remote operations for testing."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps

if TYPE_CHECKING:
    # Import PushedBranch type from parent module to avoid circular import
    from erk_shared.gateway.git.fake import PushedBranch


class FakeGitRemoteOps(GitRemoteOps):
    """In-memory fake implementation of Git remote operations.

    This fake accepts pre-configured state in its constructor and tracks
    mutations for test assertions.

    Constructor Injection:
    ---------------------
    - remote_urls: Mapping of (repo_root, remote_name) -> remote URL
    - pull_branch_raises: Exception to raise when pull_branch() is called
    - push_to_remote_raises: Exception to raise when push_to_remote() is called
    - pull_rebase_raises: Exception to raise when pull_rebase() is called

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - fetched_branches: List of (remote, branch) tuples from fetch_branch()
    - pulled_branches: List of (remote, branch, ff_only) tuples from pull_branch()
    - pushed_branches: List of PushedBranch named tuples from push_to_remote()
      (PushedBranch is defined in erk_shared.gateway.git.fake)
    - pull_rebase_calls: List of (cwd, remote, branch) tuples from pull_rebase()
    """

    def __init__(
        self,
        *,
        remote_urls: dict[tuple[Path, str], str] | None = None,
        pull_branch_raises: Exception | None = None,
        push_to_remote_raises: Exception | None = None,
        pull_rebase_raises: Exception | None = None,
    ) -> None:
        """Create FakeGitRemoteOps with pre-configured state.

        Args:
            remote_urls: Mapping of (repo_root, remote_name) -> remote URL
            pull_branch_raises: Exception to raise when pull_branch() is called
            push_to_remote_raises: Exception to raise when push_to_remote() is called
            pull_rebase_raises: Exception to raise when pull_rebase() is called
        """
        self._remote_urls = remote_urls or {}
        self._pull_branch_raises = pull_branch_raises
        self._push_to_remote_raises = push_to_remote_raises
        self._pull_rebase_raises = pull_rebase_raises

        # Mutation tracking
        self._fetched_branches: list[tuple[str, str]] = []
        self._pulled_branches: list[tuple[str, str, bool]] = []
        # Note: _pushed_branches uses PushedBranch from git.fake module
        self._pushed_branches: list[PushedBranch] = []
        self._pull_rebase_calls: list[tuple[Path, str, str]] = []

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote (tracks mutation)."""
        self._fetched_branches.append((remote, branch))

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote (tracks mutation)."""
        self._pulled_branches.append((remote, branch, ff_only))
        if self._pull_branch_raises is not None:
            raise self._pull_branch_raises

    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """Record PR ref fetch in fake storage (mutates internal state).

        Simulates fetching a PR ref by tracking the operation.
        In real git, this would fetch refs/pull/<number>/head.
        """
        # Track the fetch for test assertions
        self._fetched_branches.append((remote, f"pull/{pr_number}/head"))

    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool = False,
        force: bool = False,
    ) -> None:
        """Record push to remote, or raise if failure configured."""
        # Import at runtime to avoid circular dependency
        from erk_shared.gateway.git.fake import PushedBranch

        if self._push_to_remote_raises is not None:
            raise self._push_to_remote_raises
        self._pushed_branches.append(
            PushedBranch(remote=remote, branch=branch, set_upstream=set_upstream, force=force)
        )

    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None:
        """Pull and rebase from remote branch.

        Tracks call for test assertions. Raises configured exception if set.
        """
        self._pull_rebase_calls.append((cwd, remote, branch))
        if self._pull_rebase_raises is not None:
            raise self._pull_rebase_raises

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote.

        Raises:
            ValueError: If remote doesn't exist or has no URL
        """
        url = self._remote_urls.get((repo_root, remote))
        if url is None:
            raise ValueError(f"Remote '{remote}' not found in repository")
        return url

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def fetched_branches(self) -> list[tuple[str, str]]:
        """Read-only access to fetched branches for test assertions.

        Returns list of (remote, branch) tuples.
        """
        return list(self._fetched_branches)

    @property
    def pulled_branches(self) -> list[tuple[str, str, bool]]:
        """Read-only access to pulled branches for test assertions.

        Returns list of (remote, branch, ff_only) tuples.
        """
        return list(self._pulled_branches)

    @property
    def pushed_branches(self) -> list[PushedBranch]:
        """Read-only access to pushed branches for test assertions.

        Returns list of PushedBranch named tuples with fields:
        remote, branch, set_upstream, force.
        """
        return list(self._pushed_branches)

    @property
    def pull_rebase_calls(self) -> list[tuple[Path, str, str]]:
        """Get list of pull_rebase calls for test assertions.

        Returns list of (cwd, remote, branch) tuples.
        This property is for test assertions only.
        """
        return list(self._pull_rebase_calls)

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        fetched_branches: list[tuple[str, str]],
        pulled_branches: list[tuple[str, str, bool]],
        pushed_branches: list[PushedBranch],
        pull_rebase_calls: list[tuple[Path, str, str]],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        This allows FakeGit to expose remote operations mutations through its
        own properties while delegating to this subgateway.

        Args:
            fetched_branches: FakeGit's _fetched_branches list
            pulled_branches: FakeGit's _pulled_branches list
            pushed_branches: FakeGit's _pushed_branches list
            pull_rebase_calls: FakeGit's _pull_rebase_calls list
        """
        self._fetched_branches = fetched_branches
        self._pulled_branches = pulled_branches
        self._pushed_branches = pushed_branches
        self._pull_rebase_calls = pull_rebase_calls
