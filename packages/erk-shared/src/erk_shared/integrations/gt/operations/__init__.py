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
from erk_shared.integrations.gt.operations.prep import execute_prep
from erk_shared.integrations.gt.operations.squash import execute_squash
from erk_shared.integrations.gt.operations.update_pr import execute_update_pr

__all__ = [
    "execute_finalize",
    "execute_land_pr",
    "execute_pre_analysis",
    "execute_preflight",
    "execute_prep",
    "execute_squash",
    "execute_update_pr",
]
