"""GT kit operations for Graphite (gt) and GitHub (gh)."""

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.real import (
    RealGtKit,
)
from erk_shared.integrations.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
]
