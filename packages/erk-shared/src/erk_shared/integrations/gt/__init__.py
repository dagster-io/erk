"""GT kit operations for git, Graphite (gt), and GitHub (gh)."""

from erk_shared.integrations.gt.abc import GitGtKit, GtKit
from erk_shared.integrations.gt.fake import (
    FakeGitGtKitOps,
    FakeGtKit,
    FakeGtKitOps,
    GitState,
)
from erk_shared.integrations.gt.real import (
    RealGitGtKit,
    RealGtKit,
)
from erk_shared.integrations.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "GitGtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
    "RealGitGtKit",
    # Fake implementations
    "FakeGtKit",
    "FakeGtKitOps",  # Backwards compatibility alias
    "FakeGitGtKitOps",
    # State types
    "GitState",
]
