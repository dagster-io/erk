"""Check PR completion invariants before submission.

Validates that implementation is complete and PR is ready for submission.
Combines the existing pr-check validations with implementation-specific checks
like ensuring .erk/impl-context/ has been cleaned up.

Usage:
    erk exec pr-check-complete

Output:
    [PASS]/[FAIL] for each check, with overall summary

Exit Codes:
    0: All checks passed
    1: One or more checks failed

Examples:
    $ erk exec pr-check-complete
    Checking PR #123 for branch P42-my-feature...

    [PASS] .erk/impl-context/ not present (cleaned up)
    [PASS] Branch name and plan reference agree (#42)
    [PASS] PR body contains issue closing reference (Closes #42)
    [PASS] PR body contains checkout footer
    [PASS] Plan-header metadata is at correct position

    All checks passed
"""

from pathlib import Path

import click

from erk.cli.ensure import Ensure
from erk_shared.context.helpers import require_context, require_cwd, require_git, require_github
from erk_shared.gateway.github.pr_footer import (
    extract_header_from_body,
    is_header_at_legacy_position,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.pr.submit import (
    has_checkout_footer_for_pr,
    has_issue_closing_reference,
)
from erk_shared.impl_folder import read_plan_ref, validate_plan_linkage


def _check_impl_context_absent(repo_root: Path) -> tuple[bool, str]:
    """Check that .erk/impl-context/ does not exist.

    This directory is created during plan-save and should be removed
    (via git rm) before implementation completes.
    """
    impl_context_dir = repo_root / ".erk" / "impl-context"
    if impl_context_dir.exists():
        return (False, ".erk/impl-context/ still present (should be removed before submission)")
    return (True, ".erk/impl-context/ not present (cleaned up)")


@click.command(name="pr-check-complete")
@click.pass_context
def pr_check_complete(ctx: click.Context) -> None:
    """Check PR completion invariants before submission.

    Validates that:
    1. .erk/impl-context/ has been cleaned up
    2. Branch/plan-ref agreement
    3. Issue closing reference present
    4. Checkout footer present
    5. Plan-header at correct position
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    github = require_github(ctx)

    # Get current branch
    branch = Ensure.not_none(
        git.branch.get_current_branch(cwd),
        "Not on a branch (detached HEAD)",
    )

    # Get repo root
    repo_root = git.repo.get_repository_root(cwd)

    # Get PR for branch
    pr = github.get_pr_for_branch(repo_root, branch)
    if isinstance(pr, PRNotFound):
        click.echo(
            click.style("Error: ", fg="red") + f"No pull request found for branch '{branch}'"
        )
        raise SystemExit(1)

    pr_number = pr.number
    pr_body = pr.body

    click.echo(f"Checking PR #{pr_number} for branch {branch}...")
    click.echo("")

    # Track validation results
    checks: list[tuple[bool, str]] = []

    # .impl always lives at worktree/repo root
    impl_dir = repo_root / ".impl"

    # Check 0: .erk/impl-context/ must not be present
    checks.append(_check_impl_context_absent(repo_root))

    # Check 1: Branch/plan-ref agreement
    issue_number: int | None = None
    try:
        plan_id = validate_plan_linkage(impl_dir, branch)
        if plan_id is not None:
            issue_number = int(plan_id)
            checks.append((True, f"Branch name and plan reference agree (#{issue_number})"))
    except ValueError as e:
        checks.append((False, str(e)))
        plan_ref_fallback = read_plan_ref(impl_dir)
        if plan_ref_fallback is not None:
            issue_number = int(plan_ref_fallback.plan_id)

    # Check 2: Issue closing reference
    plan_ref = read_plan_ref(impl_dir)

    if plan_ref is not None:
        if plan_ref.provider == "github-draft-pr":
            checks.append((True, "Draft PR plan — no closing reference needed"))
        else:
            expected_issue_number = int(plan_ref.plan_id)
            erk_ctx = require_context(ctx)
            plans_repo = erk_ctx.local_config.plans_repo if erk_ctx.local_config else None
            if has_issue_closing_reference(pr_body, expected_issue_number, plans_repo):
                if plans_repo is None:
                    ref_display = f"#{expected_issue_number}"
                else:
                    ref_display = f"{plans_repo}#{expected_issue_number}"
                checks.append(
                    (True, f"PR body contains issue closing reference (Closes {ref_display})")
                )
            else:
                if plans_repo is None:
                    expected = f"Closes #{expected_issue_number}"
                else:
                    expected = f"Closes {plans_repo}#{expected_issue_number}"
                checks.append(
                    (False, f"PR body missing issue closing reference (expected: {expected})")
                )

    # Check 3: Checkout footer
    if has_checkout_footer_for_pr(pr_body, pr_number):
        checks.append((True, "PR body contains checkout footer"))
    else:
        checks.append((False, "PR body missing checkout footer"))

    # Check 4: Header position
    header = extract_header_from_body(pr_body)
    if header:
        if is_header_at_legacy_position(pr_body):
            checks.append(
                (False, "Plan-header metadata is at legacy top position (should be above footer)")
            )
        else:
            checks.append((True, "Plan-header metadata is at correct position"))

    # Output results
    for passed, description in checks:
        status = click.style("[PASS]", fg="green") if passed else click.style("[FAIL]", fg="red")
        click.echo(f"{status} {description}")

    click.echo("")

    # Determine overall result
    failed_count = sum(1 for passed, _ in checks if not passed)
    if failed_count == 0:
        click.echo(click.style("All checks passed", fg="green"))
        raise SystemExit(0)
    else:
        check_word = "check" if failed_count == 1 else "checks"
        click.echo(click.style(f"{failed_count} {check_word} failed", fg="red"))
        raise SystemExit(1)
