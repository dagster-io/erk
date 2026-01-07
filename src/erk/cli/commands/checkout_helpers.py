"""Checkout navigation helpers - shared across checkout commands.

This module is separate from navigation_helpers.py to avoid circular imports.
navigation_helpers imports from wt.create_cmd, which triggers wt/__init__.py,
which imports wt.checkout_cmd. By having checkout-specific helpers here,
we break that cycle.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from erk.cli.activation import render_activation_script
from erk.core.context import ErkContext


def navigate_to_worktree(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    branch: str,
    script: bool,
    command_name: str,
    script_message: str,
    relative_path: Path | None,
    post_cd_commands: Sequence[str] | None,
) -> bool:
    """Navigate to worktree, handling script/subshell/shell-integration modes.

    This function consolidates the three-mode navigation pattern used by checkout commands:
    1. Script mode: Generate activation script and output for shell integration
    2. No shell integration: Spawn a subshell in the worktree directory
    3. Shell integration active: Return True so caller can output custom message

    Args:
        ctx: Erk context (for script_writer and shell gateway)
        worktree_path: Path to the target worktree directory
        branch: Branch name (for subshell display)
        script: Whether running in script mode
        command_name: Name of the command (for script generation)
        script_message: Message to echo in activation script (e.g., 'echo "Switched to worktree"')
        relative_path: Computed relative path to preserve directory position, or None
        post_cd_commands: Optional shell commands to run after cd

    Returns:
        True if caller should output custom message (shell integration mode).
        In script and subshell modes, this function exits via sys.exit() and does not return.
    """
    from erk.cli.subshell import is_shell_integration_active, spawn_simple_subshell

    if script:
        activation_script = render_activation_script(
            worktree_path=worktree_path,
            target_subpath=relative_path,
            post_cd_commands=post_cd_commands,
            final_message=script_message,
            comment="work activate-script",
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=f"checkout {branch}",
        )
        result.output_for_shell_integration()
        sys.exit(0)
    elif not is_shell_integration_active():
        exit_code = spawn_simple_subshell(
            ctx.shell,
            worktree_path=worktree_path,
            branch=branch,
            shell=None,
        )
        sys.exit(exit_code)
    else:
        return True  # Caller should output custom message
