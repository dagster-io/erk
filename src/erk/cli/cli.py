import logging
import os
import sys
from pathlib import Path

import click

from erk.cli.alias import register_with_aliases
from erk.cli.commands.admin import admin_group
from erk.cli.commands.artifact.group import artifact_group
from erk.cli.commands.branch import branch_group
from erk.cli.commands.cc import cc_group
from erk.cli.commands.completion import completion_group
from erk.cli.commands.config import config_group
from erk.cli.commands.docs.group import docs_group
from erk.cli.commands.doctor import doctor_cmd
from erk.cli.commands.down import down_cmd
from erk.cli.commands.exec.group import exec_group
from erk.cli.commands.implement import implement
from erk.cli.commands.info import info_group
from erk.cli.commands.init import init_group
from erk.cli.commands.land_cmd import land
from erk.cli.commands.learn import learn_cmd
from erk.cli.commands.log_cmd import log_cmd
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
from erk.cli.commands.slot import slot_group
from erk.cli.commands.stack import stack_group
from erk.cli.commands.up import up_cmd
from erk.cli.commands.upgrade import upgrade_cmd
from erk.cli.commands.wt import wt_group
from erk.cli.help_formatter import ErkCommandGroup
from erk.core.command_log import get_cli_args, log_command_start, register_exit_handler
from erk.core.context import create_context
from erk.core.release_notes import check_for_version_change, get_current_version
from erk.core.version_check import (
    format_version_warning,
    get_required_version,
    is_version_mismatch,
)
from erk_shared.gateway.console.real import InteractiveConsole
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from erk_shared.git.real import RealGit

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # terse help flags


def _show_version_change_banner() -> None:
    """Show upgrade banner with full release notes if version has changed.

    Displays all release notes since the last seen version and prompts user
    to confirm before continuing. This function is designed to never fail -
    exceptions are logged but don't break the CLI.
    """
    try:
        erk_installation = RealErkInstallation()
        changed, releases = check_for_version_change(erk_installation)
        if not changed or not releases:
            return

        current = get_current_version()

        # Build banner header
        click.echo(file=sys.stderr)
        click.echo(
            click.style(f"  ✨ erk updated to v{current}", fg="green", bold=True), file=sys.stderr
        )
        click.echo(click.style("  " + "─" * 50, dim=True), file=sys.stderr)
        click.echo(file=sys.stderr)

        # Show all releases with their items grouped by category
        for release in releases:
            # Skip releases with no items
            if not release.items:
                continue

            # Version header
            header = f"  [{release.version}]"
            if release.date:
                header += f" - {release.date}"
            click.echo(click.style(header, bold=True), file=sys.stderr)

            # Show items grouped by category if available
            if release.categories:
                for category, category_items in release.categories.items():
                    if not category_items:
                        continue
                    click.echo(click.style(f"    {category}", dim=True), file=sys.stderr)
                    for item_text, indent_level in category_items:
                        # Base indent (6 spaces) + extra indent per nesting level (2 spaces)
                        indent = "      " + ("  " * indent_level)
                        click.echo(f"{indent}• {item_text}", file=sys.stderr)
            else:
                # Fallback to flat list for releases without categories
                for item_text, indent_level in release.items:
                    indent = "    " + ("  " * indent_level)
                    click.echo(f"{indent}• {item_text}", file=sys.stderr)
            click.echo(file=sys.stderr)

        click.echo(click.style("  " + "─" * 50, dim=True), file=sys.stderr)
        click.echo(file=sys.stderr)

        # Prompt user to continue (only if stdin is a TTY)
        console = InteractiveConsole()
        if console.is_stdin_interactive():
            click.pause(info=click.style("  Press Enter to continue...", dim=True), err=True)
    except click.Abort:
        # User pressed Ctrl+C or declined - exit gracefully
        raise SystemExit(0) from None
    except Exception as e:
        # Never let release notes break the CLI, but warn so issues can be diagnosed
        logging.warning("Failed to show version change banner: %s", e)


def _show_version_warning() -> None:
    """Show warning if installed erk version doesn't match repo-required version.

    This is designed to never fail - exceptions are logged but don't break the CLI.
    """
    # Skip if user has disabled version checking
    if os.environ.get("ERK_SKIP_VERSION_CHECK") == "1":
        return

    try:
        # Check if we're in a git repo using LBYL pattern
        # (get_git_common_dir returns None gracefully, get_repository_root raises)
        git = RealGit()
        git_dir = git.get_git_common_dir(Path.cwd())
        if git_dir is None:
            return

        repo_root = git.get_repository_root(Path.cwd())
        if repo_root is None:
            return

        # Read required version from repo
        required = get_required_version(repo_root)
        if required is None:
            return

        # Compare versions
        installed = get_current_version()
        if not is_version_mismatch(installed, required):
            return

        # Show warning
        click.echo(format_version_warning(installed, required), err=True)
        click.echo(file=sys.stderr)
    except Exception as e:
        # Never let version checking break the CLI, but warn so issues can be diagnosed
        logging.warning("Failed to check version: %s", e)


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
        _show_version_warning()

    # Only create context if not already provided (e.g., by tests)
    if ctx.obj is None:
        ctx.obj = create_context(dry_run=False)


# Register all commands
# Commands with @alias decorators use register_with_aliases() to auto-register aliases
cli.add_command(admin_group)
cli.add_command(artifact_group)
register_with_aliases(cli, branch_group)  # Has @alias("br")
cli.add_command(cc_group)
cli.add_command(completion_group)
cli.add_command(config_group)
cli.add_command(doctor_cmd)
cli.add_command(down_cmd)
register_with_aliases(cli, implement)  # Has @alias("impl")
cli.add_command(init_group)
cli.add_command(land)
cli.add_command(learn_cmd)
admin_group.add_command(log_cmd)
cli.add_command(dash)
cli.add_command(plan_group)
cli.add_command(planner_group)
cli.add_command(pr_group)
cli.add_command(info_group)
cli.add_command(objective_group)
cli.add_command(project_group)
cli.add_command(slot_group)
cli.add_command(run_group)
cli.add_command(stack_group)
cli.add_command(up_cmd)
cli.add_command(upgrade_cmd)
cli.add_command(wt_group)
cli.add_command(hidden_shell_cmd)
cli.add_command(prepare_cwd_recovery_cmd)

# Additional command groups
cli.add_command(docs_group)
cli.add_command(exec_group)
cli.add_command(md_group)


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    # Log command start and register exit handler for completion logging
    entry_id = log_command_start(get_cli_args(), Path.cwd())
    register_exit_handler(entry_id)

    cli()
