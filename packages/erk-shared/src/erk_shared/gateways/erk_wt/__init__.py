"""Erk worktree operations for create_wt_from_issue command."""

from erk_shared.gateways.erk_wt.abc import (
    ErkWtKit,
    IssueData,
    IssueParseResult,
    WorktreeCreationResult,
)
from erk_shared.gateways.erk_wt.fake import FakeErkWtKit
from erk_shared.gateways.erk_wt.real import RealErkWtKit

__all__ = [
    # ABC interface
    "ErkWtKit",
    # Data types
    "IssueData",
    "IssueParseResult",
    "WorktreeCreationResult",
    # Real implementation
    "RealErkWtKit",
    # Fake implementation
    "FakeErkWtKit",
]
