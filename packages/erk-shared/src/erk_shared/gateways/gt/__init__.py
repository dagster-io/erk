"""GT kit operations for Graphite (gt) and GitHub (gh)."""

from erk_shared.gateways.gt.abc import GtKit
from erk_shared.gateways.gt.real import (
    RealGtKit,
)
from erk_shared.gateways.gt.types import CommandResult

__all__ = [
    # ABC interfaces
    "GtKit",
    "CommandResult",
    # Real implementations
    "RealGtKit",
]
