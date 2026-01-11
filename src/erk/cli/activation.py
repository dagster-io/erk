"""Shell activation script generation for worktree environments.

This module provides utilities for generating shell scripts that activate
worktree environments by setting up virtual environments and loading .env files.
"""

import shlex
from collections.abc import Sequence
from pathlib import Path


def _render_logging_helper() -> str:
    """Return shell helper functions for transparency logging.

    These helpers handle ERK_QUIET and ERK_VERBOSE environment variables
    to control output verbosity during worktree activation.

    Normal mode (default): Shows brief progress indicators
    Quiet mode (ERK_QUIET=1): Suppresses transparency output (errors still shown)
    Verbose mode (ERK_VERBOSE=1): Shows full details with paths
    """
    return """# Transparency logging helper
__erk_log() {
  [ -n "$ERK_QUIET" ] && return
  local prefix="$1" msg="$2"
  if [ -t 2 ]; then
    printf '\\033[0;36m%s\\033[0m %s\\n' "$prefix" "$msg" >&2
  else
    printf '%s %s\\n' "$prefix" "$msg" >&2
  fi
}
__erk_log_verbose() {
  [ -z "$ERK_VERBOSE" ] && return
  __erk_log "$1" "$2"
}"""


def render_activation_script(
    *,
    worktree_path: Path,
    target_subpath: Path | None,
    post_cd_commands: Sequence[str] | None,
    final_message: str,
    comment: str,
) -> str:
    """Return shell code that activates a worktree's venv and .env.

    The script:
      - cds into the worktree (optionally to a subpath within it)
      - creates .venv with `uv sync` if not present
      - sources `.venv/bin/activate` if present
      - exports variables from `.env` if present
      - runs optional post-activation commands
    Works in bash and zsh.

    Args:
        worktree_path: Path to the worktree directory
        target_subpath: Optional relative path within the worktree to cd to.
            If the subpath doesn't exist, a warning is shown and the script
            falls back to the worktree root.
        post_cd_commands: Optional sequence of shell commands to run after venv
            activation, before final message.
            Pass None if no post-cd commands are needed.
        final_message: Shell command for final echo message
        comment: Comment line for script identification

    Returns:
        Shell script as a string with newlines

    Example:
        >>> script = render_activation_script(
        ...     worktree_path=Path("/path/to/worktree"),
        ...     target_subpath=Path("src/lib"),
        ...     post_cd_commands=None,
        ...     final_message='echo "Ready: $(pwd)"',
        ...     comment="work activate-script",
        ... )
    """
    wt = shlex.quote(str(worktree_path))
    venv_dir = shlex.quote(str(worktree_path / ".venv"))
    venv_activate = shlex.quote(str(worktree_path / ".venv" / "bin" / "activate"))

    # Generate the cd command with optional subpath handling
    if target_subpath is not None:
        subpath_quoted = shlex.quote(str(target_subpath))
        # Check if subpath exists in target worktree, fall back to root with warning
        cd_command = f"""__erk_log "->" "cd {worktree_path}"
cd {wt}
# Try to preserve relative directory position
if [ -d {subpath_quoted} ]; then
  cd {subpath_quoted}
else
  echo "Warning: '{target_subpath}' doesn't exist in target, using worktree root" >&2
fi"""
    else:
        cd_command = f"""__erk_log "->" "cd {worktree_path}"
cd {wt}"""

    logging_helper = _render_logging_helper()

    # Build optional post-activation commands section
    post_activation_section = ""
    if post_cd_commands:
        post_activation_section = (
            "# Post-activation commands\n" + "\n".join(post_cd_commands) + "\n"
        )

    return f"""# {comment}
{logging_helper}
{cd_command}
# Unset VIRTUAL_ENV to avoid conflicts with previous activations
unset VIRTUAL_ENV
# Create venv if it doesn't exist
if [ ! -d {venv_dir} ]; then
  echo 'Creating virtual environment with uv sync...'
  uv sync
fi
if [ -f {venv_activate} ]; then
  . {venv_activate}
  __py_ver=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
  __erk_log "->" "Activating venv: {worktree_path / ".venv"} ($__py_ver)"
fi
# Load .env into the environment (allexport)
set -a
if [ -f ./.env ]; then
  __erk_log "->" "Loading .env"
  . ./.env
fi
set +a
{post_activation_section}# Optional: show where we are
{final_message}
"""
