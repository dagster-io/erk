"""In-memory fake implementations of GT kit operations for testing.

This module provides fake implementations with declarative setup methods that
eliminate the need for extensive subprocess mocking in tests.

Design:
- Immutable state using frozen dataclasses
- Declarative setup methods (with_branch, with_uncommitted_files, etc.)
- Automatic state transitions (commit clears uncommitted files)
- LBYL pattern: methods check state before operations
- Returns match interface contracts exactly
- GitHub operations use the main FakeGitHub from erk_shared.github
"""

from dataclasses import dataclass, field, replace
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.gt.abc import GitGtKit, GtKit


@dataclass(frozen=True)
class GitState:
    """Immutable git repository state."""

    current_branch: str = "main"
    uncommitted_files: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    branch_parents: dict[str, str] = field(default_factory=dict)
    add_success: bool = True
    trunk_branch: str = "main"
    tracked_files: list[str] = field(default_factory=list)


class FakeGitGtKitOps(GitGtKit):
    """Fake git operations with in-memory state."""

    def __init__(self, state: GitState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GitState()

    def get_state(self) -> GitState:
        """Get current state (for testing assertions)."""
        return self._state

    def get_current_branch(self) -> str | None:
        """Get the name of the current branch."""
        if not self._state.current_branch:
            return None
        return self._state.current_branch

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        return len(self._state.uncommitted_files) > 0

    def add_all(self) -> bool:
        """Stage all changes with configurable success/failure."""
        if not self._state.add_success:
            return False

        # Track staged files separately for proper simulation
        # In a real git workflow, add_all stages files but doesn't commit them
        # For our fake, we'll track this via a staged_files field
        if not hasattr(self, "_staged_files"):
            self._staged_files: list[str] = []
        self._staged_files = list(self._state.uncommitted_files)
        return True

    def commit(self, message: str) -> bool:
        """Create a commit and clear uncommitted files."""
        # Create new state with commit added and uncommitted files cleared
        new_commits = [*self._state.commits, message]
        # Track committed files in the state
        tracked_files = getattr(self._state, "tracked_files", [])
        new_tracked = list(set(tracked_files + self._state.uncommitted_files))
        self._state = replace(
            self._state, commits=new_commits, uncommitted_files=[], tracked_files=new_tracked
        )
        # Clear staged files after commit
        if hasattr(self, "_staged_files"):
            self._staged_files = []
        return True

    def amend_commit(self, message: str) -> bool:
        """Amend the current commit message and include any staged changes."""
        if not self._state.commits:
            return False

        # Replace last commit message
        new_commits = [*self._state.commits[:-1], message]
        # Amend should include staged files and clear uncommitted files
        # (since they're now part of the amended commit)
        tracked_files = getattr(self._state, "tracked_files", [])
        new_tracked = list(set(tracked_files + self._state.uncommitted_files))
        self._state = replace(
            self._state, commits=new_commits, uncommitted_files=[], tracked_files=new_tracked
        )
        # Clear staged files after amend
        if hasattr(self, "_staged_files"):
            self._staged_files = []
        return True

    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch.

        For fakes, this returns the total number of commits since we don't
        track per-branch commit history in detail.
        """
        return len(self._state.commits)

    def get_trunk_branch(self) -> str:
        """Get the trunk branch name for the repository."""
        return self._state.trunk_branch

    def get_repository_root(self) -> str:
        """Fake repository root."""
        return "/fake/repo/root"

    def get_diff_to_parent(self, parent_branch: str) -> str:
        """Fake diff output."""
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def check_merge_conflicts(self, base_branch: str, head_branch: str) -> bool:
        """Fake conflict checker - returns False unless configured otherwise."""
        # Check if fake has been configured to simulate conflicts
        if hasattr(self, "_simulated_conflicts"):
            return (base_branch, head_branch) in self._simulated_conflicts
        return False

    def simulate_conflict(self, base_branch: str, head_branch: str) -> None:
        """Configure fake to simulate conflicts for specific branch pair."""
        if not hasattr(self, "_simulated_conflicts"):
            self._simulated_conflicts: set[tuple[str, str]] = set()
        self._simulated_conflicts.add((base_branch, head_branch))

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Fake git common dir - returns parent of cwd as .git location."""
        return cwd / ".git"

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Fake branch head - returns a fake SHA."""
        return f"fake-sha-for-{branch}"

    def checkout_branch(self, branch: str) -> bool:
        """Fake checkout - always succeeds and updates current branch."""
        self._state = replace(self._state, current_branch=branch)
        return True


class FakeGtKit(GtKit):
    """Fake composite operations for testing.

    Provides declarative setup methods for common test scenarios.
    Uses FakeGitHub from erk_shared.github for GitHub operations.
    """

    def __init__(
        self,
        git_state: GitState | None = None,
        github: FakeGitHub | None = None,
        main_graphite: Graphite | None = None,
    ) -> None:
        """Initialize with optional initial states.

        Args:
            git_state: Initial git state (optional)
            github: FakeGitHub instance to use (optional, default empty)
            main_graphite: Graphite instance to use (optional, default FakeGraphite)
        """
        self._git = FakeGitGtKitOps(git_state)
        self._github = github if github is not None else FakeGitHub()
        self._main_graphite = main_graphite if main_graphite is not None else FakeGraphite()
        # Track PRs configured via with_pr() for rebuilding FakeGitHub
        self._configured_prs: dict[str, PullRequestInfo] = {}

    def git(self) -> FakeGitGtKitOps:
        """Get the git operations interface."""
        return self._git

    def github(self) -> GitHub:
        """Get the GitHub operations interface."""
        return self._github

    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface."""
        return self._main_graphite

    # Declarative setup methods

    def with_branch(self, branch: str, parent: str = "main") -> "FakeGtKit":
        """Set current branch and its parent.

        Args:
            branch: Branch name
            parent: Parent branch name

        Returns:
            Self for chaining
        """
        # Update git state
        git_state = self._git.get_state()
        self._git._state = replace(git_state, current_branch=branch)
        return self

    def with_uncommitted_files(self, files: list[str]) -> "FakeGtKit":
        """Set uncommitted files.

        Args:
            files: List of file paths

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, uncommitted_files=files)
        return self

    def with_commits(self, count: int) -> "FakeGtKit":
        """Add a number of commits.

        Args:
            count: Number of commits to add

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        commits = [f"commit-{i}" for i in range(count)]
        self._git._state = replace(git_state, commits=commits)
        return self

    def with_pr(
        self,
        number: int,
        *,
        url: str | None = None,
        state: str = "OPEN",
        title: str | None = None,
        body: str | None = None,
    ) -> "FakeGtKit":
        """Set PR for current branch.

        Args:
            number: PR number
            url: PR URL (auto-generated if None)
            state: PR state (default: OPEN)
            title: PR title (optional)
            body: PR body (optional)

        Returns:
            Self for chaining
        """
        branch = self._git.get_state().current_branch

        if url is None:
            url = f"https://github.com/repo/pull/{number}"

        # Create PullRequestInfo for this branch
        pr_info = PullRequestInfo(
            number=number,
            state=state,
            url=url,
            is_draft=False,
            title=title,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        )
        self._configured_prs[branch] = pr_info

        # Rebuild FakeGitHub with updated PRs
        self._github = FakeGitHub(prs=self._configured_prs.copy())
        return self

    def with_add_failure(self) -> "FakeGtKit":
        """Configure git add to fail.

        Returns:
            Self for chaining
        """
        git_state = self._git.get_state()
        self._git._state = replace(git_state, add_success=False)
        return self


# Backwards compatibility alias
FakeGtKitOps = FakeGtKit
