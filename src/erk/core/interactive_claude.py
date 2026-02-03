"""Utilities for launching Claude CLI interactively.

This module provides helper functions for building Claude CLI argument lists
that respect the global interactive_agent configuration and CLI overrides.
"""

from erk_shared.context.types import (
    InteractiveAgentConfig,
    permission_mode_to_claude,
)


def build_claude_command_string(
    config: InteractiveAgentConfig,
    *,
    command: str,
) -> str:
    """Build Claude CLI command string for display or shell execution.

    Uses the resolved config (with any CLI overrides already applied via
    config.with_overrides()) to construct the command string.

    Args:
        config: InteractiveAgentConfig with resolved values
        command: The slash command to execute (empty string for no command)

    Returns:
        Shell command string suitable for display
    """
    permission_mode = permission_mode_to_claude(config.permission_mode)
    cmd = f"claude --permission-mode {permission_mode}"

    if config.dangerous:
        cmd += " --dangerously-skip-permissions"

    if config.allow_dangerous:
        cmd += " --allow-dangerously-skip-permissions"

    if config.model is not None:
        cmd += f" --model {config.model}"

    if command:
        cmd += f' "{command}"'

    return cmd
