"""Plan command group with verb/noun dual behavior.

Following the `git branch` pattern:
- Verb (no args): `erk plan` → launches remote planning via Codespace
- Noun (with subcommands): `erk plan list`, `erk plan get <id>` → plan management
"""

import os
import shutil

import click
from erk_shared.output.output import user_output

from erk.cli.commands.plan.check_cmd import check_plan
from erk.cli.commands.plan.close_cmd import close_plan
from erk.cli.commands.plan.create_cmd import create_plan
from erk.cli.commands.plan.get import get_plan
from erk.cli.commands.plan.list_cmd import list_plans
from erk.cli.commands.plan.log_cmd import plan_log
from erk.core.codespace import get_or_create_codespace


def _run_remote_planning(cwd_path: str, description: str) -> None:
    """Create/reuse Codespace and auto-execute Claude with /erk:craft-plan.

    Args:
        cwd_path: Current working directory path
        description: Optional description for the plan

    Note:
        This function uses os.execvp to replace the current process with SSH.
        It does not return on success.

    Raises:
        SystemExit: If codespace creation fails or Claude CLI is not available
    """
    from pathlib import Path

    cwd = Path(cwd_path)

    user_output("Looking for existing Codespace or creating new one...")

    codespace_name = get_or_create_codespace(cwd)

    # Build slash command
    slash_cmd = "/erk:craft-plan"
    if description:
        slash_cmd = f"/erk:craft-plan {description}"

    # Auto-execute Claude via SSH with command
    ssh_cmd = [
        "gh",
        "codespace",
        "ssh",
        "-c",
        codespace_name,
        "--",  # Command follows
        "claude",
        "--permission-mode",
        "acceptEdits",
        slash_cmd,
    ]

    user_output(f"Connecting to Codespace '{codespace_name}' and starting planning...")
    os.execvp("gh", ssh_cmd)


def _run_local_planning(description: str) -> None:
    """Run Claude with /erk:craft-plan in current directory.

    Args:
        description: Optional description for the plan

    Note:
        This function uses os.execvp to replace the current process with Claude.
        It does not return on success.

    Raises:
        SystemExit: If Claude CLI is not available
    """
    # LBYL: Check if claude CLI is available
    if shutil.which("claude") is None:
        user_output(click.style("Error: ", fg="red") + "Claude CLI not found.")
        user_output("Please install Claude CLI: https://docs.anthropic.com/claude-code")
        raise SystemExit(1)

    slash_cmd = "/erk:craft-plan"
    if description:
        slash_cmd = f"/erk:craft-plan {description}"

    cmd = ["claude", "--permission-mode", "acceptEdits", slash_cmd]

    user_output("Starting local planning with Claude...")
    os.execvp("claude", cmd)


@click.group("plan", invoke_without_command=True)
@click.option(
    "--local",
    is_flag=True,
    help="Plan in current directory instead of remote Codespace",
)
@click.option(
    "-m",
    "--message",
    "description",
    default="",
    help="Description for the plan (e.g., -m 'add user auth')",
)
@click.pass_context
def plan_group(ctx: click.Context, local: bool, description: str) -> None:
    """Manage implementation plans.

    When called without a subcommand, launches planning mode:

    \b
    erk plan                         # Remote: create/reuse Codespace + auto-execute Claude
    erk plan -m "add user auth"      # Remote with description
    erk plan --local                 # Local: run Claude in current directory
    erk plan --local -m "add auth"   # Local with description

    For plan management, use subcommands:

    \b
    erk plan list               # List all plans
    erk plan get 42             # Get specific plan
    erk plan create --file f    # Create plan from file
    """
    if ctx.invoked_subcommand is None:
        # Verb usage: launch planning mode
        if local:
            _run_local_planning(description)
        else:
            # Get cwd from context or use current directory
            cwd_path = str(ctx.obj.cwd) if ctx.obj else os.getcwd()
            _run_remote_planning(cwd_path, description)


plan_group.add_command(check_plan)
plan_group.add_command(close_plan)
plan_group.add_command(create_plan, name="create")
plan_group.add_command(get_plan)
plan_group.add_command(list_plans, name="list")
plan_group.add_command(plan_log, name="log")
