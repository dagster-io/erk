"""Git remote operations integration."""

from erk_shared.git.remotes.abc import GitRemotes
from erk_shared.git.remotes.dry_run import DryRunGitRemotes
from erk_shared.git.remotes.fake import FakeGitRemotes
from erk_shared.git.remotes.printing import PrintingGitRemotes
from erk_shared.git.remotes.real import RealGitRemotes

__all__ = [
    "GitRemotes",
    "DryRunGitRemotes",
    "FakeGitRemotes",
    "PrintingGitRemotes",
    "RealGitRemotes",
]
