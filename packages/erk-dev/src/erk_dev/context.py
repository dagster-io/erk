"""Context for erk-dev CLI commands.

Provides dependency injection for gateways (Git, etc.) to enable testing
with fakes instead of mocks.
"""

from dataclasses import dataclass

from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.dry_run import DryRunGit
from erk_shared.gateway.git.real import RealGit


@dataclass(frozen=True)
class ErkDevContext:
    """Context object for erk-dev commands.

    Contains gateways that can be injected for testing.
    """

    git: Git


def create_context(*, dry_run: bool = False) -> ErkDevContext:
    """Create a context with real or dry-run implementations.

    Args:
        dry_run: If True, wrap Git in DryRunGit to prevent mutations.

    Returns:
        ErkDevContext with appropriate gateway implementations.
    """
    git: Git = RealGit()
    if dry_run:
        git = DryRunGit(git)
    return ErkDevContext(git=git)
