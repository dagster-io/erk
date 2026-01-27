"""Git status operations subgateway."""

from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.dry_run import DryRunGitStatusOps
from erk_shared.gateway.git.status_ops.fake import FakeGitStatusOps
from erk_shared.gateway.git.status_ops.printing import PrintingGitStatusOps
from erk_shared.gateway.git.status_ops.real import RealGitStatusOps

__all__ = [
    "GitStatusOps",
    "RealGitStatusOps",
    "FakeGitStatusOps",
    "DryRunGitStatusOps",
    "PrintingGitStatusOps",
]
