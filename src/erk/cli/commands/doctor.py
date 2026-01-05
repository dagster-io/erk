"""Doctor command for erk setup diagnostics.

Runs health checks on the erk setup to identify issues with
CLI availability, repository configuration, and Claude settings.
"""

import click

from erk.core.context import ErkContext
from erk.core.health_checks import CheckResult, run_all_checks
from erk.core.health_checks_dogfooder import EARLY_DOGFOODER_CHECK_NAMES
from erk_shared.hooks.logging import clear_hook_logs

# Sub-group definitions for Repository Setup condensed display
REPO_SUBGROUPS: dict[str, set[str]] = {
    "Git repository": {"repository", "gitignore"},
    "Claude settings": {
        "claude-erk-permission",
        "claude-settings",
        "user-prompt-hook",
        "exit-plan-hook",
    },
    "Erk configuration": {
        "required-version",
        "legacy-prompt-hooks",
        "legacy-config",
        "managed-artifacts",
        "post-plan-implement-ci-hook",
    },
    "GitHub": {"workflow-permissions"},
    "Hooks": {"hooks"},
}

# Sub-group definitions for User Setup condensed display
USER_SUBGROUPS: dict[str, set[str]] = {
    "User checks": {"github-auth", "claude-hooks", "statusline", "shell-integration"},
}


def _format_check_result(result: CheckResult, indent: str = "", verbose: bool = False) -> None:
    """Format and display a single check result.

    Args:
        result: The check result to format
        indent: Optional indentation prefix for nested display
        verbose: If True and verbose_details exists, use it instead of details
    """
    if not result.passed:
        icon = click.style("❌", fg="red")
    elif result.warning:
        icon = click.style("⚠️", fg="yellow")
    elif result.info:
        icon = click.style("ℹ️", fg="cyan")
    else:
        icon = click.style("✅", fg="green")

    # Use verbose_details in verbose mode if available, otherwise use details
    details = result.verbose_details if verbose and result.verbose_details else result.details

    if details and "\n" not in details:
        # Single-line details: show inline
        styled_details = click.style(f" - {details}", dim=True)
        click.echo(f"{indent}{icon} {result.message}{styled_details}")
    else:
        click.echo(f"{indent}{icon} {result.message}")
        if details:
            # Multi-line details: show with indentation
            for line in details.split("\n"):
                click.echo(click.style(f"{indent}   {line}", dim=True))


def _format_subgroup(name: str, checks: list[CheckResult], verbose: bool, indent: str = "") -> None:
    """Format a sub-group of checks (condensed or expanded).

    Args:
        name: Sub-group display name
        checks: List of check results in this sub-group
        verbose: If True, always show all individual checks
        indent: Indentation prefix
    """
    if not checks:
        return

    passed = sum(1 for c in checks if c.passed)
    total = len(checks)
    all_passed = passed == total

    if verbose:
        # Always show all individual checks with sub-group header
        click.echo(click.style(f"{indent}  {name}", dim=True))
        for result in checks:
            _format_check_result(result, indent=f"{indent}  ", verbose=True)
    elif all_passed:
        # Condensed: single line with count
        icon = click.style("✅", fg="green")
        click.echo(f"{indent}{icon} {name} ({total} checks)")
    else:
        # Failed: show summary line + expand failures
        icon = click.style("❌", fg="red")
        click.echo(f"{indent}{icon} {name} ({passed}/{total} checks)")
        for result in checks:
            if not result.passed:
                _format_check_result(result, indent=f"{indent}   ", verbose=False)


@click.command("doctor")
@click.option("-v", "--verbose", is_flag=True, help="Show all individual checks")
@click.option("--dogfooder", is_flag=True, help="Include early dogfooder migration checks")
@click.option(
    "--clear-hook-logs", "clear_hook_logs_flag", is_flag=True, help="Clear all hook execution logs"
)
@click.pass_obj
def doctor_cmd(ctx: ErkContext, verbose: bool, dogfooder: bool, clear_hook_logs_flag: bool) -> None:
    """Run diagnostic checks on erk setup.

    Checks for:

    \b
      - Repository Setup: git config, Claude settings, erk config, hooks
      - User Setup: prerequisites (erk, claude, gt, gh, uv), GitHub auth

    Examples:

    \b
      # Run checks (condensed output)
      erk doctor

      # Show all individual checks
      erk doctor --verbose

      # Include early dogfooder migration checks
      erk doctor --dogfooder

      # Clear hook execution logs
      erk doctor --clear-hook-logs
    """
    # Handle --clear-hook-logs flag (clears logs and returns early)
    if clear_hook_logs_flag:
        deleted_count = clear_hook_logs(ctx.repo_root)
        click.echo(f"Cleared {deleted_count} hook log(s)")
        return

    click.echo(click.style("🔍 Checking erk setup...", bold=True))
    click.echo("")

    # Run all checks
    results = run_all_checks(ctx)

    # Group results by category
    prerequisite_names = {"erk", "claude", "graphite", "github", "uv"}
    user_check_names = {"github-auth", "claude-hooks", "statusline", "shell-integration"}
    repo_check_names = {
        "repository",
        "claude-settings",
        "user-prompt-hook",
        "exit-plan-hook",
        "gitignore",
        "claude-erk-permission",
        "legacy-config",
        "required-version",
        "legacy-prompt-hooks",
        "managed-artifacts",
        "post-plan-implement-ci-hook",
        "workflow-permissions",
        "hooks",
    }

    prerequisite_checks = [r for r in results if r.name in prerequisite_names]
    user_checks = [r for r in results if r.name in user_check_names]
    repo_checks = [r for r in results if r.name in repo_check_names]
    early_dogfooder_checks = [r for r in results if r.name in EARLY_DOGFOODER_CHECK_NAMES]

    # Track displayed check names to catch any uncategorized checks
    displayed_names = (
        prerequisite_names | user_check_names | repo_check_names | EARLY_DOGFOODER_CHECK_NAMES
    )

    # Display Repository Setup FIRST (with sub-groups)
    click.echo(click.style("Repository Setup", bold=True))
    if verbose:
        # In verbose mode, show sub-groups with all individual checks
        for subgroup_name, subgroup_check_names in REPO_SUBGROUPS.items():
            subgroup_checks = [r for r in repo_checks if r.name in subgroup_check_names]
            _format_subgroup(subgroup_name, subgroup_checks, verbose=True)
    else:
        # Condensed mode: show sub-group summaries
        for subgroup_name, subgroup_check_names in REPO_SUBGROUPS.items():
            subgroup_checks = [r for r in repo_checks if r.name in subgroup_check_names]
            _format_subgroup(subgroup_name, subgroup_checks, verbose=False)
    click.echo("")

    # Display Early Dogfooder checks (only when --dogfooder flag is passed)
    if dogfooder and early_dogfooder_checks:
        click.echo(click.style("Early Dogfooder", bold=True))
        for result in early_dogfooder_checks:
            _format_check_result(result, verbose=verbose)
        click.echo("")

    # Display User Setup SECOND
    click.echo(click.style("User Setup", bold=True))
    # Prerequisites (always expanded)
    for result in prerequisite_checks:
        _format_check_result(result, verbose=verbose)
    # User checks (condensable subgroup)
    if verbose:
        for subgroup_name, subgroup_check_names in USER_SUBGROUPS.items():
            subgroup_checks = [r for r in user_checks if r.name in subgroup_check_names]
            _format_subgroup(subgroup_name, subgroup_checks, verbose=True)
    else:
        for subgroup_name, subgroup_check_names in USER_SUBGROUPS.items():
            subgroup_checks = [r for r in user_checks if r.name in subgroup_check_names]
            _format_subgroup(subgroup_name, subgroup_checks, verbose=False)
    click.echo("")

    # Display any uncategorized checks (defensive - catches missing categorization)
    other_checks = [r for r in results if r.name not in displayed_names]
    if other_checks:
        click.echo(click.style("Other Checks", bold=True))
        for result in other_checks:
            _format_check_result(result, verbose=verbose)
        click.echo("")

    # Collect and display consolidated remediations for failing checks
    remediations = {r.remediation for r in results if r.remediation and not r.passed}
    if remediations:
        click.echo(click.style("Remediation", bold=True))
        for remediation in sorted(remediations):
            click.echo(f"  {remediation}")
        click.echo("")

    # Calculate summary - exclude dogfooder checks from total if not showing them
    checks_for_summary = [r for r in results if r.name not in EARLY_DOGFOODER_CHECK_NAMES]
    if dogfooder:
        checks_for_summary = results

    passed = sum(1 for r in checks_for_summary if r.passed)
    total = len(checks_for_summary)
    failed = total - passed

    if failed == 0:
        click.echo(click.style("✨ All checks passed!", fg="green", bold=True))
    else:
        click.echo(click.style(f"⚠️  {failed} check(s) failed", fg="yellow", bold=True))
