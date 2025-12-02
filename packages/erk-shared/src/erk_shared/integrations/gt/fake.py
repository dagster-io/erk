"""In-memory fake implementations of GT kit operations for testing.

This module provides fake implementations with declarative setup methods that
eliminate the need for extensive subprocess mocking in tests.

Design:
- Immutable state using frozen dataclasses
- Declarative setup methods (with_branch, with_uncommitted_files, etc.)
- Automatic state transitions (commit clears uncommitted files)
- LBYL pattern: methods check state before operations
- Returns match interface contracts exactly

Note: Git operations are now provided by the core Git interface from erk_shared.git.abc.
Tests should use their own fake Git implementation or FakeGit when available.
"""

from dataclasses import dataclass, field, replace

from erk_shared.integrations.gt.abc import GitHubGtKit


@dataclass(frozen=True)
class GitHubState:
    """Immutable GitHub PR state."""

    pr_numbers: dict[str, int] = field(default_factory=dict)
    pr_urls: dict[str, str] = field(default_factory=dict)
    pr_states: dict[str, str] = field(default_factory=dict)
    pr_titles: dict[int, str] = field(default_factory=dict)
    pr_bodies: dict[int, str] = field(default_factory=dict)
    pr_diffs: dict[int, str] = field(default_factory=dict)
    pr_mergeability: dict[int, tuple[str, str]] = field(default_factory=dict)
    merge_success: bool = True
    pr_update_success: bool = True
    pr_delay_attempts_until_visible: int = 0
    authenticated: bool = True
    auth_username: str | None = "test-user"
    auth_hostname: str | None = "github.com"


class FakeGitHubGtKitOps(GitHubGtKit):
    """Fake GitHub operations with in-memory state."""

    def __init__(self, state: GitHubState | None = None) -> None:
        """Initialize with optional initial state."""
        self._state = state if state is not None else GitHubState()
        self._current_branch = "main"
        self._pr_info_attempt_count = 0

    def set_current_branch(self, branch: str) -> None:
        """Set current branch (needed for context)."""
        self._current_branch = branch

    def get_state(self) -> GitHubState:
        """Get current state (for testing assertions)."""
        return self._state

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status."""
        if not self._state.authenticated:
            return (False, None, None)
        return (True, self._state.auth_username, self._state.auth_hostname)

    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL for current branch."""
        # Simulate PR delay if configured
        if self._state.pr_delay_attempts_until_visible > 0:
            self._pr_info_attempt_count += 1
            if self._pr_info_attempt_count <= self._state.pr_delay_attempts_until_visible:
                return None

        if self._current_branch not in self._state.pr_numbers:
            return None

        pr_number = self._state.pr_numbers[self._current_branch]
        pr_url = self._state.pr_urls.get(
            self._current_branch, f"https://github.com/repo/pull/{pr_number}"
        )
        return (pr_number, pr_url)

    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state for current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None

        pr_number = self._state.pr_numbers[self._current_branch]
        pr_state = self._state.pr_states.get(self._current_branch, "OPEN")
        return (pr_number, pr_state)

    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False

        if not self._state.pr_update_success:
            return False

        pr_number = self._state.pr_numbers[self._current_branch]

        # Create new state with updated metadata
        new_titles = {**self._state.pr_titles, pr_number: title}
        new_bodies = {**self._state.pr_bodies, pr_number: body}
        self._state = replace(self._state, pr_titles=new_titles, pr_bodies=new_bodies)
        return True

    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review (fake always succeeds if PR exists)."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        # In the fake, marking as ready always succeeds if PR exists
        return True

    def get_pr_title(self) -> str | None:
        """Get the title of the PR for the current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None
        pr_number = self._state.pr_numbers[self._current_branch]
        return self._state.pr_titles.get(pr_number)

    def get_pr_body(self) -> str | None:
        """Get the body of the PR for the current branch."""
        if self._current_branch not in self._state.pr_numbers:
            return None
        pr_number = self._state.pr_numbers[self._current_branch]
        return self._state.pr_bodies.get(pr_number)

    def merge_pr(self, *, subject: str | None = None, body: str | None = None) -> bool:
        """Merge the PR with configurable success/failure."""
        if self._current_branch not in self._state.pr_numbers:
            return False
        return self._state.merge_success

    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL (fake returns test URL)."""
        return f"https://app.graphite.com/github/pr/test-owner/test-repo/{pr_number}"

    def get_pr_diff(self, pr_number: int) -> str:
        """Get PR diff from configured state or return default."""
        if pr_number in self._state.pr_diffs:
            return self._state.pr_diffs[pr_number]
        # Return a simple default diff
        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL for branch from fake state."""
        if branch not in self._state.pr_numbers:
            return (None, None)

        pr_number = self._state.pr_numbers[branch]
        pr_url = self._state.pr_urls.get(branch, f"https://github.com/repo/pull/{pr_number}")
        return (pr_number, pr_url)

    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from fake state."""
        # Default: MERGEABLE/CLEAN unless configured otherwise
        return self._state.pr_mergeability.get(pr_number, ("MERGEABLE", "CLEAN"))
