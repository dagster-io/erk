"""Fake GitHub Actions admin operations for testing.

FakeGitHubAdmin is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path
from typing import Any

from erk_shared.github.types import GitHubRepoLocation

from erk.core.implementation_queue.github.abc import GitHubAdmin


class FakeGitHubAdmin(GitHubAdmin):
    """In-memory fake implementation of GitHub Actions admin operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults.

    Mutation Tracking:
    -----------------
    Tracks permission changes via read-only properties for test assertions:
    - set_permission_calls: List of (repo_root, enabled) tuples
    """

    def __init__(
        self,
        *,
        workflow_permissions: dict[str, Any] | None = None,
    ) -> None:
        """Create FakeGitHubAdmin with pre-configured state.

        Args:
            workflow_permissions: Dict to return from get_workflow_permissions.
                                 Defaults to {"default_workflow_permissions": "read",
                                             "can_approve_pull_request_reviews": False}
        """
        # Default permissions state (PR creation disabled)
        self._workflow_permissions = workflow_permissions or {
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": False,
        }

        # Mutation tracking
        self._set_permission_calls: list[tuple[Path, bool]] = []

    def get_workflow_permissions(self, location: GitHubRepoLocation) -> dict[str, Any]:
        """Return pre-configured workflow permissions."""
        return self._workflow_permissions

    def set_workflow_pr_permissions(self, location: GitHubRepoLocation, enabled: bool) -> None:
        """Record permission change in mutation tracking list.

        Also updates internal state to simulate permission change.
        """
        self._set_permission_calls.append((location.root, enabled))
        # Update internal state to match what GitHub would do
        self._workflow_permissions["can_approve_pull_request_reviews"] = enabled

    @property
    def set_permission_calls(self) -> list[tuple[Path, bool]]:
        """Read-only access to tracked permission changes for test assertions."""
        return self._set_permission_calls
