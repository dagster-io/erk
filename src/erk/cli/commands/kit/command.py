"""Top-level command for executing Claude Code slash commands."""

# TODO: Future enhancements
# 1. Improved formatting - Enhance output formatting and styling consistency
# 2. Status bars that are prettier - Add visual progress indicators and status displays

from pathlib import Path

import click

from erk.kits.cli.output import user_output
from erk_kits.data.kits.command.scripts.command.models import (
    CommandNotFoundError,
)
from erk_kits.data.kits.command.scripts.command.ops import (
    RealClaudeCliOps,
)
from erk_kits.data.kits.command.scripts.command.resolution import (
    resolve_command_file,
)


def complete_command_name(ctx: click.Context, param: click.Parameter, incomplete: str) -> list[str]:
    """Provide shell completion for command names.

    Args:
        ctx: Click context (unused but required by Click API)
        param: Click parameter (unused but required by Click API)
        incomplete: Partial command name typed by user

    Returns:
        List of command names that start with incomplete text
    """
    # Get available commands from current directory
    project_dir = Path.cwd()

    # Check if .claude/commands/ exists (LBYL)
    if not (project_dir / ".claude" / "commands").exists():
        return []

    # Get all available commands
    all_commands = discover_commands(project_dir)

    # Filter commands that start with the incomplete text
    return [cmd for cmd in all_commands if cmd.startswith(incomplete)]


def discover_commands(project_dir: Path) -> list[str]:
    """Discover available commands in .claude/commands/.

    Args:
        project_dir: Project root directory

    Returns:
        Sorted list of command names (includes both flat and namespaced)
    """
    commands_dir = project_dir / ".claude" / "commands"
    if not commands_dir.exists():
        return []

    commands = []

    # Find all .md files in commands directory
    for md_file in commands_dir.rglob("*.md"):
        # Get relative path from commands_dir
        rel_path = md_file.relative_to(commands_dir)

        # Remove .md extension
        command_path = str(rel_path.with_suffix(""))

        # Convert path to command name
        # commands/ensure-ci.md -> ensure-ci
        # commands/gt/submit-branch.md -> gt:submit-branch
        if "/" in command_path:
            parts = command_path.split("/")
            command_name = ":".join(parts)
        else:
            command_name = command_path

        commands.append(command_name)

    return sorted(commands)


def format_help_text(ctx: click.Context, project_dir: Path) -> str:
    """Generate help text with dynamic command list.

    Args:
        ctx: Click context
        project_dir: Project root directory

    Returns:
        Formatted help text
    """
    # Get base help from Click
    help_text = ctx.get_help()

    # Discover available commands
    commands = discover_commands(project_dir)

    if len(commands) == 0:
        commands_section = "\nNo commands found in .claude/commands/\n"
    else:
        commands_section = "\nAvailable commands:\n"
        for cmd in commands:
            commands_section += f"  • {cmd}\n"

    # Insert commands section before "Options:" section
    if "Options:" in help_text:
        parts = help_text.split("Options:")
        help_text = parts[0] + commands_section + "\nOptions:" + parts[1]
    else:
        help_text += commands_section

    return help_text


@click.command()
@click.argument("command_name", required=False, shell_complete=complete_command_name)
@click.option("--json", is_flag=True, help="Output JSON for scripting")
@click.pass_context
def command(ctx: click.Context, command_name: str | None, json: bool) -> None:
    """Execute a Claude Code slash command.

    COMMAND_NAME can be a flat command (e.g., ensure-ci) or namespaced
    (e.g., gt:submit-branch).

    Examples:

        dot-agent command ensure-ci

        dot-agent command gt:submit-branch

        dot-agent command --json ensure-ci

    Shell Completion:

        Enable tab completion for command names:

        For Bash:
            eval "$(_DOT_AGENT_COMPLETE=bash_source dot-agent)"

        For Zsh:
            eval "$(_DOT_AGENT_COMPLETE=zsh_source dot-agent)"

        For Fish:
            _DOT_AGENT_COMPLETE=fish_source dot-agent | source

        Add to your shell's rc file (.bashrc, .zshrc, etc.) for persistent completion.
    """
    project_dir = Path.cwd()

    # If no command name provided, show help with available commands
    if command_name is None:
        help_text = format_help_text(ctx, project_dir)
        user_output(help_text)
        return

    try:
        # Validate command exists (LBYL)
        resolve_command_file(command_name, project_dir)

        # Execute command via ops layer
        cli_ops = RealClaudeCliOps()
        result = cli_ops.execute_command(
            command_name=command_name,
            cwd=project_dir,
            json_output=json,
        )

        raise SystemExit(result.returncode)

    except CommandNotFoundError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        user_output("\nAvailable commands:")
        commands = discover_commands(project_dir)
        if len(commands) == 0:
            user_output("  (none found in .claude/commands/)")
        else:
            for cmd in commands:
                user_output(f"  • {cmd}")
        raise SystemExit(1) from None
    except FileNotFoundError:
        user_output(click.style("Error: ", fg="red") + "claude CLI not found")
        user_output("\nInstall Claude Code from: https://claude.com/claude-code")
        raise SystemExit(1) from None
    except Exception as e:
        user_output(click.style("Unexpected error: ", fg="red") + str(e))
        raise SystemExit(1) from e
