"""Protocol interface for PR submission operations.

This module defines the interface for PR submission, allowing any context
object with the required attributes (like ErkContext) to be used.
"""

from typing import Protocol

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.integrations.graphite.abc import Graphite


class PrKit(Protocol):
    """Structural typing interface for PR submission operations.

    This Protocol provides a single injection point for all git and GitHub
    operations used by the unified PR submission flow.

    Uses Protocol for structural typing compatibility, meaning any object with
    git and github attributes (like ErkContext) can be used directly without
    explicit inheritance.

    Note: Properties are used instead of bare attributes to make the Protocol
    read-only compatible. This allows frozen dataclasses (like ErkContext) to
    satisfy the Protocol.
    """

    @property
    def git(self) -> Git:
        """Git operations interface."""
        ...

    @property
    def github(self) -> GitHub:
        """GitHub operations interface."""
        ...

    @property
    def graphite(self) -> Graphite:
        """Graphite operations interface (for optional enhancement)."""
        ...
