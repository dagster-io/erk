"""CLI command for executing Claude Code slash commands."""

from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk_kits.data.kits.command.scripts.command.models import (
    CommandNotFoundError,
)
from erk_kits.data.kits.command.scripts.command.ops import (
    ClaudeCliOps,
    RealClaudeCliOps,
)
from erk_kits.data.kits.command.scripts.command.resolution import (
    resolve_command_file,
)


def execute_command_impl(
    command_name: str,
    json: bool,
    cli_ops: ClaudeCliOps,
) -> int:
    """Implementation of command execution (testable with dependency injection).

    Args:
        command_name: Name of the command to execute
        json: Whether to use JSON output format
        cli_ops: ClaudeCliOps implementation for executing commands

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Validate command exists (LBYL)
    cwd = Path.cwd()
    resolve_command_file(command_name, cwd)

    # Execute command via ops layer
    result = cli_ops.execute_command(
        command_name=command_name,
        cwd=cwd,
        json_output=json,
    )

    return result.returncode


@click.command()
@click.argument("command_name")
@click.option("--json", is_flag=True, help="Output JSON for scripting")
def execute(command_name: str, json: bool) -> None:
    """Execute a Claude Code slash command via out-of-process CLI.

    Examples:
        erk kit exec command execute gt:submit-branch
        erk kit exec command execute ensure-ci --json
    """
    try:
        cli_ops = RealClaudeCliOps()
        exit_code = execute_command_impl(command_name, json, cli_ops)
        raise SystemExit(exit_code)

    except CommandNotFoundError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None
    except FileNotFoundError:
        user_output(click.style("Error: ", fg="red") + "claude CLI not found")
        user_output("\nInstall Claude Code from: https://claude.com/claude-code")
        raise SystemExit(1) from None
    except Exception as e:
        user_output(click.style("Unexpected error: ", fg="red") + str(e))
        raise SystemExit(1) from e
