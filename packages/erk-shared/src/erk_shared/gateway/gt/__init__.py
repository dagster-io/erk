"""GT kit operations for Graphite (gt) and GitHub (gh)."""

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.real import (
    RealGtKit,
)
from erk_shared.gateway.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
]
