"""Command to validate PR rules for the current branch."""

import click

from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.pr.submit import (
    has_checkout_footer_for_pr,
    has_issue_closing_reference,
)
from erk_shared.impl_folder import read_plan_ref, validate_plan_linkage
from erk_shared.output.output import user_output


@click.command("check")
@click.pass_obj
def pr_check(ctx: ErkContext) -> None:
    """Validate PR rules for the current branch.

    Checks that the PR:
    1. Has issue closing reference (Closes #N) when .impl/issue.json exists
    2. Has the standard checkout command footer
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
    checks: list[tuple[bool, str]] = []

    pr_body = pr.body

    # .impl always lives at worktree/repo root
    impl_dir = repo_root / ".impl"

    # Check 0: Branch/plan-ref agreement
    # This catches cases where branch name says "P42-..." but plan-ref says #99
    issue_number: int | None = None
    try:
        plan_id = validate_plan_linkage(impl_dir, branch)
        if plan_id is not None:
            issue_number = int(plan_id)
            checks.append((True, f"Branch name and plan reference agree (#{issue_number})"))
    except ValueError as e:
        checks.append((False, str(e)))
        # Continue with other checks - use the plan ref as fallback
        plan_ref_fallback = read_plan_ref(impl_dir)
        if plan_ref_fallback is not None:
            issue_number = int(plan_ref_fallback.plan_id)

    # Check 1: Issue closing reference (if issue number is discoverable)
    plan_ref = read_plan_ref(impl_dir)

    if plan_ref is not None:
        expected_issue_number = int(plan_ref.plan_id)
        plans_repo = ctx.local_config.plans_repo if ctx.local_config else None
        if has_issue_closing_reference(pr_body, expected_issue_number, plans_repo):
            # Format expected reference for display
            if plans_repo is None:
                ref_display = f"#{expected_issue_number}"
            else:
                ref_display = f"{plans_repo}#{expected_issue_number}"
            msg = f"PR body contains issue closing reference (Closes {ref_display})"
            checks.append((True, msg))
        else:
            if plans_repo is None:
                expected = f"Closes #{expected_issue_number}"
            else:
                expected = f"Closes {plans_repo}#{expected_issue_number}"
            msg = f"PR body missing issue closing reference (expected: {expected})"
            checks.append((False, msg))

    # Check 2: Checkout footer
    if has_checkout_footer_for_pr(pr_body, pr_number):
        checks.append((True, "PR body contains checkout footer"))
    else:
        checks.append((False, "PR body missing checkout footer"))

    # Output results
    for passed, description in checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        user_output(f"{status} {description}")

    user_output("")

    # Determine overall result
    failed_count = sum(1 for passed, _ in checks if not passed)
    if failed_count == 0:
        user_output(click.style("All checks passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "check" if failed_count == 1 else "checks"
        user_output(click.style(f"{failed_count} {check_word} failed", fg="red"))
        raise SystemExit(1)
