"""Update a plan issue's plan-body comment with new content.

Usage:
    erk exec plan-update-from-feedback <plan-number> --plan-path PATH
    erk exec plan-update-from-feedback <plan-number> --plan-content "..."

Output:
    JSON with success status and plan number

Exit Codes:
    0: Success
    1: Error (plan not found, missing label, or update failed)
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class PlanUpdateFromFeedbackSuccess:
    """Success response for plan update from feedback."""

    success: bool
    plan_number: int


@dataclass(frozen=True)
class PlanUpdateFromFeedbackError:
    """Error response for plan update from feedback."""

    success: bool
    error: str
    message: str


class PlanUpdateFromFeedbackException(Exception):
    """Exception raised during plan update from feedback."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


def _update_plan_from_feedback_impl(
    backend: PlanBackend,
    *,
    repo_root: Path,
    plan_number: int,
    plan_content: str,
) -> PlanUpdateFromFeedbackSuccess:
    """Update the plan-body comment on a plan issue.

    Args:
        backend: PlanBackend for plan operations
        repo_root: Repository root path
        plan_number: Plan number to update
        plan_content: New plan markdown content

    Returns:
        PlanUpdateFromFeedbackSuccess on success

    Raises:
        PlanUpdateFromFeedbackException: If validation fails
    """
    plan_id = str(plan_number)

    # LBYL: Check if plan exists
    plan_result = backend.get_plan(repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        raise PlanUpdateFromFeedbackException(
            error="issue_not_found",
            message=f"Plan #{plan_number} not found",
        )

    # Validate erk-plan label
    if "erk-plan" not in plan_result.labels:
        raise PlanUpdateFromFeedbackException(
            error="missing_erk_plan_label",
            message=f"Plan #{plan_number} does not have the erk-plan label",
        )

    # Update plan content via PlanBackend
    try:
        backend.update_plan_content(repo_root, plan_id, plan_content)
    except RuntimeError as e:
        raise PlanUpdateFromFeedbackException(
            error="update_failed",
            message=f"Failed to update plan content: {e}",
        ) from e

    return PlanUpdateFromFeedbackSuccess(
        success=True,
        plan_number=plan_number,
    )


@click.command(name="plan-update-from-feedback")
@click.argument("plan_number", type=int)
@click.option("--plan-path", type=click.Path(exists=True), help="Path to plan markdown file")
@click.option("--plan-content", type=str, help="Plan content as string")
@click.pass_context
def plan_update_from_feedback(
    ctx: click.Context,
    plan_number: int,
    plan_path: str | None,
    plan_content: str | None,
) -> None:
    """Update a plan issue's plan-body comment with new content.

    Requires exactly one of --plan-path or --plan-content.
    """
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    # Validate mutually exclusive options
    if plan_path is not None and plan_content is not None:
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error="invalid_input",
            message="Cannot specify both --plan-path and --plan-content",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    if plan_path is None and plan_content is None:
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error="invalid_input",
            message="Must specify either --plan-path or --plan-content",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    # Read content from file or use provided string
    # Both-None and both-set cases already handled above with early return
    if plan_path is not None:
        content = Path(plan_path).read_text(encoding="utf-8")
    elif plan_content is not None:
        content = plan_content
    else:
        # Unreachable: guarded by validation above, but satisfies type checker
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error="invalid_input",
            message="Must specify either --plan-path or --plan-content",
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1)

    try:
        result = _update_plan_from_feedback_impl(
            backend,
            repo_root=repo_root,
            plan_number=plan_number,
            plan_content=content,
        )
        click.echo(json.dumps(asdict(result)))
    except PlanUpdateFromFeedbackException as e:
        error_response = PlanUpdateFromFeedbackError(
            success=False,
            error=e.error,
            message=e.message,
        )
        click.echo(json.dumps(asdict(error_response)))
        raise SystemExit(1) from None
