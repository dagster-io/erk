"""Adapters for bridging ErkContext with GtKit Protocol.

This module provides adapter classes that allow ErkContext components
to satisfy the GtKit Protocol interface used by GT kit operations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.integrations.ai.abc import ClaudeCLIExecutor, CommitMessageResult
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.time.abc import Time

from erk.core.context import ErkContext


class NoOpClaudeCLIExecutor(ClaudeCLIExecutor):
    """Claude CLI executor that does nothing.

    Used for operations that don't require AI generation (like land-pr).
    Raises an error if called, since these operations shouldn't use AI.
    """

    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Raise error since this should never be called."""
        raise RuntimeError(
            "AI generation was called on an operation that doesn't support it. "
            "This is a programming error."
        )


@dataclass
class ContextGtKit:
    """Adapter that makes ErkContext components satisfy GtKit Protocol.

    Combines ErkContext's git, github, graphite with an ClaudeCLIExecutor
    to create a composite that satisfies the GtKit Protocol.

    For operations that require AI (like submit-pr), pass a real ClaudeCLIExecutor.
    For operations that don't use AI (like land-pr), use NoOpClaudeCLIExecutor.
    """

    git: Git
    github: GitHub
    graphite: Graphite
    ai: ClaudeCLIExecutor
    time: Time

    @classmethod
    def from_context(cls, ctx: ErkContext, ai: ClaudeCLIExecutor | None = None) -> Self:
        """Create ContextGtKit from an ErkContext.

        Args:
            ctx: The ErkContext to adapt
            ai: Optional ClaudeCLIExecutor. If None, uses NoOpClaudeCLIExecutor.

        Returns:
            ContextGtKit that satisfies GtKit Protocol
        """
        return cls(
            git=ctx.git,
            github=ctx.github,
            graphite=ctx.graphite,
            ai=ai if ai is not None else NoOpClaudeCLIExecutor(),
            time=ctx.time,
        )
