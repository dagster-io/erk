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
        submit_branch_raises: Exception | None = None,
        track_branch_raises: Exception | None = None,
        pr_info: dict[str, PullRequestInfo] | None = None,
        branches: dict[str, BranchMetadata] | None = None,
        stacks: dict[str, list[str]] | None = None,
    ) -> None:
        """Create FakeGraphite with pre-configured state.

        Args:
            sync_raises: Exception to raise when sync() is called (for testing error cases)
            submit_branch_raises: Exception to raise when submit_branch() is called
            track_branch_raises: Exception to raise when track_branch() is called
            pr_info: Mapping of branch name -> PullRequestInfo for get_prs_from_graphite()
            branches: Mapping of branch name -> BranchMetadata for get_all_branches()
            stacks: Mapping of branch name -> stack (list of branches from trunk to leaf)
        """
        self._sync_raises = sync_raises
        self._submit_branch_raises = submit_branch_raises
        self._track_branch_raises = track_branch_raises
        self._sync_calls: list[tuple[Path, bool, bool]] = []
        self._submit_branch_calls: list[tuple[Path, str, bool]] = []
        self._track_branch_calls: list[tuple[Path, str, str]] = []
        self._pr_info = pr_info if pr_info is not None else {}
        self._branches = branches if branches is not None else {}
        self._stacks = stacks if stacks is not None else {}

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
        """
        self._track_branch_calls.append((cwd, branch_name, parent_branch))

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
