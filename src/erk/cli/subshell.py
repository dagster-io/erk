"""Subshell spawning for worktree activation without shell integration.

This module provides functionality to spawn a subshell in a worktree directory
when shell integration is not active. The subshell can automatically launch
Claude for implementation.
"""

import os
import subprocess
from pathlib import Path


def is_shell_integration_active() -> bool:
    """Check if ERK_SHELL env var is set (indicates shell wrapper is active).

    Returns:
        True if shell integration is active, False otherwise.
    """
    return os.environ.get("ERK_SHELL") is not None


def detect_user_shell() -> str:
    """Return $SHELL or default to /bin/sh.

    Returns:
        Path to the user's shell executable.
    """
    return os.environ.get("SHELL", "/bin/sh")


def format_subshell_welcome_message(
    *,
    worktree_path: Path,
    branch: str,
) -> str:
    """Format welcome banner with prompt customization hint.

    Args:
        worktree_path: Path to the worktree directory.
        branch: Branch name for the worktree.

    Returns:
        Formatted welcome message string.
    """
    border = "━" * 60
    return f"""{border}
You are now in a subshell at: {worktree_path}
Branch: {branch}

To switch directories and stay in the same shell, install shell integration:
  erk init --shell

To show this in your prompt, add to ~/.bashrc or ~/.zshrc:
  if [ -n "$ERK_SUBSHELL" ]; then
    PS1="(erk:$ERK_WORKTREE_NAME) $PS1"
  fi

Type 'exit' to return to your original directory.
{border}"""


def _build_shell_init_command(
    *,
    shell: str,
    claude_command: str,
    dangerous: bool,
    model: str | None,
) -> str:
    """Build the shell initialization command to run Claude.

    Args:
        shell: Path to the shell executable.
        claude_command: The slash command to execute in Claude.
        dangerous: Whether to skip permission prompts.
        model: Optional model name (haiku, sonnet, opus).

    Returns:
        Shell command string to execute on shell startup.
    """
    # Build Claude CLI arguments
    args = ["claude", "--permission-mode", "acceptEdits"]
    if dangerous:
        args.append("--dangerously-skip-permissions")
    if model is not None:
        args.extend(["--model", model])
    args.append(claude_command)

    # Quote each argument for shell safety
    quoted_args = " ".join(f'"{arg}"' for arg in args)

    # Build the init command based on shell type
    shell_name = Path(shell).name

    if shell_name in ("bash", "sh"):
        # For bash: use --init-file with a temporary script approach
        # We'll use -c with exec to run Claude, then drop into interactive shell
        return quoted_args
    elif shell_name == "zsh":
        # For zsh: similar approach
        return quoted_args
    elif shell_name == "fish":
        # For fish: use -C for startup command
        return quoted_args
    else:
        # Generic fallback
        return quoted_args


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
        worktree_path: Path to the worktree directory.
        branch: Branch name for display.
        claude_command: The slash command to execute in Claude.
        dangerous: Whether to skip permission prompts.
        model: Optional model name (haiku, sonnet, opus).
        shell: Optional shell path override (uses $SHELL if None).

    Returns:
        Exit code from the subshell.
    """
    import sys

    # Determine shell to use
    user_shell = shell if shell is not None else detect_user_shell()
    shell_name = Path(user_shell).name

    # Build environment with subshell markers
    env = os.environ.copy()
    env["ERK_SUBSHELL"] = "1"
    env["ERK_WORKTREE_NAME"] = worktree_path.name

    # Print welcome message
    welcome = format_subshell_welcome_message(
        worktree_path=worktree_path,
        branch=branch,
    )
    print(welcome, file=sys.stderr)

    # Build Claude command
    claude_args = _build_shell_init_command(
        shell=user_shell,
        claude_command=claude_command,
        dangerous=dangerous,
        model=model,
    )

    # Strategy: Run Claude first, then drop into interactive shell
    # This way user can continue working after Claude exits
    if shell_name in ("bash", "sh"):
        # Bash: Run Claude, then exec interactive shell
        # The -i flag makes it interactive
        shell_cmd = f"{claude_args}; exec {user_shell} -i"
        result = subprocess.run(
            [user_shell, "-c", shell_cmd],
            cwd=worktree_path,
            env=env,
        )
    elif shell_name == "zsh":
        # Zsh: Similar approach
        shell_cmd = f"{claude_args}; exec {user_shell} -i"
        result = subprocess.run(
            [user_shell, "-c", shell_cmd],
            cwd=worktree_path,
            env=env,
        )
    elif shell_name == "fish":
        # Fish: Use -C for command, but fish doesn't have -c with exec the same way
        shell_cmd = f"{claude_args}; exec {user_shell}"
        result = subprocess.run(
            [user_shell, "-c", shell_cmd],
            cwd=worktree_path,
            env=env,
        )
    else:
        # Generic fallback: just run Claude, then interactive shell
        shell_cmd = f"{claude_args}; exec {user_shell}"
        result = subprocess.run(
            [user_shell, "-c", shell_cmd],
            cwd=worktree_path,
            env=env,
        )

    return result.returncode
