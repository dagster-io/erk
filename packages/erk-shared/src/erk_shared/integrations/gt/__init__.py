"""GT kit operations for Graphite (gt) and GitHub (gh)."""

from erk_shared.integrations.gt.abc import GitHubGtKit, GtKit
from erk_shared.integrations.gt.fake import (
    FakeGitHubGtKitOps,
    GitHubState,
)
from erk_shared.integrations.gt.real import (
    RealGitHubGtKit,
    RealGtKit,
)
from erk_shared.integrations.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "GitHubGtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
    "RealGitHubGtKit",
    # Fake implementations
    "FakeGitHubGtKitOps",
    # State types
    "GitHubState",
]
