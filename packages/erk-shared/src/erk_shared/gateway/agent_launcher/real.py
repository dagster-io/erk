"""Real AgentLauncher implementation using Claude CLI.

RealAgentLauncher provides process replacement to launch Claude CLI
interactively.
"""

import os
import shutil
from typing import NoReturn

from erk_shared.context.types import InteractiveClaudeConfig
from erk_shared.gateway.agent_launcher.abc import AgentLauncher


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

    if config.allow_dangerous:
        args.append("--allow-dangerously-skip-permissions")

    if config.model is not None:
        args.extend(["--model", config.model])

    # Only append command if non-empty (allows launching Claude for planning)
    if command:
        args.append(command)

    return args


class RealAgentLauncher(AgentLauncher):
    """Production implementation using Claude CLI for interactive sessions."""

    def launch_interactive(self, config: InteractiveClaudeConfig, *, command: str) -> NoReturn:
        """Replace current process with Claude CLI session.

        Uses os.execvp() to replace the current process with Claude CLI.

        Args:
            config: InteractiveClaudeConfig with resolved values
            command: The slash command to execute (empty string for no command)

        Raises:
            RuntimeError: If Claude CLI is not available in PATH

        Note:
            This method never returns - the process is replaced.
        """
        # Check Claude CLI availability
        if shutil.which("claude") is None:
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        # Build Claude CLI arguments
        cmd_args = build_claude_args(config, command=command)

        # Replace current process with Claude
        os.execvp("claude", cmd_args)
