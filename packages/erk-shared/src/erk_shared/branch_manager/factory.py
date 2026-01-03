"""Factory function for creating BranchManager instances."""

from __future__ import annotations

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.git import GitBranchManager
from erk_shared.branch_manager.graphite import GraphiteBranchManager
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.disabled import GraphiteDisabled
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub


def create_branch_manager(
    git: Git,
    github: GitHub,
    graphite: Graphite,
) -> BranchManager:
    """Create appropriate BranchManager based on Graphite availability.

    Args:
        git: Git gateway for branch operations
        github: GitHub gateway for PR lookups (used when Graphite disabled)
        graphite: Graphite gateway (may be GraphiteDisabled sentinel)

    Returns:
        GraphiteBranchManager if Graphite is available,
        GitBranchManager otherwise.
    """
    if isinstance(graphite, GraphiteDisabled):
        return GitBranchManager(git=git, github=github)
    return GraphiteBranchManager(git=git, graphite=graphite)
