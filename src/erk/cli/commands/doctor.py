"""Doctor command for erk setup diagnostics.

Runs health checks on the erk setup to identify issues with
CLI availability, repository configuration, and Claude settings.
"""

import click

from erk.core.context import ErkContext
from erk.core.health_checks import CheckResult, run_all_checks


def _format_check_result(result: CheckResult) -> None:
    """Format and display a single check result."""
    if result.passed:
        icon = click.style("✅", fg="green")
    else:
        icon = click.style("❌", fg="red")

    click.echo(f"{icon} {result.message}")

    if result.details:
        # Show details with indentation
        for line in result.details.split("\n"):
            click.echo(click.style(f"   {line}", dim=True))


@click.command("doctor")
@click.pass_obj
def doctor_cmd(ctx: ErkContext) -> None:
    """Run diagnostic checks on erk setup.

    Checks for:

    \b
      - CLI tools: erk, claude, gt, gh
      - Kit health: kit configuration
      - Repository: git setup, .erk/ directory
      - Claude settings: hooks, configuration

    Examples:

    \b
      # Run all checks
      erk doctor
    """
    click.echo(click.style("🔍 Checking erk setup...", bold=True))
    click.echo("")

    # Run all checks
    results = run_all_checks(ctx)

    # Group results by category
    cli_tool_names = ("erk", "claude", "graphite", "github")
    cli_checks = [r for r in results if r.name in cli_tool_names]
    health_checks = [r for r in results if r.name == "kit health"]
    repo_checks = [r for r in results if r.name in ("repository", "claude settings")]

    # Display CLI availability
    click.echo(click.style("CLI Tools", bold=True))
    for result in cli_checks:
        _format_check_result(result)
    click.echo("")

    # Display health checks if any
    if health_checks:
        click.echo(click.style("Health Checks", bold=True))
        for result in health_checks:
            _format_check_result(result)
        click.echo("")

    # Display repository checks
    click.echo(click.style("Repository Setup", bold=True))
    for result in repo_checks:
        _format_check_result(result)
    click.echo("")

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    failed = total - passed

    if failed == 0:
        click.echo(click.style("✨ All checks passed!", fg="green", bold=True))
    else:
        click.echo(click.style(f"⚠️  {failed} check(s) failed", fg="yellow", bold=True))
