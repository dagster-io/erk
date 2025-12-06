"""GT kit operations - pure business logic without CLI dependencies.

This module contains the business logic for GT kit operations. Each operation:
- Takes explicit dependencies (GtKit, cwd) instead of using global state
- Yields ProgressEvent for progress updates instead of click.echo
- Yields CompletionEvent with the final result

CLI layers consume these generators and handle rendering.
"""

from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.operations.pre_analysis import execute_pre_analysis
from erk_shared.integrations.gt.operations.preflight import execute_preflight
from erk_shared.integrations.gt.operations.restack_continue import execute_restack_continue
from erk_shared.integrations.gt.operations.restack_finalize import execute_restack_finalize
from erk_shared.integrations.gt.operations.restack_preflight import execute_restack_preflight
from erk_shared.integrations.gt.operations.squash import execute_squash

__all__ = [
    "execute_finalize",
    "execute_land_pr",
    "execute_pre_analysis",
    "execute_preflight",
    "execute_restack_continue",
    "execute_restack_finalize",
    "execute_restack_preflight",
    "execute_squash",
]
