"""GT kit operations - pure business logic without CLI dependencies.

This module contains the business logic for GT kit operations. Each operation:
- Takes explicit dependencies (GtKit, cwd) instead of using global state
- Yields ProgressEvent for progress updates instead of click.echo
- Yields CompletionEvent with the final result

CLI layers consume these generators and handle rendering.
"""

from erk_shared.gateway.gt.operations.finalize import execute_finalize
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.operations.pre_analysis import execute_pre_analysis
from erk_shared.gateway.gt.operations.preflight import execute_preflight
from erk_shared.gateway.gt.operations.squash import execute_squash

__all__ = [
    "execute_finalize",
    "execute_land_pr",
    "execute_pre_analysis",
    "execute_preflight",
    "execute_squash",
]
