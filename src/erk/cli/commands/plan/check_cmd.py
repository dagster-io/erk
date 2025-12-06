"""Command to validate plan format against Schema v2 requirements."""

from dataclasses import dataclass
from pathlib import Path

import click
from erk_shared.github.issues.abc import GitHubIssues
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


@dataclass(frozen=True)
class PlanValidationSuccess:
    """Validation completed (may have passed or failed checks).

    Attributes:
        passed: True if all validation checks passed
        checks: List of (passed, description) tuples for each check
        failed_count: Number of failed checks
    """

    passed: bool
    checks: list[tuple[bool, str]]
    failed_count: int


@dataclass(frozen=True)
class PlanValidationError:
    """Could not complete validation (API error, network issue, etc.)."""

    error: str


PlanValidationResult = PlanValidationSuccess | PlanValidationError


def validate_plan_format(
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
) -> PlanValidationResult:
    """Validate plan format programmatically.

    Validates that a plan stored in a GitHub issue conforms to Schema v2:
    - Issue body has plan-header metadata block with required fields
    - First comment has plan-body metadata block with extractable content

    This function is designed to be called programmatically (e.g., from land_cmd).
    It does not produce output or raise SystemExit. It never raises exceptions -
    API failures are returned as PlanValidationError.

    Args:
        github_issues: GitHub issues interface
        repo_root: Repository root path
        issue_number: GitHub issue number to validate

    Returns:
        PlanValidationSuccess if validation completed (may have passed or failed checks)
        PlanValidationError if unable to complete validation (API error, etc.)
    """
    # Track validation results
    checks: list[tuple[bool, str]] = []

    # Fetch issue from GitHub
    try:
        issue = github_issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        return PlanValidationError(error=str(e))

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
        comments = github_issues.get_issue_comments(repo_root, issue_number)
    except RuntimeError as e:
        return PlanValidationError(error=str(e))

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

    # Determine overall result
    failed_count = sum(1 for passed, _ in checks if not passed)

    return PlanValidationSuccess(
        passed=failed_count == 0,
        checks=checks,
        failed_count=failed_count,
    )


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

    # Run validation
    result = validate_plan_format(ctx.issues, repo_root, issue_number)

    if isinstance(result, PlanValidationError):
        user_output(click.style("Error: ", fg="red") + f"Failed to validate plan: {result.error}")
        raise SystemExit(1)

    # result is now PlanValidationSuccess
    # Output results
    for passed, description in result.checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    # Determine overall result
    if result.passed:
        user_output(click.style("Plan validation passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "checks" if result.failed_count > 1 else "check"
        user_output(
            click.style(
                f"Plan validation failed ({result.failed_count} {check_word} failed)", fg="red"
            )
        )
        raise SystemExit(1)
