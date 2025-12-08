import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from erk_shared.debug import debug_log
from erk_shared.output.output import user_output

from erk.cli.commands.prepare_cwd_recovery import generate_recovery_script
from erk.cli.shell_utils import (
    STALE_SCRIPT_MAX_AGE_SECONDS,
    cleanup_stale_scripts,
)
from erk.core.context import create_context

PASSTHROUGH_MARKER: Final[str] = "__ERK_PASSTHROUGH__"
PASSTHROUGH_COMMANDS: Final[set[str]] = {"sync"}

# Global flags that should be stripped from args before command matching
# These are top-level flags that don't affect which command is being invoked
GLOBAL_FLAGS: Final[set[str]] = {"--debug", "--dry-run", "--verbose", "-v"}

# Commands that support shell integration (directory switching)
# Maps command names (as received from shell) to CLI command paths (for subprocess)
# Keys are what the shell handler receives, values are what gets passed to subprocess
SHELL_INTEGRATION_COMMANDS: Final[dict[str, list[str]]] = {
    # Top-level commands (key matches CLI path)
    "checkout": ["checkout"],
    "co": ["checkout"],  # Alias for checkout
    "up": ["up"],
    "down": ["down"],
    "implement": ["implement"],
    # Subcommands under pr
    "pr land": ["pr", "land"],
    "pr checkout": ["pr", "checkout"],
    "pr co": ["pr", "checkout"],  # Alias for pr checkout
    # Legacy top-level aliases (map to actual CLI paths)
    "create": ["wt", "create"],
    "goto": ["wt", "goto"],
    "consolidate": ["stack", "consolidate"],
    # Subcommands under wt
    "wt create": ["wt", "create"],
    "wt goto": ["wt", "goto"],
    # Subcommands under stack
    "stack consolidate": ["stack", "consolidate"],
}


@dataclass(frozen=True)
class ShellIntegrationResult:
    """Result returned by shell integration handlers."""

    passthrough: bool
    script: str | None
    exit_code: int


def process_command_result(
    exit_code: int,
    stdout: str | None,
    stderr: str | None,
    command_name: str,
    exception: BaseException | None = None,
) -> ShellIntegrationResult:
    """Process command result and determine shell integration behavior.

    This function implements the core logic for deciding whether to use a script
    or passthrough based on command output. It prioritizes script availability
    over exit code to handle destructive commands that output scripts early.

    Args:
        exit_code: Command exit code
        stdout: Command stdout (expected to be script path if successful)
        stderr: Command stderr (error messages)
        command_name: Name of the command (for user messages)
        exception: Exception from CliRunner result (e.g., Click's MissingParameter)

    Returns:
        ShellIntegrationResult with passthrough, script, and exit_code
    """
    script_path = stdout.strip() if stdout else None

    debug_log(f"Handler: Got script_path={script_path}, exit_code={exit_code}")

    # Check if the script exists (only if we have a path)
    script_exists = False
    if script_path:
        script_exists = Path(script_path).exists()
        debug_log(f"Handler: Script exists? {script_exists}")

    # If we have a valid script, use it even if command had errors.
    # This handles destructive commands (like pr land) that output the script
    # before failure. The shell can still navigate to the destination.
    if script_path and script_exists:
        # Forward stderr so user sees status messages even on success
        # (e.g., "✓ Removed worktree", "✓ Deleted branch", etc.)
        if stderr:
            user_output(stderr, nl=False)
        return ShellIntegrationResult(passthrough=False, script=script_path, exit_code=exit_code)

    # No script available - if command failed, forward the error and don't passthrough.
    # Passthrough would run the command again WITHOUT --script, which for commands
    # like 'pr land' would show a misleading "requires shell integration" error
    # instead of the actual failure reason.
    if exit_code != 0:
        if stderr:
            user_output(stderr, nl=False)
        elif exception is not None:
            # Handle Click exceptions that don't go to stderr (e.g., MissingParameter)
            # When using standalone_mode=False, Click stores usage errors in result.exception
            # but leaves stderr empty, causing silent exits without this handling.
            user_output(f"Error: {exception}")
        return ShellIntegrationResult(passthrough=False, script=None, exit_code=exit_code)

    # Forward stderr messages to user (only for successful commands)
    if stderr:
        user_output(stderr, nl=False)

    # Note when command completed successfully but no directory change is needed
    if script_path is None or not script_path:
        user_output(f"Note: '{command_name}' completed (no directory change needed)")

    return ShellIntegrationResult(passthrough=False, script=script_path, exit_code=exit_code)


def _invoke_hidden_command(command_name: str, args: tuple[str, ...]) -> ShellIntegrationResult:
    """Invoke a command with --script flag for shell integration.

    If args contain help flags or explicit --script, passthrough to regular command.
    Otherwise, add --script flag and run as subprocess with live stderr streaming.

    Uses subprocess.run instead of CliRunner to allow stderr (user messages)
    to stream directly to the terminal in real-time, while capturing stdout
    (the activation script path) for shell integration.
    """
    # Check if help flags, --script, --dry-run, or non-interactive flags are present
    # These should pass through to avoid shell integration adding --script.
    # --yolo and --no-interactive conflict with --script (mutually exclusive).
    passthrough_flags = {"-h", "--help", "--script", "--dry-run", "--yolo", "--no-interactive"}
    if passthrough_flags & set(args):
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    cli_cmd_parts = SHELL_INTEGRATION_COMMANDS.get(command_name)
    if cli_cmd_parts is None:
        if command_name in PASSTHROUGH_COMMANDS:
            return _build_passthrough_script(command_name, args)
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Clean up stale scripts before running (opportunistic cleanup)
    cleanup_stale_scripts(max_age_seconds=STALE_SCRIPT_MAX_AGE_SECONDS)

    # Build full command: erk <cli_cmd_parts> <args> --script
    # cli_cmd_parts contains the actual CLI path (e.g., ["wt", "create"] for "create")
    cmd = ["erk", *cli_cmd_parts, *args, "--script"]

    debug_log(f"Handler: Running subprocess: {cmd}")

    # Run subprocess with:
    # - stdout captured (contains activation script path)
    # - stderr passed through to terminal (live streaming of user messages)
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,  # Capture stdout for script path
        stderr=None,  # Let stderr pass through to terminal (live streaming)
        text=True,
        check=False,  # Don't raise on non-zero exit
    )

    return process_command_result(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=None,  # stderr already shown to user
        command_name=command_name,
        exception=None,  # No exception from subprocess
    )


def handle_shell_request(args: tuple[str, ...]) -> ShellIntegrationResult:
    """Dispatch shell integration handling based on the original CLI invocation."""
    if len(args) == 0:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Strip global flags from the beginning of args before command matching
    # This ensures commands like "erk --debug pr land" are recognized correctly
    args_list = list(args)
    while args_list and args_list[0] in GLOBAL_FLAGS:
        args_list.pop(0)

    if len(args_list) == 0:
        return ShellIntegrationResult(passthrough=True, script=None, exit_code=0)

    # Try compound command first (e.g., "wt create", "stack consolidate")
    if len(args_list) >= 2:
        compound_name = f"{args_list[0]} {args_list[1]}"
        if compound_name in SHELL_INTEGRATION_COMMANDS:
            return _invoke_hidden_command(compound_name, tuple(args_list[2:]))

    # Fall back to single command
    command_name = args_list[0]
    command_args = tuple(args_list[1:]) if len(args_list) > 1 else ()
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
