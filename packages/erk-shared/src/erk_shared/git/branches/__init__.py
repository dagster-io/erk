"""Git branch operations integration."""

from erk_shared.git.branches.abc import GitBranches
from erk_shared.git.branches.dry_run import DryRunGitBranches
from erk_shared.git.branches.fake import FakeGitBranches
from erk_shared.git.branches.printing import PrintingGitBranches
from erk_shared.git.branches.real import RealGitBranches

__all__ = [
    "GitBranches",
    "DryRunGitBranches",
    "FakeGitBranches",
    "PrintingGitBranches",
    "RealGitBranches",
]
