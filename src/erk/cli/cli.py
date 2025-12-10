import logging

import click

from dot_agent_kit.commands.artifact.group import artifact_group
from dot_agent_kit.commands.dev.group import dev_group
from dot_agent_kit.commands.docs.group import docs_group
from dot_agent_kit.commands.hook.group import hook_group
from dot_agent_kit.commands.kit.group import kit_group
from dot_agent_kit.commands.md.group import md_group
from erk.cli.alias import register_with_aliases
from erk.cli.commands.admin import admin_group
from erk.cli.commands.checkout import checkout_cmd
from erk.cli.commands.completion import completion_group
from erk.cli.commands.config import config_group
from erk.cli.commands.doctor import doctor_cmd
from erk.cli.commands.down import down_cmd
from erk.cli.commands.implement import implement
from erk.cli.commands.init import init_cmd
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


@click.group(cls=ErkCommandGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="erk")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """Manage git worktrees in a global worktrees directory."""
    if debug:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s")

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
cli.add_command(project_group)
cli.add_command(run_group)
cli.add_command(stack_group)
cli.add_command(submit_cmd)
cli.add_command(up_cmd)
cli.add_command(wt_group)
cli.add_command(hidden_shell_cmd)
cli.add_command(prepare_cwd_recovery_cmd)

# Kit management command groups (facade imports from dot-agent-kit)
cli.add_command(artifact_group)
cli.add_command(dev_group)
cli.add_command(docs_group)
cli.add_command(hook_group)
cli.add_command(kit_group)
cli.add_command(md_group)


def main() -> None:
    """CLI entry point used by the `erk` console script."""
    cli()
