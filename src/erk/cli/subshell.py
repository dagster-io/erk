"""Subshell utilities for launching Claude in worktrees without shell integration.

When shell integration (ERK_SHELL) is not active, these functions provide a fallback
mechanism that spawns a subshell in the worktree directory and automatically launches
Claude within it.
"""

import os
from pathlib import Path

import click

from erk_shared.gateway.shell import Shell


def is_shell_integration_active() -> bool:
    """Check if ERK_SHELL env var is set (indicates shell wrapper is active)."""
    return os.environ.get("ERK_SHELL") is not None


def detect_user_shell() -> str:
    """Return $SHELL or default to /bin/sh."""
    return os.environ.get("SHELL", "/bin/sh")


def build_prompt_setup_command(shell_path: str) -> str:
    """Build shell command to modify PS1 for visual indicator.

    Returns empty string if ERK_NO_PROMPT_MODIFY is set or for unsupported shells.

    Args:
        shell_path: Path to the shell executable (e.g., /bin/bash, /bin/zsh)

    Returns:
        Shell command to set PS1, or empty string if opt-out or unsupported shell.
    """
    # Check opt-out
    if os.environ.get("ERK_NO_PROMPT_MODIFY") is not None:
        return ""

    # Detect shell type from path
    shell_name = Path(shell_path).name

    # Fish has different syntax and fish users typically use custom prompts
    if shell_name == "fish":
        return ""

    # bash, zsh, sh all support the same PS1 syntax
    if shell_name in ("bash", "zsh", "sh"):
        return 'export PS1="(erk:$ERK_WORKTREE_NAME) $PS1"'

    # Unknown shell - skip prompt modification
    return ""


def format_subshell_welcome_message(worktree_path: Path, branch: str) -> str:
    """Format welcome banner for worktree subshell.

    Args:
        worktree_path: Path to the worktree directory
        branch: Current branch name

    Returns:
        Formatted welcome message string
    """
    return f"""\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are now in a worktree subshell.
Branch: {branch}
Type 'exit' to return to your original directory.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


def build_claude_command_string(
    *,
    claude_command: str,
    dangerous: bool,
    model: str | None,
) -> str:
    """Build the quoted Claude CLI command string for shell execution.

    Args:
        claude_command: The slash command to execute (e.g., "/erk:plan-implement")
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

    Returns:
        Shell-quoted command string ready for execution
    """
    claude_args = ["claude", "--permission-mode", "acceptEdits"]
    if dangerous:
        claude_args.append("--dangerously-skip-permissions")
    if model is not None:
        claude_args.extend(["--model", model])
    claude_args.append(claude_command)

    # Quote arguments for shell
    # Simple quoting - wrap in single quotes, escape existing single quotes
    def shell_quote(s: str) -> str:
        return "'" + s.replace("'", "'\\''") + "'"

    return " ".join(shell_quote(arg) for arg in claude_args)


def spawn_worktree_subshell(
    shell_gateway: Shell,
    *,
    worktree_path: Path,
    branch: str,
    claude_command: str,
    dangerous: bool,
    model: str | None,
    shell: str | None,
) -> int:
    """Spawn subshell in worktree that auto-launches Claude.

    Uses the Shell gateway to spawn user's shell with:
    - cwd set to worktree_path
    - ERK_SUBSHELL=1 and ERK_WORKTREE_NAME in environment
    - Automatic PS1 modification for visual indicator (unless ERK_NO_PROMPT_MODIFY is set)
    - Shell command to launch Claude with provided args

    Args:
        shell_gateway: Shell gateway for spawning the subshell
        worktree_path: Path to worktree directory
        branch: Current branch name (for display in welcome message)
        claude_command: The slash command to execute (e.g., "/erk:plan-implement")
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        shell: Override for user's shell (for testing), None uses $SHELL

    Returns:
        Exit code when subshell exits
    """
    # Determine shell to use
    user_shell = shell if shell is not None else detect_user_shell()

    # Build Claude command string
    claude_cmd_str = build_claude_command_string(
        claude_command=claude_command,
        dangerous=dangerous,
        model=model,
    )

    # Build prompt setup command (may be empty if opt-out or unsupported shell)
    prompt_setup = build_prompt_setup_command(user_shell)

    # Combine prompt setup with Claude command
    if prompt_setup:
        full_command = f"{prompt_setup}; {claude_cmd_str}"
    else:
        full_command = claude_cmd_str

    # Build environment for subshell
    subshell_env: dict[str, str] = {
        "ERK_SUBSHELL": "1",
        "ERK_WORKTREE_NAME": worktree_path.name,
    }

    # Pass through ERK_NO_PROMPT_MODIFY if set (so nested subshells respect it)
    opt_out_value = os.environ.get("ERK_NO_PROMPT_MODIFY")
    if opt_out_value is not None:
        subshell_env["ERK_NO_PROMPT_MODIFY"] = opt_out_value

    # Print welcome message
    welcome_msg = format_subshell_welcome_message(worktree_path, branch)
    click.echo(welcome_msg)
    click.echo()

    # Use Shell gateway to spawn the subshell
    return shell_gateway.spawn_subshell(
        cwd=worktree_path,
        shell_path=user_shell,
        command=full_command,
        env=subshell_env,
    )


def spawn_simple_subshell(
    shell_gateway: Shell,
    *,
    worktree_path: Path,
    branch: str,
    shell: str | None,
) -> int:
    """Spawn subshell in worktree for navigation (no Claude auto-launch).

    Uses the Shell gateway to spawn user's shell with:
    - cwd set to worktree_path
    - ERK_SUBSHELL=1 and ERK_WORKTREE_NAME in environment
    - Automatic PS1 modification for visual indicator (unless ERK_NO_PROMPT_MODIFY is set)

    Unlike spawn_worktree_subshell(), this does NOT auto-launch Claude. It's intended
    for checkout commands where the user just wants to navigate to a worktree.

    Args:
        shell_gateway: Shell gateway for spawning the subshell
        worktree_path: Path to worktree directory
        branch: Current branch name (for display in welcome message)
        shell: Override for user's shell (for testing), None uses $SHELL

    Returns:
        Exit code when subshell exits
    """
    # Determine shell to use
    user_shell = shell if shell is not None else detect_user_shell()

    # Build prompt setup command (may be empty if opt-out or unsupported shell)
    prompt_setup = build_prompt_setup_command(user_shell)

    # Build environment for subshell
    subshell_env: dict[str, str] = {
        "ERK_SUBSHELL": "1",
        "ERK_WORKTREE_NAME": worktree_path.name,
    }

    # Pass through ERK_NO_PROMPT_MODIFY if set (so nested subshells respect it)
    opt_out_value = os.environ.get("ERK_NO_PROMPT_MODIFY")
    if opt_out_value is not None:
        subshell_env["ERK_NO_PROMPT_MODIFY"] = opt_out_value

    # Print welcome message
    welcome_msg = format_subshell_welcome_message(worktree_path, branch)
    click.echo(welcome_msg)
    click.echo()

    # Use Shell gateway to spawn the subshell
    # If prompt setup exists, pass it as a command to execute at shell startup
    # For shells without prompt setup (fish, unknown, or opted out), pass ":" (no-op)
    return shell_gateway.spawn_subshell(
        cwd=worktree_path,
        shell_path=user_shell,
        command=prompt_setup if prompt_setup else ":",
        env=subshell_env,
    )
