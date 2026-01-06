"""Subshell utilities for launching Claude in worktrees without shell integration.

When shell integration (ERK_SHELL) is not active, these functions provide a fallback
mechanism that spawns a subshell in the worktree directory and automatically launches
Claude within it.
"""

import os
import subprocess
from pathlib import Path

import click


def is_shell_integration_active() -> bool:
    """Check if ERK_SHELL env var is set (indicates shell wrapper is active)."""
    return os.environ.get("ERK_SHELL") is not None


def detect_user_shell() -> str:
    """Return $SHELL or default to /bin/sh."""
    return os.environ.get("SHELL", "/bin/sh")


def format_subshell_welcome_message(worktree_path: Path, branch: str) -> str:
    """Format welcome banner with prompt customization hint.

    Args:
        worktree_path: Path to the worktree directory
        branch: Current branch name

    Returns:
        Formatted welcome message string
    """
    prompt_hint = """\
To show this in your prompt, add to ~/.bashrc or ~/.zshrc:
  if [ -n "$ERK_SUBSHELL" ]; then
    PS1="(erk:$ERK_WORKTREE_NAME) $PS1"
  fi"""

    return f"""\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are now in a subshell at: {worktree_path}
Branch: {branch}

{prompt_hint}

Type 'exit' to return to your original directory.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


def spawn_worktree_subshell(
    *,
    worktree_path: Path,
    branch: str,
    claude_command: str,
    dangerous: bool,
    model: str | None,
    shell: str | None,
) -> int:
    """Spawn subshell in worktree that auto-launches Claude.

    Uses subprocess.run() to spawn user's shell with:
    - cwd set to worktree_path
    - ERK_SUBSHELL=1 and ERK_WORKTREE_NAME in environment
    - Shell command to launch Claude with provided args

    Args:
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
    shell_name = Path(user_shell).name

    # Build Claude command
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

    claude_cmd_str = " ".join(shell_quote(arg) for arg in claude_args)

    # Build environment for subshell
    env = os.environ.copy()
    env["ERK_SUBSHELL"] = "1"
    env["ERK_WORKTREE_NAME"] = worktree_path.name

    # Print welcome message
    welcome_msg = format_subshell_welcome_message(worktree_path, branch)
    click.echo(welcome_msg)
    click.echo()

    # Build shell invocation
    # We use shell -i to get an interactive shell with user's configs
    # Then run Claude as the first command
    if shell_name in ("bash", "zsh", "sh"):
        # For bash/zsh/sh, use -i for interactive and -c to run initial command
        # After Claude exits, the shell remains interactive
        # Use exec to replace the subshell with bash -i after Claude
        shell_args = [
            user_shell,
            "-c",
            f"{claude_cmd_str}; exec {user_shell} -i",
        ]
    else:
        # For other shells, just run Claude then start interactive shell
        shell_args = [
            user_shell,
            "-c",
            f"{claude_cmd_str}; exec {user_shell}",
        ]

    # Intentionally omit check=True: We want to capture and return the exit code
    # from the subshell rather than raise an exception. The exit code propagates
    # to the caller (sys.exit in execute_interactive_mode) for proper status.
    result = subprocess.run(
        shell_args,
        cwd=worktree_path,
        env=env,
    )

    return result.returncode
