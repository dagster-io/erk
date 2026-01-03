"""StatuslineContext - dependency injection container for statusline operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.factory import create_branch_manager
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

    Provides access to Git, Graphite, GitHub, and BranchManager gateways
    for testability. All external dependencies are accessed through this context.
    """

    cwd: Path
    git: Git
    graphite: Graphite
    github: GitHub
    branch_manager: BranchManager


def create_context(cwd: str) -> StatuslineContext:
    """Create a StatuslineContext with real gateway implementations.

    Args:
        cwd: Current working directory as string

    Returns:
        StatuslineContext configured with real gateways
    """
    git = RealGit()
    graphite = RealGraphite()
    github = RealGitHub(RealTime())
    branch_manager = create_branch_manager(git, github, graphite)
    return StatuslineContext(
        cwd=Path(cwd),
        git=git,
        graphite=graphite,
        github=github,
        branch_manager=branch_manager,
    )
