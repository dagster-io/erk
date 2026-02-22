"""Update plan-header metadata fields generically.

Usage:
    erk exec update-plan-header <plan_id> key1=value1 key2=value2 ...

Output:
    JSON with success status, plan_id, and fields_updated

Exit Codes:
    0: Success
    1: Error (plan not found, no fields provided, invalid field format,
       schema validation failure, no plan-header block)
"""

import json
from dataclasses import asdict, dataclass

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root
from erk_shared.plan_store.types import PlanHeaderNotFoundError


@dataclass(frozen=True)
class UpdateSuccess:
    """Success response for plan-header update."""

    success: bool
    plan_id: str
    fields_updated: list[str]


@dataclass(frozen=True)
class UpdateError:
    """Error response for plan-header update."""

    success: bool
    error: str
    message: str


def _coerce_value(raw: str) -> object:
    """Coerce a string value to the appropriate Python type.

    Rules:
        "null" -> None
        Valid int string -> int
        Everything else -> str
    """
    if raw == "null":
        return None
    # Check if valid integer (handles negative numbers too)
    if raw.lstrip("-").isdigit() and raw != "-":
        return int(raw)
    return raw


def _parse_fields(fields: tuple[str, ...]) -> dict[str, object]:
    """Parse key=value field pairs into a dictionary.

    Raises:
        ValueError: If any field lacks an '=' separator.
    """
    parsed: dict[str, object] = {}
    for field in fields:
        if "=" not in field:
            msg = f"Invalid field format: '{field}'. Expected key=value."
            raise ValueError(msg)
        key, raw_value = field.split("=", 1)
        parsed[key] = _coerce_value(raw_value)
    return parsed


@click.command(name="update-plan-header")
@click.argument("plan_id", type=str)
@click.argument("fields", nargs=-1)
@click.pass_context
def update_plan_header(
    ctx: click.Context,
    *,
    plan_id: str,
    fields: tuple[str, ...],
) -> None:
    """Update plan-header metadata fields on a plan.

    Generic command to set arbitrary plan-header metadata fields.
    Backend handles merge with existing data, immutable field protection,
    and full PlanHeaderSchema validation.
    """
    # LBYL: reject if zero fields provided
    if not fields:
        error = UpdateError(
            success=False,
            error="no_fields",
            message="No fields provided. Usage: update-plan-header <plan_id> key=value ...",
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1)

    # Parse key=value pairs
    try:
        parsed = _parse_fields(fields)
    except ValueError as e:
        error = UpdateError(
            success=False,
            error="invalid_field_format",
            message=str(e),
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1) from None

    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    try:
        backend.update_metadata(repo_root, plan_id, metadata=parsed)
    except PlanHeaderNotFoundError:
        error = UpdateError(
            success=False,
            error="no_plan_header",
            message=f"Plan {plan_id} has no plan-header metadata block.",
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1) from None
    except RuntimeError as e:
        error = UpdateError(
            success=False,
            error="update_failed",
            message=f"Failed to update plan header: {e}",
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1) from None
    except ValueError as e:
        error = UpdateError(
            success=False,
            error="schema_validation_failed",
            message=f"Schema validation failed: {e}",
        )
        click.echo(json.dumps(asdict(error)), err=True)
        raise SystemExit(1) from None

    result = UpdateSuccess(
        success=True,
        plan_id=plan_id,
        fields_updated=list(parsed.keys()),
    )
    click.echo(json.dumps(asdict(result)))
