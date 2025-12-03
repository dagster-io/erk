"""Command to validate plan format against Schema v2 requirements."""

import click
from erk_shared.github.metadata import (
    PlanHeaderSchema,
    extract_plan_from_comment,
    find_metadata_block,
)
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.cli.github_parsing import parse_issue_identifier
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


@click.command("check")
@click.argument("identifier", type=str)
@click.pass_obj
def check_plan(ctx: ErkContext, identifier: str) -> None:
    """Validate a plan's format against Schema v2 requirements.

    Validates that a plan stored in a GitHub issue conforms to Schema v2:
    - Issue body has plan-header metadata block with required fields
    - First comment has plan-body metadata block with extractable content

    Args:
        identifier: Plan identifier (e.g., "42" or GitHub URL)
    """
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)  # Ensure erk metadata directories exist
    repo_root = repo.root  # Use git repository root for GitHub operations

    # Parse identifier - raises click.ClickException if invalid
    issue_number = parse_issue_identifier(identifier)

    user_output(f"Validating plan #{issue_number}...")
    user_output("")

    # Track validation results
    checks: list[tuple[bool, str]] = []

    # Fetch issue from GitHub
    try:
        issue = ctx.issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to fetch issue: {e}")
        raise SystemExit(1) from e

    issue_body = issue.body if issue.body else ""

    # Check 1: plan-header metadata block exists
    plan_header_block = find_metadata_block(issue_body, "plan-header")
    if plan_header_block is None:
        checks.append((False, "plan-header metadata block present"))
    else:
        checks.append((True, "plan-header metadata block present"))

        # Check 2: plan-header has required fields and is valid
        try:
            schema = PlanHeaderSchema()
            schema.validate(plan_header_block.data)
            checks.append((True, "plan-header has required fields"))
        except ValueError as e:
            # Extract first error message for cleaner output
            error_msg = str(e).split("\n")[0]
            checks.append((False, f"plan-header validation failed: {error_msg}"))

    # Check 3: First comment exists
    try:
        comments = ctx.issues.get_issue_comments(repo_root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + f"Failed to fetch comments: {e}")
        raise SystemExit(1) from e

    if not comments:
        checks.append((False, "First comment exists"))
    else:
        checks.append((True, "First comment exists"))

        # Check 4: plan-body content extractable
        first_comment = comments[0]
        plan_content = extract_plan_from_comment(first_comment)
        if plan_content is None:
            checks.append((False, "plan-body content extractable"))
        else:
            checks.append((True, "plan-body content extractable"))

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
