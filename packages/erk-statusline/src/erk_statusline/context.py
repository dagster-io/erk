"""StatuslineContext - dependency injection container for statusline operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.real import RealGraphite
from erk_shared.gateway.time.real import RealTime
from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub


@dataclass(frozen=True)
class StatuslineContext:
    """Context container for statusline operations.

    Provides access to Git, Graphite, and GitHub gateways for testability.
    All external dependencies are accessed through this context.
    """

    cwd: Path
    git: Git
    graphite: Graphite
    github: GitHub


def create_context(cwd: str) -> StatuslineContext:
    """Create a StatuslineContext with real gateway implementations.

    Args:
        cwd: Current working directory as string

    Returns:
        StatuslineContext configured with real gateways
    """
    return StatuslineContext(
        cwd=Path(cwd),
        git=RealGit(),
        graphite=RealGraphite(),
        github=RealGitHub(RealTime()),
    )
