"""Printing wrapper for GitHub Actions admin operations."""

from typing import Any

from erk_shared.github.types import GitHubRepoLocation
from erk_shared.github_admin.abc import AuthStatus, GitHubAdmin
from erk_shared.printing.base import PrintingBase


class PrintingGitHubAdmin(PrintingBase, GitHubAdmin):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or Noop).

    Usage:
        # For production
        printing_admin = PrintingGitHubAdmin(real_admin, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = NoopGitHubAdmin(real_admin)
        printing_admin = PrintingGitHubAdmin(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    def get_workflow_permissions(self, location: GitHubRepoLocation) -> dict[str, Any]:
        """Get workflow permissions (read-only, no printing)."""
        return self._wrapped.get_workflow_permissions(location)

    def set_workflow_pr_permissions(self, location: GitHubRepoLocation, enabled: bool) -> None:
        """Set workflow PR permissions with printed output."""
        self._emit(
            self._format_command(
                f"gh api --method PUT .../actions/permissions/workflow "
                f"(can_approve_pull_request_reviews={str(enabled).lower()})"
            )
        )
        self._wrapped.set_workflow_pr_permissions(location, enabled)

    def check_auth_status(self) -> AuthStatus:
        """Check auth status (read-only, no printing)."""
        return self._wrapped.check_auth_status()
