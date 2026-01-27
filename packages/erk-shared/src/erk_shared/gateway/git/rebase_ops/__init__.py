"""Git rebase operations subgateway."""

from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.dry_run import DryRunGitRebaseOps
from erk_shared.gateway.git.rebase_ops.fake import FakeGitRebaseOps
from erk_shared.gateway.git.rebase_ops.printing import PrintingGitRebaseOps
from erk_shared.gateway.git.rebase_ops.real import RealGitRebaseOps

__all__ = [
    "GitRebaseOps",
    "RealGitRebaseOps",
    "FakeGitRebaseOps",
    "DryRunGitRebaseOps",
    "PrintingGitRebaseOps",
]
