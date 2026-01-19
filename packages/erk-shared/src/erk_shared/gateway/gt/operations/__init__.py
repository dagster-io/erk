"""GT kit operations - pure business logic without CLI dependencies.

This module contains the business logic for GT kit operations. Each operation:
- Takes explicit dependencies (GtKit, cwd) instead of using global state
- Yields ProgressEvent for progress updates instead of click.echo
- Yields CompletionEvent with the final result

CLI layers consume these generators and handle rendering.

Import from submodules:
- erk_shared.gateway.gt.operations.finalize: execute_finalize
- erk_shared.gateway.gt.operations.land_pr: execute_land_pr
- erk_shared.gateway.gt.operations.pre_analysis: execute_pre_analysis
- erk_shared.gateway.gt.operations.preflight: execute_preflight
- erk_shared.gateway.gt.operations.squash: execute_squash
"""
