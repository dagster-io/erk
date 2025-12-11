import logging
import sys

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.admin import admin_group
from erk.cli.commands.artifact.group import artifact_group
from erk.cli.commands.checkout import checkout_cmd
from erk.cli.commands.completion import completion_group
from erk.cli.commands.config import config_group
from erk.cli.commands.dev.group import dev_group
from erk.cli.commands.docs.group import docs_group
from erk.cli.commands.doctor import doctor_cmd
from erk.cli.commands.down import down_cmd
from erk.cli.commands.hook.group import hook_group
from erk.cli.commands.implement import implement
from erk.cli.commands.info import info_group
from erk.cli.commands.init import init_cmd
from erk.cli.commands.kit.group import kit_group
from erk.cli.commands.md.group import md_group
from erk.cli.commands.objective import objective_group
from erk.cli.commands.plan import plan_group
from erk.cli.commands.plan.list_cmd import dash
from erk.cli.commands.planner import planner_group
from erk.cli.commands.pr import pr_group
from erk.cli.commands.prepare_cwd_recovery import prepare_cwd_recovery_cmd
from erk.cli.commands.project import project_group
from erk.cli.commands.run import run_group
from erk.cli.commands.shell_integration import hidden_shell_cmd
from erk.cli.commands.stack import stack_group
from erk.cli.commands.submit import submit_cmd
from erk.cli.commands.up import up_cmd
from erk.cli.commands.wt import wt_group
from erk.cli.help_formatter import ErkCommandGroup
from erk.core.context import create_context

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # terse help flags

# Maximum number of items to show in upgrade banner
MAX_BANNER_ITEMS = 3


def _show_version_change_banner() -> None:
    """Show upgrade banner if version has changed since last run.

    This function is designed to never fail - any exception is silently caught
    to ensure the CLI always works even if release notes are broken.
    """
    # Inline import to avoid import-time side effects
    from erk.core.release_notes import check_for_version_change, get_current_version

    try:
        changed, releases = check_for_version_change()
        if not changed or not releases:
            return

        current = get_current_version()

        # Collect all items from new releases
        all_items: list[str] = []
        for release in releases:
            all_items.extend(release.items)

        if not all_items:
            return

        # Build banner
        click.echo(file=sys.stderr)
        click.echo(
            click.style(f"  ✨ erk updated to v{current}", fg="green", bold=True), file=sys.stderr
        )
        click.echo(click.style("  " + "─" * 36, dim=True), file=sys.stderr)

        # Show first N items
        shown_items = all_items[:MAX_BANNER_ITEMS]
        for item in shown_items:
            click.echo(f"    • {item}", file=sys.stderr)

        # Show overflow count if needed
        remaining = len(all_items) - MAX_BANNER_ITEMS
        if remaining > 0:
            click.echo(click.style(f"    ... and {remaining} more", dim=True), file=sys.stderr)

        click.echo(click.style("  " + "─" * 36, dim=True), file=sys.stderr)
        msg = "  Run 'erk info release-notes' to see full notes"
        click.echo(click.style(msg, dim=True), file=sys.stderr)
        click.echo(file=sys.stderr)
    except Exception:
        # Never let release notes break the CLI
        pass


@click.group(cls=ErkCommandGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="erk")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Manage git worktrees in a global worktrees directory."""
    if debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s")

    # Show version change banner (only on actual CLI runs, not completions)
    if not ctx.resilient_parsing:
        _show_version_change_banner()

    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = create_context(dry_run=False)


# Register all commands
# Commands with @alias decorators use register_with_aliases() to auto-register aliases
cli.add_command(admin_group)
register_with_aliases(cli, checkout_cmd)  # Has @alias("co")
cli.add_command(completion_group)
cli.add_command(config_group)
cli.add_command(doctor_cmd)
cli.add_command(down_cmd)
cli.add_command(implement)
cli.add_command(init_cmd)
cli.add_command(dash)
cli.add_command(objective_group)
cli.add_command(plan_group)
cli.add_command(planner_group)
cli.add_command(pr_group)
cli.add_command(info_group)
cli.add_command(project_group)
cli.add_command(run_group)
cli.add_command(stack_group)
cli.add_command(submit_cmd)
cli.add_command(up_cmd)
cli.add_command(wt_group)
cli.add_command(hidden_shell_cmd)
cli.add_command(prepare_cwd_recovery_cmd)

# Kit management command groups
cli.add_command(artifact_group)
cli.add_command(dev_group)
cli.add_command(docs_group)
cli.add_command(hook_group)
cli.add_command(kit_group)
cli.add_command(md_group)


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
