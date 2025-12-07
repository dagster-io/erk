"""Command to validate PR rules for the current branch."""

import re
from pathlib import Path

import click
from erk_shared.github.types import PRNotFound
from erk_shared.impl_folder import read_issue_reference
from erk_shared.output.output import user_output

from erk.core.context import ErkContext


@click.command("check")
@click.pass_obj
def pr_check(ctx: ErkContext) -> None:
    """Validate PR rules for the current branch.

    Checks that the PR:
    1. Has issue closing reference (Closes #N) when .impl/issue.json exists
    2. Has the standard checkout command footer
    """
    # Get current branch
    branch = ctx.git.get_current_branch(ctx.cwd)
    if branch is None:
        user_output(click.style("Error: ", fg="red") + "Not on a branch (detached HEAD)")
        raise SystemExit(1)

    # Get repo root for GitHub operations
    repo_root = ctx.git.get_repository_root(ctx.cwd)

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

    # Check 1: Issue closing reference (if .impl/issue.json exists)
    impl_dir = Path(ctx.cwd) / ".impl"
    issue_ref = read_issue_reference(impl_dir)

    if issue_ref is not None:
        # Check for "Closes #N" pattern
        expected_issue_number = issue_ref.issue_number
        closing_pattern = rf"Closes\s+#{expected_issue_number}\b"
        has_closing_ref = bool(re.search(closing_pattern, pr_body, re.IGNORECASE))

        if has_closing_ref:
            msg = f"PR body contains issue closing reference (Closes #{expected_issue_number})"
            checks.append((True, msg))
        else:
            issue_num = expected_issue_number
            msg = f"PR body missing issue closing reference (expected: Closes #{issue_num})"
            checks.append((False, msg))

    # Check 2: Checkout footer
    footer_pattern = rf"erk pr checkout {pr_number}\b"
    has_footer = bool(re.search(footer_pattern, pr_body))

    if has_footer:
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
