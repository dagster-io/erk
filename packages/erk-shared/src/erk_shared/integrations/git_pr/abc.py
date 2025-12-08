"""Structural typing interface for git-only PR operations.

This module defines a Protocol interface for git-only PR operations,
which only requires Git and GitHub (no Graphite). This is a subset of
the GtKit interface used for Graphite operations.

Design:
- Protocol-based GitPrKit interface that combines Git and GitHub attributes
- Enables structural typing: ErkContext or any object with these attributes works
- No Graphite dependency required
"""

from typing import Protocol

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub


class GitPrKit(Protocol):
    """Structural typing interface combining Git and GitHub operations.

    This Protocol provides a single injection point for git and GitHub
    operations used by git-only PR workflows. Unlike GtKit, it does not
    require Graphite operations.

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
