"""Update the lifecycle_stage metadata field on a plan.

Usage:
    erk exec update-lifecycle-stage --plan-id 123 --stage implementing

Output:
    JSON with success status

Exit Codes:
    0: Success
    1: Error (plan not found, invalid stage)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root
from erk_shared.gateway.github.metadata.schemas import LifecycleStageValue
from erk_shared.plan_store.types import PlanNotFound

# Valid lifecycle stage values (must match LifecycleStageValue type)
_VALID_STAGES: tuple[str, ...] = (
    "prompted",
    "planning",
    "planned",
    "implementing",
    "implemented",
)


@dataclass(frozen=True)
class UpdateLifecycleSuccess:
    """Success response for lifecycle stage update."""

    success: bool
    plan_id: str
    stage: str


@dataclass(frozen=True)
class UpdateLifecycleError:
    """Error response for lifecycle stage update."""

    success: bool
    error: str
    message: str


@click.command(name="update-lifecycle-stage")
@click.option("--plan-id", required=True, help="Plan identifier (issue number or PR number)")
@click.option(
    "--stage",
    required=True,
    type=click.Choice(_VALID_STAGES),
    help="Lifecycle stage to set",
)
@click.pass_context
def update_lifecycle_stage(
    ctx: click.Context,
    *,
    plan_id: str,
    stage: str,
) -> None:
    """Update the lifecycle_stage metadata field on a plan.

    Sets the lifecycle_stage field in the plan-header metadata block
    to the specified value.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    # Verify plan exists before updating
    plan_result = backend.get_plan(repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        error_result = UpdateLifecycleError(
            success=False,
            error="plan_not_found",
            message=f"Plan {plan_id} not found",
        )
        click.echo(json.dumps(asdict(error_result)), err=True)
        raise SystemExit(1)

    # Update lifecycle stage
    try:
        # Cast is safe because Click validates against _VALID_STAGES
        _stage: LifecycleStageValue = stage  # type: ignore[assignment]
        backend.update_metadata(
            repo_root,
            plan_id,
            metadata={"lifecycle_stage": _stage},
        )
    except RuntimeError as e:
        error_result = UpdateLifecycleError(
            success=False,
            error="update_failed",
            message=f"Failed to update lifecycle stage: {e}",
        )
        click.echo(json.dumps(asdict(error_result)), err=True)
        raise SystemExit(1) from None

    result = UpdateLifecycleSuccess(
        success=True,
        plan_id=plan_id,
        stage=stage,
    )
    click.echo(json.dumps(asdict(result)))
