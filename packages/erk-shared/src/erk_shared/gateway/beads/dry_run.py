"""Dry-run wrapper for Beads gateway operations."""

from erk_shared.gateway.beads.abc import BeadsGateway
from erk_shared.gateway.beads.types import BeadsIssue


class DryRunBeadsGateway(BeadsGateway):
    """Dry-run wrapper that delegates read-only operations.

    Read operations are delegated to the wrapped implementation.
    Write operations would return without executing (no-op behavior).

    Note: Currently list_issues is the only method. It's read-only,
    so it delegates to the wrapped implementation.
    """

    def __init__(self, wrapped: BeadsGateway) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real BeadsGateway implementation to wrap.
        """
        self._wrapped = wrapped

    def list_issues(
        self,
        *,
        labels: list[str] | None,
        status: str | None,
        limit: int | None,
    ) -> list[BeadsIssue]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.list_issues(labels=labels, status=status, limit=limit)
