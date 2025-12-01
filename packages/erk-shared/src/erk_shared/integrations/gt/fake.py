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
GitHub operations use the main FakeGitHub from erk_shared.github.
"""

from dataclasses import dataclass, field


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


class FakeGitHubGtKitOps:
    """Fake GitHub operations with in-memory state.

    Note: This is a legacy test helper that doesn't inherit from an ABC.
    New tests should use FakeGitHub from erk_shared.github instead, which
    provides the same functionality with better integration.
    """

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
