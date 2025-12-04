"""Adapters for bridging ErkContext with GtKit Protocol.

This module provides adapter classes that allow ErkContext components
to satisfy the GtKit Protocol interface used by GT kit operations.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.integrations.claude.abc import (
    ClaudeExecutor,
    CommitMessageResult,
    StreamEvent,
)
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.time.abc import Time

from erk.core.context import ErkContext


class NoOpClaudeExecutor(ClaudeExecutor):
    """Claude executor that does nothing.

    Used for operations that don't require Claude execution (like land-pr).
    Raises an error if called, since these operations shouldn't use Claude.
    """

    def is_claude_available(self) -> bool:
        """Return False since this is a no-op executor."""
        return False

    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
    ) -> Iterator[StreamEvent]:
        """Raise error since this should never be called."""
        raise RuntimeError(
            "Claude execution was called on an operation that doesn't support it. "
            "This is a programming error."
        )

    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Raise error since this should never be called."""
        raise RuntimeError(
            "Claude execution was called on an operation that doesn't support it. "
            "This is a programming error."
        )

    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Raise error since this should never be called."""
        raise RuntimeError(
            "Claude execution was called on an operation that doesn't support it. "
            "This is a programming error."
        )


@dataclass
class ContextGtKit:
    """Adapter that makes ErkContext components satisfy GtKit Protocol.

    Combines ErkContext's git, github, graphite with a ClaudeExecutor
    to create a composite that satisfies the GtKit Protocol.

    For operations that require Claude (like submit-pr), pass a real ClaudeExecutor.
    For operations that don't use Claude (like land-pr), use NoOpClaudeExecutor.
    """

    git: Git
    github: GitHub
    graphite: Graphite
    claude: ClaudeExecutor
    time: Time

    @classmethod
    def from_context(cls, ctx: ErkContext, claude: ClaudeExecutor | None = None) -> Self:
        """Create ContextGtKit from an ErkContext.

        Args:
            ctx: The ErkContext to adapt
            claude: Optional ClaudeExecutor. If None, uses NoOpClaudeExecutor.

        Returns:
            ContextGtKit that satisfies GtKit Protocol
        """
        return cls(
            git=ctx.git,
            github=ctx.github,
            graphite=ctx.graphite,
            claude=claude if claude is not None else NoOpClaudeExecutor(),
            time=ctx.time,
        )
