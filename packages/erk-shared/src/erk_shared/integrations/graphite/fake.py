"""Fake Graphite operations for testing.

FakeGraphite is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.github.types import GitHubRepoId, PullRequestInfo
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.types import BranchMetadata


class FakeGraphite(Graphite):
    """In-memory fake implementation of Graphite operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults (empty dicts).
    """

    def __init__(
        self,
        *,
        sync_raises: Exception | None = None,
        restack_raises: Exception | None = None,
        submit_branch_raises: Exception | None = None,
        track_branch_raises: Exception | None = None,
        squash_branch_raises: Exception | None = None,
        submit_stack_raises: Exception | None = None,
        pr_info: dict[str, PullRequestInfo] | None = None,
        branches: dict[str, BranchMetadata] | None = None,
        stacks: dict[str, list[str]] | None = None,
        authenticated: bool = True,
        auth_username: str | None = "test-user",
        auth_repo_info: str | None = "owner/repo",
    ) -> None:
        """Create FakeGraphite with pre-configured state.

        Args:
            sync_raises: Exception to raise when sync() is called (for testing error cases)
            restack_raises: Exception to raise when restack() is called
            submit_branch_raises: Exception to raise when submit_branch() is called
            track_branch_raises: Exception to raise when track_branch() is called
            squash_branch_raises: Exception to raise when squash_branch() is called
            submit_stack_raises: Exception to raise when submit_stack() is called
            pr_info: Mapping of branch name -> PullRequestInfo for get_prs_from_graphite()
            branches: Mapping of branch name -> BranchMetadata for get_all_branches()
            stacks: Mapping of branch name -> stack (list of branches from trunk to leaf)
            authenticated: Whether gt is authenticated (default True for test convenience)
            auth_username: Username returned by check_auth_status() (default "test-user")
            auth_repo_info: Repo info returned by check_auth_status() (default "owner/repo")
        """
        self._sync_raises = sync_raises
        self._restack_raises = restack_raises
        self._submit_branch_raises = submit_branch_raises
        self._track_branch_raises = track_branch_raises
        self._squash_branch_raises = squash_branch_raises
        self._submit_stack_raises = submit_stack_raises
        self._sync_calls: list[tuple[Path, bool, bool]] = []
        self._restack_calls: list[tuple[Path, bool, bool]] = []
        self._submit_branch_calls: list[tuple[Path, str, bool]] = []
        self._track_branch_calls: list[tuple[Path, str, str]] = []
        self._squash_branch_calls: list[tuple[Path, bool]] = []
        self._submit_stack_calls: list[tuple[Path, bool, bool, bool]] = []
        self._pr_info = pr_info if pr_info is not None else {}
        self._branches = branches if branches is not None else {}
        self._stacks = stacks if stacks is not None else {}
        self._authenticated = authenticated
        self._auth_username = auth_username
        self._auth_repo_info = auth_repo_info
        self._check_auth_status_calls: list[None] = []

    def get_graphite_url(self, repo_id: GitHubRepoId, pr_number: int) -> str:
        """Get Graphite PR URL (constructs URL directly)."""
        return f"https://app.graphite.com/github/pr/{repo_id.owner}/{repo_id.repo}/{pr_number}"

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Fake sync operation.

        Tracks calls for verification and raises configured exception if set.
        """
        self._sync_calls.append((repo_root, force, quiet))

        if self._sync_raises is not None:
            raise self._sync_raises

    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """Fake restack operation.

        Tracks calls for verification and raises configured exception if set.
        """
        self._restack_calls.append((repo_root, no_interactive, quiet))

        if self._restack_raises is not None:
            raise self._restack_raises

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Return pre-configured PR info for tests."""
        return self._pr_info.copy()

    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Return pre-configured branch metadata for tests."""
        return self._branches.copy()

    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Return pre-configured stack for the given branch."""
        # If stacks are configured, use those
        if self._stacks:
            # Find the stack that contains this branch
            for _stack_branch, stack in self._stacks.items():
                if branch in stack:
                    return stack.copy()
            return None

        # Otherwise, build from branch metadata if available
        if not self._branches:
            return None

        if branch not in self._branches:
            return None

        # Build stack from branch metadata (simplified version)
        ancestors: list[str] = []
        current = branch
        while current in self._branches:
            ancestors.append(current)
            parent = self._branches[current].parent
            if parent is None or parent not in self._branches:
                break
            current = parent

        ancestors.reverse()

        # Add descendants
        descendants: list[str] = []
        current = branch
        while current in self._branches:
            children = self._branches[current].children
            if not children:
                break
            first_child = children[0]
            if first_child not in self._branches:
                break
            descendants.append(first_child)
            current = first_child

        return ancestors + descendants

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Fake track_branch operation.

        Tracks calls for verification and raises configured exception if set.
        Also updates internal branch metadata so get_parent_branch() and
        get_child_branches() work.
        """
        self._track_branch_calls.append((cwd, branch_name, parent_branch))

        # Also update branch metadata so get_parent_branch() can find the parent
        from erk_shared.integrations.graphite.types import BranchMetadata

        self._branches[branch_name] = BranchMetadata(
            name=branch_name,
            parent=parent_branch,
            children=[],
            is_trunk=False,
            commit_sha=None,
        )

        # Also update parent's children list so get_child_branches() works
        if parent_branch in self._branches:
            parent_metadata = self._branches[parent_branch]
            if branch_name not in parent_metadata.children:
                updated_children = [*parent_metadata.children, branch_name]
                self._branches[parent_branch] = BranchMetadata(
                    name=parent_metadata.name,
                    parent=parent_metadata.parent,
                    children=updated_children,
                    is_trunk=parent_metadata.is_trunk,
                    commit_sha=parent_metadata.commit_sha,
                )

        if self._track_branch_raises is not None:
            raise self._track_branch_raises

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Fake submit_branch operation.

        Tracks calls for verification and raises configured exception if set.
        """
        self._submit_branch_calls.append((repo_root, branch_name, quiet))

        if self._submit_branch_raises is not None:
            raise self._submit_branch_raises

    @property
    def sync_calls(self) -> list[tuple[Path, bool, bool]]:
        """Get the list of sync() calls that were made.

        Returns list of (repo_root, force, quiet) tuples.

        This property is for test assertions only.
        """
        return self._sync_calls

    @property
    def restack_calls(self) -> list[tuple[Path, bool, bool]]:
        """Get the list of restack() calls that were made.

        Returns list of (repo_root, no_interactive, quiet) tuples.

        This property is for test assertions only.
        """
        return self._restack_calls

    @property
    def track_branch_calls(self) -> list[tuple[Path, str, str]]:
        """Get the list of track_branch() calls that were made.

        Returns list of (cwd, branch_name, parent_branch) tuples.

        This property is for test assertions only.
        """
        return self._track_branch_calls

    @property
    def submit_branch_calls(self) -> list[tuple[Path, str, bool]]:
        """Get the list of submit_branch() calls that were made.

        Returns list of (repo_root, branch_name, quiet) tuples.

        This property is for test assertions only.
        """
        return self._submit_branch_calls

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status.

        Tracks calls for verification.

        Returns:
            Tuple of (is_authenticated, username, repo_info)
        """
        self._check_auth_status_calls.append(None)

        if not self._authenticated:
            return (False, None, None)

        return (True, self._auth_username, self._auth_repo_info)

    @property
    def check_auth_status_calls(self) -> list[None]:
        """Get the list of check_auth_status() calls that were made.

        Returns list of None values (one per call, no arguments tracked).

        This property is for test assertions only.
        """
        return self._check_auth_status_calls

    def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
        """Track squash_branch calls and optionally raise."""
        self._squash_branch_calls.append((repo_root, quiet))
        if self._squash_branch_raises is not None:
            raise self._squash_branch_raises

    def submit_stack(
        self, repo_root: Path, *, publish: bool = False, restack: bool = False, quiet: bool = False
    ) -> None:
        """Track submit_stack calls and optionally raise."""
        self._submit_stack_calls.append((repo_root, publish, restack, quiet))
        if self._submit_stack_raises is not None:
            raise self._submit_stack_raises

    @property
    def squash_branch_calls(self) -> list[tuple[Path, bool]]:
        """Get the list of squash_branch() calls.

        Returns list of (repo_root, quiet) tuples.
        """
        return self._squash_branch_calls

    @property
    def submit_stack_calls(self) -> list[tuple[Path, bool, bool, bool]]:
        """Get the list of submit_stack() calls.

        Returns list of (repo_root, publish, restack, quiet) tuples.
        """
        return self._submit_stack_calls
