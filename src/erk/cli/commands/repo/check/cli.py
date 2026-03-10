"""Human command for repo check with [PASS]/[FAIL] output."""

import click

from erk.cli.commands.repo.check.operation import (
    RepoCheckRequest,
    RepoCheckResult,
    run_repo_check,
)
from erk_shared.output.output import user_output


@click.command("check")
@click.argument("repo", type=str)
def repo_check(repo: str) -> None:
    """Validate remote repo setup for erk workflows.

    REPO should be in 'owner/repo' format (e.g., 'myorg/myrepo').

    Checks workflows, secrets, variables, permissions, and labels
    required for erk's remote automation to work.
    """
    result = run_repo_check(RepoCheckRequest(repo=repo))
    _render_human(result)


def _render_human(result: RepoCheckResult) -> None:
    """Render [PASS]/[FAIL] output for each check."""
    user_output(f"Checking repo {result.repo}...")
    user_output("")

    for item in result.checks:
        tag = "[PASS]" if item.passed else "[FAIL]"
        color = "green" if item.passed else "red"
        status = click.style(tag, fg=color)
        user_output(f"{status} {item.message}")
        if not item.passed and item.remediation is not None:
            user_output(f"       {click.style(item.remediation, dim=True)}")

    user_output("")

    passed_count = sum(1 for item in result.checks if item.passed)
    total_count = len(result.checks)

    if result.all_passed:
        user_output(click.style(f"All checks passed ({passed_count}/{total_count})", fg="green"))
    else:
        failed_count = total_count - passed_count
        check_word = "checks" if failed_count > 1 else "check"
        msg = (
            f"Repo check failed"
            f" ({failed_count} {check_word} failed,"
            f" {passed_count}/{total_count} passed)"
        )
        user_output(click.style(msg, fg="red"))
        raise SystemExit(1)
