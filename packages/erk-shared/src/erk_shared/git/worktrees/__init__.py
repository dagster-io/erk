"""Git worktree operations integration."""

from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.git.worktrees.dry_run import DryRunGitWorktrees
from erk_shared.git.worktrees.fake import FakeGitWorktrees
from erk_shared.git.worktrees.printing import PrintingGitWorktrees
from erk_shared.git.worktrees.real import RealGitWorktrees

__all__ = [
    "GitWorktrees",
    "DryRunGitWorktrees",
    "FakeGitWorktrees",
    "PrintingGitWorktrees",
    "RealGitWorktrees",
]
