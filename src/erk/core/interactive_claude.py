"""Utilities for launching Claude CLI interactively.

This module provides helper functions for building Claude CLI argument lists
that respect the global interactive_claude configuration and CLI overrides.
"""

from erk_shared.context.types import InteractiveClaudeConfig


def build_claude_args(
    config: InteractiveClaudeConfig,
    *,
    command: str,
) -> list[str]:
    """Build Claude CLI argument list for interactive launch.

    Uses the resolved config (with any CLI overrides already applied via
    config.with_overrides()) to construct the argument list.

    Args:
        config: InteractiveClaudeConfig with resolved values
        command: The slash command to execute (empty string for no command)

    Returns:
        List of command arguments suitable for subprocess or os.execvp
    """
    args = ["claude", "--permission-mode", config.permission_mode]

    if config.dangerous:
        args.append("--dangerously-skip-permissions")

    if config.model is not None:
        args.extend(["--model", config.model])

    # Only append command if non-empty (allows launching Claude for planning)
    if command:
        args.append(command)

    return args


def build_claude_command_string(
    config: InteractiveClaudeConfig,
    *,
    command: str,
) -> str:
    """Build Claude CLI command string for display or shell execution.

    Uses the resolved config (with any CLI overrides already applied via
    config.with_overrides()) to construct the command string.

    Args:
        config: InteractiveClaudeConfig with resolved values
        command: The slash command to execute (empty string for no command)

    Returns:
        Shell command string suitable for display
    """
    cmd = f"claude --permission-mode {config.permission_mode}"

    if config.dangerous:
        cmd += " --dangerously-skip-permissions"

    if config.model is not None:
        cmd += f" --model {config.model}"

    if command:
        cmd += f' "{command}"'

    return cmd
