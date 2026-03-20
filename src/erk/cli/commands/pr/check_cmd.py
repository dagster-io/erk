"""Command to validate PR rules or plan format for the current branch."""

from dataclasses import dataclass
from typing import NamedTuple

import click

from erk.cli.ensure import Ensure
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.repo_resolution import (
    get_remote_github,
    repo_option,
    resolve_owner_repo,
)
from erk.core.context import ErkContext
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.github.metadata.core import find_metadata_block
from erk_shared.gateway.github.metadata.plan_header import extract_plan_from_comment
from erk_shared.gateway.github.metadata.schemas import PlanHeaderSchema
from erk_shared.gateway.github.metadata.types import BlockKeys
from erk_shared.gateway.github.pr_footer import (
    extract_header_from_body,
    is_header_at_legacy_position,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.pr.submit import has_checkout_footer_for_pr
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir
from erk_shared.output.output import user_output
from erk_shared.plan_store.planned_pr_lifecycle import (
    extract_plan_content,
    has_original_plan_section,
)


class PrCheck(NamedTuple):
    passed: bool
    description: str


# --- Plan validation types and function ---


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
    remote: RemoteGitHub,
    *,
    owner: str,
    repo: str,
    pr_number: int,
) -> PlanValidationResult:
    """Validate plan format programmatically.

    Validates that a plan stored in a GitHub issue conforms to Schema v2:
    - Issue body has plan-header metadata block with required fields
    - First comment has plan-body metadata block with extractable content

    This function is designed to be called programmatically (e.g., from land_cmd).
    It does not produce output or raise SystemExit. It never raises exceptions -
    API failures are returned as PlanValidationError.

    Args:
        remote: RemoteGitHub instance
        owner: Repository owner
        repo: Repository name
        pr_number: GitHub issue number to validate

    Returns:
        PlanValidationSuccess if validation completed (may have passed or failed checks)
        PlanValidationError if unable to complete validation (API error, etc.)
    """
    checks: list[tuple[bool, str]] = []

    issue = remote.get_issue(owner=owner, repo=repo, number=pr_number)
    if isinstance(issue, IssueNotFound):
        return PlanValidationError(error=f"PR #{pr_number} not found")

    issue_body = issue.body if issue.body else ""

    # Check 1: plan-header metadata block exists
    plan_header_block = find_metadata_block(issue_body, BlockKeys.PLAN_HEADER)
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
            error_msg = str(e).split("\n")[0]
            checks.append((False, f"plan-header validation failed: {error_msg}"))

    # Detect format: draft-PR (body has original-plan section)
    if has_original_plan_section(issue_body):
        plan_content = extract_plan_content(issue_body)
        if plan_content:
            checks.append((True, "plan content extractable from body"))
        else:
            checks.append((False, "plan content extractable from body"))
    else:
        # Issue-based format: plan content is in first comment
        comments = remote.get_issue_comments(owner=owner, repo=repo, number=pr_number)

        if not comments:
            checks.append((False, "First comment exists"))
        else:
            checks.append((True, "First comment exists"))

            first_comment = comments[0]
            plan_content = extract_plan_from_comment(first_comment)
            if plan_content is None:
                checks.append((False, "plan-body content extractable"))
            else:
                checks.append((True, "plan-body content extractable"))

    failed_count = sum(1 for passed, _ in checks if not passed)

    return PlanValidationSuccess(
        passed=failed_count == 0,
        checks=checks,
        failed_count=failed_count,
    )


# --- CLI command ---


@click.command("check")
@click.argument("identifier", required=False, default=None)
@click.option(
    "--stage",
    type=click.Choice(["impl"]),
    default=None,
    help="Run stage-specific checks. Use 'impl' to also verify .erk/impl-context/ was cleaned up.",
)
@repo_option
@click.pass_obj
def pr_check(
    ctx: ErkContext,
    identifier: str | None,
    stage: str | None,
    *,
    target_repo: str | None,
) -> None:
    """Validate PR rules or plan format.

    \b
    Without arguments: validates the current branch's PR body.
    With an identifier: validates a plan's format against Schema v2.

    \b
    PR validation checks:
    1. Branch/plan-ref agreement
    2. Checkout footer present
    3. Plan-header metadata at correct position

    \b
    Plan validation (with identifier):
    - Issue body has plan-header metadata block with required fields
    - First comment has plan-body metadata block with extractable content

    \b
    Examples:
        erk pr check              # Validate current branch's PR
        erk pr check P123         # Validate plan #123 format
        erk pr check 456          # Validate plan #456 format
        erk pr check --stage impl # PR check + impl-context cleanup
        erk pr check 456 --repo owner/repo  # Remote plan validation
    """
    if identifier is not None:
        _check_plan_format(ctx, identifier, target_repo=target_repo)
    else:
        if target_repo is not None or isinstance(ctx.repo, NoRepoSentinel):
            user_output(
                click.style("Error: ", fg="red")
                + "PR body validation requires a local git repository.\n"
                "Provide a plan identifier for remote validation:\n"
                "  erk pr check <number> --repo owner/repo"
            )
            raise SystemExit(1)
        _check_pr_body(ctx, stage)


def _check_plan_format(
    ctx: ErkContext,
    identifier: str,
    *,
    target_repo: str | None,
) -> None:
    """Validate a plan's format against Schema v2 requirements."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=target_repo)
    remote = get_remote_github(ctx)

    pr_number = parse_issue_identifier(identifier)

    user_output(f"Validating PR #{pr_number}...")
    user_output("")

    result = validate_plan_format(remote, owner=owner, repo=repo_name, pr_number=pr_number)

    if isinstance(result, PlanValidationError):
        user_output(click.style("Error: ", fg="red") + f"Failed to validate PR: {result.error}")
        raise SystemExit(1)

    for passed, description in result.checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    if result.passed:
        user_output(click.style("PR validation passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "checks" if result.failed_count > 1 else "check"
        user_output(
            click.style(
                f"PR validation failed ({result.failed_count} {check_word} failed)", fg="red"
            )
        )
        raise SystemExit(1)


def _check_pr_body(ctx: ErkContext, stage: str | None) -> None:
    """Validate PR rules for the current branch."""
    # Get current branch
    branch = Ensure.not_none(
        ctx.git.branch.get_current_branch(ctx.cwd),
        "Not on a branch (detached HEAD)",
    )

    # Get repo root for GitHub operations
    repo_root = ctx.git.repo.get_repository_root(ctx.cwd)

    # Get PR for branch
    pr = ctx.github.get_pr_for_branch(repo_root, branch)
    if isinstance(pr, PRNotFound):
        user_output(
            click.style("Error: ", fg="red") + f"No pull request found for branch '{branch}'"
        )
        raise SystemExit(1)

    pr_number = pr.number

    user_output(f"Checking PR #{pr_number} for branch {branch}...")
    user_output("")

    # Track validation results
    checks: list[PrCheck] = []

    pr_body = pr.body

    # Resolve impl dir using branch-scoped discovery
    impl_dir = resolve_impl_dir(repo_root, branch_name=branch)

    # Stage-specific check: .erk/impl-context/ must not be present
    if stage == "impl":
        impl_context_dir = repo_root / ".erk" / "impl-context"
        if impl_context_dir.exists():
            checks.append(
                PrCheck(
                    passed=False,
                    description=(
                        ".erk/impl-context/ still present (should be removed before submission)"
                    ),
                )
            )
        else:
            checks.append(
                PrCheck(passed=True, description=".erk/impl-context/ not present (cleaned up)")
            )

    # Check 0: Plan reference exists
    expected_pr_number: int | None = None
    plan_ref = read_plan_ref(impl_dir) if impl_dir is not None else None

    if plan_ref is not None:
        expected_pr_number = int(plan_ref.pr_id)
        checks.append(
            PrCheck(
                passed=True,
                description=f"Plan reference found (#{expected_pr_number})",
            )
        )

    # Check 1: Checkout footer
    if has_checkout_footer_for_pr(pr_body, pr_number):
        checks.append(PrCheck(passed=True, description="PR body contains checkout footer"))
    else:
        checks.append(PrCheck(passed=False, description="PR body missing checkout footer"))

    # Check 2: Header position (not at legacy top position)
    header = extract_header_from_body(pr_body)
    if header:
        if is_header_at_legacy_position(pr_body):
            checks.append(
                PrCheck(
                    passed=False,
                    description=(
                        "Plan-header metadata is at legacy top position (should be above footer)"
                    ),
                )
            )
        else:
            checks.append(
                PrCheck(passed=True, description="Plan-header metadata is at correct position")
            )

    # Output results
    for check in checks:
        status = (
            click.style("[PASS]", fg="green") if check.passed else click.style("[FAIL]", fg="red")
        )
        user_output(f"{status} {check.description}")

    user_output("")

    # Determine overall result
    failed_count = sum(1 for c in checks if not c.passed)
    if failed_count == 0:
        user_output(click.style("All checks passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "check" if failed_count == 1 else "checks"
        user_output(click.style(f"{failed_count} {check_word} failed", fg="red"))
        raise SystemExit(1)
