"""Command to validate plan accessibility and content.

Validates that a plan can be retrieved and has content.
This is a provider-agnostic validation - the underlying PlanStore
handles storage-format validation (e.g., Schema v2 for GitHub).
"""

from urllib.parse import urlparse

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


def _parse_identifier(identifier: str) -> str:
    """Parse plan identifier from number string or GitHub URL.

    Args:
        identifier: Plan identifier string (e.g., "42") or GitHub URL

    Returns:
        Plan identifier as string

    Raises:
        ValueError: If identifier is invalid
    """
    if identifier.isdigit():
        return identifier

    # Security: Use proper URL parsing to validate hostname
    parsed = urlparse(identifier)
    if parsed.hostname == "github.com" and parsed.path:
        parts = parsed.path.rstrip("/").split("/")
        if len(parts) >= 2 and parts[-2] == "issues":
            if parts[-1].isdigit():
                return parts[-1]

    raise ValueError(f"Invalid identifier: {identifier}")


@click.command("check")
@click.argument("identifier", type=str)
@click.pass_obj
def check_plan(ctx: ErkContext, identifier: str) -> None:
    """Validate that a plan exists and has content.

    Validates:
    - Plan can be retrieved from the store
    - Plan has the erk-plan label
    - Plan body has content

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for operations

    # Parse identifier
    try:
        plan_identifier = _parse_identifier(identifier)
    except ValueError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from e

    user_output(f"Validating plan #{plan_identifier}...")
    user_output("")

    # Track validation results
    checks: list[tuple[bool, str]] = []

    # Fetch plan from store
    try:
        plan = ctx.plan_store.get_plan(repo_root, plan_identifier)
        checks.append((True, "Plan can be retrieved"))
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to fetch plan: {e}")
        raise SystemExit(1) from e

    # Check: has erk-plan label
    has_erk_plan_label = "erk-plan" in plan.labels
    if has_erk_plan_label:
        checks.append((True, "Plan has erk-plan label"))
    else:
        checks.append((False, "Plan has erk-plan label"))

    # Check: has content
    has_content = bool(plan.body.strip())
    if has_content:
        checks.append((True, "Plan has content"))
    else:
        checks.append((False, "Plan has content"))

    # Output results
    for passed, description in checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    # Determine overall result
    failed_count = sum(1 for passed, _ in checks if not passed)
    if failed_count == 0:
        user_output(click.style("Plan validation passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "checks" if failed_count > 1 else "check"
        user_output(
            click.style(f"Plan validation failed ({failed_count} {check_word} failed)", fg="red")
        )
        raise SystemExit(1)
