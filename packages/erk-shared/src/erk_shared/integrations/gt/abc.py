"""Structural typing interface for GT kit operations.

This module defines a Protocol interface for Graphite (gt) and GitHub (gh) operations
used by GT kit CLI commands. Using Protocol enables structural typing, allowing any
object with the required attributes (like ErkContext) to be used without explicit
inheritance.

Design:
- Protocol-based GtKit interface that combines Git, GitHub, Graphite, and AI attributes
- Enables structural typing: ErkContext or any object with these attributes works
- Return values match existing subprocess patterns (str | None, bool, etc.)
- LBYL pattern: operations check state, return None/False on failure

Note: Git operations are provided by the core Git interface from erk_shared.git.abc.
GitHub operations use the main GitHub ABC from erk_shared.github.
Claude operations use the ClaudeExecutor ABC from erk_shared.integrations.claude.
"""

from typing import Protocol

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.integrations.claude.abc import ClaudeExecutor
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.time.abc import Time


class GtKit(Protocol):
    """Structural typing interface combining all GT kit operations.

    This Protocol provides a single injection point for all git, Graphite,
    GitHub, and AI operations used by GT kit CLI commands.

    Uses Protocol for structural typing compatibility, meaning any object with
    git, github, graphite, and claude attributes can be used directly without
    explicit inheritance.

    GitHub operations use the main GitHub ABC from erk_shared.github which
    provides methods that take repo_root as a parameter rather than operating
    on the "current" branch.

    AI operations use the ClaudeExecutor ABC from erk_shared.integrations.claude for
    both general Claude CLI execution and specific AI content generation.

    Note: Properties are used instead of bare attributes to make the Protocol
    read-only compatible. This allows frozen dataclasses (like ErkContext) to
    satisfy the Protocol - a read-only consumer accepts both read-only and
    read-write providers.
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
        """Graphite operations interface."""
        ...

    @property
    def claude(self) -> ClaudeExecutor:
        """Claude CLI executor for AI operations."""
        ...

    @property
    def time(self) -> Time:
        """Time operations interface."""
        ...
