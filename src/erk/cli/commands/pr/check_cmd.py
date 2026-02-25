"""Command to validate PR rules for the current branch."""

from typing import NamedTuple

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.gateway.github.pr_footer import (
    extract_header_from_body,
    is_header_at_legacy_position,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.pr.submit import (
    has_checkout_footer_for_pr,
    has_issue_closing_reference,
)
from erk_shared.impl_folder import read_plan_ref
from erk_shared.output.output import user_output


class PrCheck(NamedTuple):
    passed: bool
    description: str


@click.command("check")
@click.option(
    "--stage",
    type=click.Choice(["impl"]),
    default=None,
    help="Run stage-specific checks. Use 'impl' to also verify .erk/impl-context/ was cleaned up.",
)
@click.pass_obj
def pr_check(ctx: ErkContext, stage: str | None) -> None:
    """Validate PR rules for the current branch.

    Checks that the PR:
    1. Has issue closing reference (Closes #N) when .impl/issue.json exists
    2. Has the standard checkout command footer
    3. Has plan-header metadata at correct position (not legacy top)

    With --stage=impl, also checks:
    4. .erk/impl-context/ has been cleaned up
    """
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

    # .impl always lives at worktree/repo root
    impl_dir = repo_root / ".impl"

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
    issue_number: int | None = None
    plan_ref = read_plan_ref(impl_dir) if impl_dir.exists() else None

    if plan_ref is not None:
        issue_number = int(plan_ref.plan_id)
        checks.append(
            PrCheck(
                passed=True,
                description=f"Plan reference found (#{issue_number})",
            )
        )

    # Check 1: Issue closing reference (if issue number is discoverable)
    # plan_ref already computed above
    if plan_ref is not None:
        if plan_ref.provider == "github-draft-pr":
            checks.append(
                PrCheck(passed=True, description="Draft PR plan — no closing reference needed")
            )
        else:
            expected_issue_number = int(plan_ref.plan_id)
            plans_repo: str | None
            if ctx.local_config is not None:
                plans_repo = ctx.local_config.plans_repo
            else:
                plans_repo = None
            if has_issue_closing_reference(pr_body, expected_issue_number, plans_repo):
                if plans_repo is None:
                    ref_display = f"#{expected_issue_number}"
                else:
                    ref_display = f"{plans_repo}#{expected_issue_number}"
                msg = f"PR body contains issue closing reference (Closes {ref_display})"
                checks.append(PrCheck(passed=True, description=msg))
            else:
                if plans_repo is None:
                    expected = f"Closes #{expected_issue_number}"
                else:
                    expected = f"Closes {plans_repo}#{expected_issue_number}"
                msg = f"PR body missing issue closing reference (expected: {expected})"
                checks.append(PrCheck(passed=False, description=msg))

    # Check 2: Checkout footer
    if has_checkout_footer_for_pr(pr_body, pr_number):
        checks.append(PrCheck(passed=True, description="PR body contains checkout footer"))
    else:
        checks.append(PrCheck(passed=False, description="PR body missing checkout footer"))

    # Check 3: Header position (not at legacy top position)
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
