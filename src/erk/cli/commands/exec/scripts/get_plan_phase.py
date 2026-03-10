"""Get the current phase of a plan (plan, impl, merged, closed, unknown).

Usage:
    erk exec get-plan-phase <plan-number>

Output:
    {"success": true, "plan_number": 42, "phase": "plan"}
    {"success": true, "plan_number": 42, "phase": "impl"}
    {"success": true, "plan_number": 42, "phase": "merged"}
    {"success": true, "plan_number": 42, "phase": "closed"}
    {"success": true, "plan_number": 42, "phase": "unknown"}

Exit Codes:
    0: Success (phase resolved or unknown)
    1: Plan not found
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root
from erk_shared.gateway.plan_data_provider.lifecycle import resolve_lifecycle_stage
from erk_shared.plan_store.types import PlanNotFound

_PLAN_STAGES = frozenset({"prompted", "planning", "planned"})
_IMPL_STAGES = frozenset({"impl", "implementing", "implemented"})


def _stage_to_phase(stage: str | None) -> str:
    """Map a lifecycle stage string to a coarse phase.

    Args:
        stage: Lifecycle stage from resolve_lifecycle_stage, or None.

    Returns:
        One of "plan", "impl", "merged", "closed", or "unknown".
    """
    if stage is None:
        return "unknown"
    if stage in _PLAN_STAGES:
        return "plan"
    if stage in _IMPL_STAGES:
        return "impl"
    if stage == "merged":
        return "merged"
    if stage == "closed":
        return "closed"
    return "unknown"


@dataclass(frozen=True)
class PhaseSuccess:
    """Success response for phase detection."""

    success: bool
    plan_number: int
    phase: str


@dataclass(frozen=True)
class PhaseError:
    """Error response for phase detection."""

    success: bool
    error: str
    message: str


@click.command(name="get-plan-phase")
@click.argument("plan_number", type=int)
@click.pass_context
def get_plan_phase(ctx: click.Context, plan_number: int) -> None:
    """Get the current phase of a plan.

    Fetches the plan and resolves its lifecycle stage to a coarse phase:
    plan, impl, merged, closed, or unknown.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    plan_id = str(plan_number)
    result = backend.get_plan(repo_root, plan_id)

    if isinstance(result, PlanNotFound):
        error_result = PhaseError(
            success=False,
            error="plan_not_found",
            message=f"Plan #{plan_number} not found",
        )
        click.echo(json.dumps(asdict(error_result)), err=True)
        raise SystemExit(1)

    stage = resolve_lifecycle_stage(result)
    phase = _stage_to_phase(stage)

    success_result = PhaseSuccess(
        success=True,
        plan_number=plan_number,
        phase=phase,
    )
    click.echo(json.dumps(asdict(success_result)))
