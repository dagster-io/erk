"""Verbose wrapper for Beads gateway operations."""

from erk_shared.gateway.beads.abc import BeadsGateway
from erk_shared.gateway.beads.types import BeadsIssue


class PrintingBeadsGateway(BeadsGateway):
    """Verbose wrapper that prints mutations and delegates reads silently.

    Read operations are delegated silently to the wrapped implementation.
    Write operations would print the action, then delegate.

    Note: Currently list_issues is the only method. It's read-only,
    so it delegates silently to the wrapped implementation.
    """

    def __init__(self, wrapped: BeadsGateway) -> None:
        """Initialize printing wrapper with a real implementation.

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
        """Delegate read operation silently to wrapped implementation."""
        return self._wrapped.list_issues(labels=labels, status=status, limit=limit)
