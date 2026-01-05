"""Doctor command for erk setup diagnostics.

Runs health checks on the erk setup to identify issues with
CLI availability, repository configuration, and Claude settings.
"""

import click

from erk.core.context import ErkContext
from erk.core.health_checks import CheckResult, run_all_checks
from erk.core.health_checks_dogfooder import EARLY_DOGFOODER_CHECK_NAMES

# Sub-group definitions for Repository Setup condensed display
REPO_SUBGROUPS: dict[str, set[str]] = {
    "Git repository": {"repository", "gitignore"},
    "Claude settings": {
        "claude-hooks",
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
        "statusline",
        "post-plan-implement-ci-hook",
    },
}


def _format_check_result(result: CheckResult, indent: str = "") -> None:
    """Format and display a single check result.

    Args:
        result: The check result to format
        indent: Optional indentation prefix for nested display
    """
    if not result.passed:
        icon = click.style("❌", fg="red")
    elif result.warning:
        icon = click.style("⚠️", fg="yellow")
    elif result.info:
        icon = click.style("ℹ️", fg="cyan")
    else:
        icon = click.style("✅", fg="green")

    if result.details and "\n" not in result.details:
        # Single-line details: show inline
        styled_details = click.style(f" - {result.details}", dim=True)
        click.echo(f"{indent}{icon} {result.message}{styled_details}")
    else:
        click.echo(f"{indent}{icon} {result.message}")
        if result.details:
            # Multi-line details: show with indentation
            for line in result.details.split("\n"):
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
            _format_check_result(result, indent=f"{indent}  ")
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
                _format_check_result(result, indent=f"{indent}   ")


@click.command("doctor")
@click.option("-v", "--verbose", is_flag=True, help="Show all individual checks")
@click.option("--dogfooder", is_flag=True, help="Include early dogfooder migration checks")
@click.pass_obj
def doctor_cmd(ctx: ErkContext, verbose: bool, dogfooder: bool) -> None:
    """Run diagnostic checks on erk setup.

    Checks for:

    \b
      - Prerequisites: erk, claude, gt, gh, uv
      - Repository: git setup, .erk/ directory
      - Claude settings: hooks, configuration

    Examples:

    \b
      # Run checks (condensed output)
      erk doctor

      # Show all individual checks
      erk doctor --verbose

      # Include early dogfooder migration checks
      erk doctor --dogfooder
    """
    click.echo(click.style("🔍 Checking erk setup...", bold=True))
    click.echo("")

    # Run all checks
    results = run_all_checks(ctx)

    # Group results by category
    prerequisite_names = {"erk", "claude", "graphite", "github", "uv"}
    repo_check_names = {
        "repository",
        "claude-settings",
        "user-prompt-hook",
        "exit-plan-hook",
        "gitignore",
        "claude-erk-permission",
        "claude-hooks",
        "legacy-config",
        "required-version",
        "legacy-prompt-hooks",
        "managed-artifacts",
        "statusline",
        "post-plan-implement-ci-hook",
    }
    github_check_names = {"github-auth", "workflow-permissions"}
    hooks_check_names = {"hooks"}

    prerequisite_checks = [r for r in results if r.name in prerequisite_names]
    repo_checks = [r for r in results if r.name in repo_check_names]
    github_checks = [r for r in results if r.name in github_check_names]
    hooks_checks = [r for r in results if r.name in hooks_check_names]
    early_dogfooder_checks = [r for r in results if r.name in EARLY_DOGFOODER_CHECK_NAMES]

    # Track displayed check names to catch any uncategorized checks
    displayed_names = (
        prerequisite_names
        | repo_check_names
        | github_check_names
        | hooks_check_names
        | EARLY_DOGFOODER_CHECK_NAMES
    )

    # Display Prerequisites (always expanded - these are important)
    click.echo(click.style("Prerequisites", bold=True))
    for result in prerequisite_checks:
        _format_check_result(result)
    click.echo("")

    # Display Repository Setup (with sub-groups)
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

    # Display GitHub checks
    if github_checks:
        click.echo(click.style("GitHub", bold=True))
        for result in github_checks:
            _format_check_result(result)
        click.echo("")

    # Display Hooks checks
    if hooks_checks:
        click.echo(click.style("Hooks", bold=True))
        for result in hooks_checks:
            _format_check_result(result)
        click.echo("")

    # Display Early Dogfooder checks (only when --dogfooder flag is passed)
    if dogfooder and early_dogfooder_checks:
        click.echo(click.style("Early Dogfooder", bold=True))
        for result in early_dogfooder_checks:
            _format_check_result(result)
        click.echo("")

    # Display any uncategorized checks (defensive - catches missing categorization)
    other_checks = [r for r in results if r.name not in displayed_names]
    if other_checks:
        click.echo(click.style("Other Checks", bold=True))
        for result in other_checks:
            _format_check_result(result)
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
