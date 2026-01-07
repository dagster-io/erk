"""StatuslineContext - dependency injection container for statusline operations."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.factory import create_branch_manager
from erk_shared.gateway.erk_installation.abc import ErkInstallation
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
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


def resolve_graphite(
    installation: ErkInstallation,
    *,
    gt_installed: bool | None = None,
) -> Graphite:
    """Resolve Graphite implementation based on config and availability.

    This helper is extracted for testability. It mirrors the logic in
    src/erk/core/context.py.

    Args:
        installation: ErkInstallation to read config from
        gt_installed: Override for shutil.which("gt") check. If None, performs
            real check. Pass True/False in tests to control behavior.

    Returns:
        Appropriate Graphite implementation
    """
    if not installation.config_exists():
        # No config exists yet - default to disabled
        return GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

    config = installation.load_config()
    if not config.use_graphite:
        # Graphite disabled by config
        return GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)

    # Config says use Graphite - check if gt is installed
    is_installed = gt_installed if gt_installed is not None else (shutil.which("gt") is not None)
    if not is_installed:
        return GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)

    return RealGraphite()


def create_context(cwd: str) -> StatuslineContext:
    """Create a StatuslineContext with real gateway implementations.

    Args:
        cwd: Current working directory as string

    Returns:
        StatuslineContext configured with real gateways
    """
    git = RealGit()
    github = RealGitHub(RealTime())
    graphite = resolve_graphite(RealErkInstallation())

    branch_manager = create_branch_manager(git=git, github=github, graphite=graphite)
    return StatuslineContext(
        cwd=Path(cwd),
        git=git,
        graphite=graphite,
        github=github,
        branch_manager=branch_manager,
    )
