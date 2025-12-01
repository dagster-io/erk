import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from click import Command
from click.testing import CliRunner
from erk_shared.debug import debug_log
from erk_shared.output.output import user_output

from erk.cli.commands.checkout import checkout_cmd
from erk.cli.commands.down import down_cmd
from erk.cli.commands.implement import implement
from erk.cli.commands.pr import pr_group
from erk.cli.commands.prepare_cwd_recovery import generate_recovery_script
from erk.cli.commands.stack.consolidate_cmd import consolidate_stack
from erk.cli.commands.up import up_cmd
from erk.cli.commands.wt.create_cmd import create_wt
from erk.cli.commands.wt.goto_cmd import goto_wt
from erk.cli.shell_utils import (
    STALE_SCRIPT_MAX_AGE_SECONDS,
    cleanup_stale_scripts,
)
from erk.core.context import create_context

PASSTHROUGH_MARKER: Final[str] = "__ERK_PASSTHROUGH__"
PASSTHROUGH_COMMANDS: Final[set[str]] = {"sync"}

# Commands that support shell integration (directory switching)
# Uses compound keys for subcommands (e.g., "wt create" instead of just "create")
# Also supports legacy top-level aliases for backward compatibility
SHELL_INTEGRATION_COMMANDS: Final[dict[str, Command]] = {
    # Top-level commands
    "checkout": checkout_cmd,
    "co": checkout_cmd,  # Alias
    "up": up_cmd,
    "down": down_cmd,
    "implement": implement,
    "pr": pr_group,
    # Legacy top-level aliases (for backward compatibility)
    "create": create_wt,
    "goto": goto_wt,
    "consolidate": consolidate_stack,
    # Subcommands under wt
    "wt create": create_wt,
    "wt goto": goto_wt,
    # Subcommands under stack
    "stack consolidate": consolidate_stack,
}


@dataclass(frozen=True)
class ShellIntegrationResult:
    """Result returned by shell integration handlers."""

    passthrough: bool
    script: str | None
    exit_code: int


def _invoke_hidden_command(command_name: str, args: tuple[str, ...]) -> ShellIntegrationResult:
    """Invoke a command with --script flag for shell integration.

    If args contain help flags or explicit --script, passthrough to regular command.
    Otherwise, add --script flag and capture the activation script.
    """
    # Check if help flags, --script, or --dry-run are present - these should pass through
    # Dry-run mode should show output directly, not via shell integration
    if "-h" in args or "--help" in args or "--script" in args or "--dry-run" in args:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    command = SHELL_INTEGRATION_COMMANDS.get(command_name)
    if command is None:
        if command_name in PASSTHROUGH_COMMANDS:
            return _build_passthrough_script(command_name, args)
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Add --script flag to get activation script
    script_args = list(args) + ["--script"]

    debug_log(f"Handler: Invoking {command_name} with args: {script_args}")

    # Clean up stale scripts before running (opportunistic cleanup)
    cleanup_stale_scripts(max_age_seconds=STALE_SCRIPT_MAX_AGE_SECONDS)

    runner = CliRunner()
    result = runner.invoke(
        command,
        script_args,
        obj=create_context(dry_run=False, script=True),
        standalone_mode=False,
    )

    exit_code = int(result.exit_code)

    # If command failed, passthrough to show proper error
    # Don't forward stderr here - the passthrough execution will show it
    if exit_code != 0:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=exit_code)

    # Forward stderr messages to user (only for successful commands)
    if result.stderr:
        user_output(result.stderr, nl=False)

    # Output is now a file path, not script content
    # Click 8.2+ separates streams; result.stdout contains only stdout
    script_path = result.stdout.strip() if result.stdout else None

    debug_log(f"Handler: Got script_path={script_path}, exit_code={exit_code}")

    # Check if the script exists (only if we have a path)
    if script_path:
        script_exists = Path(script_path).exists()
        debug_log(f"Handler: Script exists? {script_exists}")

    # Note when command completed successfully but no directory change is needed
    if exit_code == 0 and (script_path is None or not script_path):
        user_output(f"Note: '{command_name}' completed (no directory change needed)")

    return ShellIntegrationResult(passthrough=False, script=script_path, exit_code=exit_code)


def handle_shell_request(args: tuple[str, ...]) -> ShellIntegrationResult:
    """Dispatch shell integration handling based on the original CLI invocation."""
    if len(args) == 0:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Try compound command first (e.g., "wt create", "stack consolidate")
    if len(args) >= 2:
        compound_name = f"{args[0]} {args[1]}"
        if compound_name in SHELL_INTEGRATION_COMMANDS:
            return _invoke_hidden_command(compound_name, tuple(args[2:]))

    # Fall back to single command
    command_name = args[0]
    command_args = args[1:] if len(args) > 1 else ()
    return _invoke_hidden_command(command_name, command_args)


def _build_passthrough_script(command_name: str, args: tuple[str, ...]) -> ShellIntegrationResult:
    """Create a passthrough script tailored for the caller's shell."""
    shell_name = os.environ.get("ERK_SHELL", "bash").lower()
    ctx = create_context(dry_run=False)
    recovery_path = generate_recovery_script(ctx)

    script_content = _render_passthrough_script(shell_name, command_name, args, recovery_path)
    result = ctx.script_writer.write_activation_script(
        script_content,
        command_name=f"{command_name}-passthrough",
        comment="generated by __shell passthrough handler",
    )
    return ShellIntegrationResult(passthrough=False, script=str(result.path), exit_code=0)


def _render_passthrough_script(
    shell_name: str,
    command_name: str,
    args: tuple[str, ...],
    recovery_path: Path | None,
) -> str:
    """Render shell-specific script that runs the command and performs recovery."""
    if shell_name == "fish":
        return _render_fish_passthrough(command_name, args, recovery_path)
    return _render_posix_passthrough(command_name, args, recovery_path)


def _render_posix_passthrough(
    command_name: str,
    args: tuple[str, ...],
    recovery_path: Path | None,
) -> str:
    quoted_args = " ".join(shlex.quote(part) for part in (command_name, *args))
    recovery_literal = shlex.quote(str(recovery_path)) if recovery_path is not None else "''"
    lines = [
        f"command erk {quoted_args}",
        "__erk_exit=$?",
        f"__erk_recovery={recovery_literal}",
        'if [ -n "$__erk_recovery" ] && [ -f "$__erk_recovery" ]; then',
        '  if [ ! -d "$PWD" ]; then',
        '    . "$__erk_recovery"',
        "  fi",
        '  if [ -z "$ERK_KEEP_SCRIPTS" ]; then',
        '    rm -f "$__erk_recovery"',
        "  fi",
        "fi",
        "return $__erk_exit",
    ]
    return "\n".join(lines) + "\n"


def _quote_fish(arg: str) -> str:
    if not arg:
        return '""'

    escape_map = {
        "\\": "\\\\",
        '"': '\\"',
        "$": "\\$",
        "`": "\\`",
        "~": "\\~",
        "*": "\\*",
        "?": "\\?",
        "{": "\\{",
        "}": "\\}",
        "[": "\\[",
        "]": "\\]",
        "(": "\\(",
        ")": "\\)",
        "<": "\\<",
        ">": "\\>",
        "|": "\\|",
        ";": "\\;",
        "&": "\\&",
    }
    escaped_parts: list[str] = []
    for char in arg:
        if char == "\n":
            escaped_parts.append("\\n")
            continue
        if char == "\t":
            escaped_parts.append("\\t")
            continue
        escaped_parts.append(escape_map.get(char, char))

    escaped = "".join(escaped_parts)
    return f'"{escaped}"'


def _render_fish_passthrough(
    command_name: str,
    args: tuple[str, ...],
    recovery_path: Path | None,
) -> str:
    command_parts = " ".join(_quote_fish(part) for part in (command_name, *args))
    recovery_literal = _quote_fish(str(recovery_path)) if recovery_path is not None else '""'
    lines = [
        f"command erk {command_parts}",
        "set __erk_exit $status",
        f"set __erk_recovery {recovery_literal}",
        'if test -n "$__erk_recovery"',
        '    if test -f "$__erk_recovery"',
        '        if not test -d "$PWD"',
        '            source "$__erk_recovery"',
        "        end",
        "        if not set -q ERK_KEEP_SCRIPTS",
        '            rm -f "$__erk_recovery"',
        "        end",
        "    end",
        "end",
        "return $__erk_exit",
    ]
    return "\n".join(lines) + "\n"
