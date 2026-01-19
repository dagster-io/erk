"""Shell activation script generation for worktree environments.

This module provides utilities for generating shell scripts that activate
worktree environments by setting up virtual environments and loading .env files.

SPECULATIVE: activation-scripts (objective #4954)
This feature is speculative and may be removed. Set ENABLE_ACTIVATION_SCRIPTS
to False to disable. Grep for "SPECULATIVE: activation-scripts" to find all
related code.
"""

import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import click

from erk.core.display_utils import copy_to_clipboard_osc52
from erk_shared.output.output import user_output

# Mode for activation instructions output
# - "activate_only": Show only `source <path>` (for navigation commands)
# - "implement": Show `source <path> && erk implement` (default for prepare)
# - "implement_dangerous": Show `source <path> && erk implement --dangerous`
# - "implement_docker": Show `source <path> && erk implement --docker` (Docker isolation)
# - "implement_docker_dangerous": Show Docker mode with --dangerous (redundant but explicit)
ActivationMode = Literal[
    "activate_only",
    "implement",
    "implement_dangerous",
    "implement_docker",
    "implement_docker_dangerous",
]

# SPECULATIVE: activation-scripts - set to False to disable this feature
ENABLE_ACTIVATION_SCRIPTS = True


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


def write_worktree_activate_script(
    *,
    worktree_path: Path,
    post_create_commands: Sequence[str] | None,
) -> Path:
    """Write an activation script to .erk/bin/activate.sh in the worktree.

    The script will:
      - CD to the worktree root
      - Create .venv with `uv sync` if not present
      - Source `.venv/bin/activate` if present
      - Export variables from `.env` if present
      - Run post-create commands if provided

    Args:
        worktree_path: Path to the worktree directory
        post_create_commands: Optional sequence of shell commands to embed in the
            script. These run after venv activation and .env loading.

    Returns:
        Path to the written activation script (.erk/bin/activate.sh)
    """
    script_content = render_activation_script(
        worktree_path=worktree_path,
        target_subpath=None,
        post_cd_commands=post_create_commands,
        final_message='echo "Activated: $(pwd)"',
        comment="erk worktree activation script",
    )

    bin_dir = worktree_path / ".erk" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    script_path = bin_dir / "activate.sh"
    script_path.write_text(script_content, encoding="utf-8")

    return script_path


def ensure_worktree_activate_script(
    *,
    worktree_path: Path,
    post_create_commands: Sequence[str] | None,
) -> Path:
    """Ensure an activation script exists at .erk/bin/activate.sh.

    If the script doesn't exist, creates it. If it exists, returns
    the path without modifying it (idempotent for existing scripts).

    Args:
        worktree_path: Path to the worktree directory
        post_create_commands: Optional sequence of shell commands to embed in the
            script. Only used if creating a new script.

    Returns:
        Path to the activation script (.erk/bin/activate.sh)
    """
    script_path = worktree_path / ".erk" / "bin" / "activate.sh"

    if not script_path.exists():
        return write_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=post_create_commands,
        )

    return script_path


def print_activation_instructions(
    script_path: Path,
    *,
    source_branch: str | None,
    force: bool,
    mode: ActivationMode,
    copy: bool,
) -> None:
    """Print activation script instructions.

    Displays instructions for activating the worktree environment. Used after
    worktree creation or navigation to guide users through the opt-in shell
    integration workflow.

    When copy=True, the primary activation command is auto-copied to the
    clipboard via OSC 52 (supported by iTerm2, Kitty, Alacritty, WezTerm,
    and other modern terminals). Terminals without OSC 52 support will
    silently ignore the sequence.

    SPECULATIVE: activation-scripts (objective #4954)

    Args:
        script_path: Path to the activation script (.erk/bin/activate.sh)
        source_branch: If provided and force is True, shows delete command for this branch.
        force: If True and source_branch is provided, shows the delete hint.
        mode: What command to show and copy:
            - "activate_only": Just `source <path>` (for navigation commands)
            - "implement": `source <path> && erk implement` (default for prepare)
            - "implement_dangerous": Include --dangerous flag
            - "implement_docker": Include --docker flag (Docker isolation)
            - "implement_docker_dangerous": Include both flags
        copy: If True, copy the primary command to clipboard via OSC 52 and show hint.
    """
    source_cmd = f"source {script_path}"

    # If deleting current branch, make the delete command the primary command
    if source_branch is not None and force:
        primary_cmd = f"{source_cmd} && erk br delete {source_branch}"
        instruction = f"To activate and delete branch {source_branch}:"
    elif mode == "activate_only":
        primary_cmd = source_cmd
        instruction = "To activate the worktree environment:"
    elif mode == "implement_dangerous":
        primary_cmd = f"{source_cmd} && erk implement --dangerous"
        instruction = "To activate and start implementation (skip permissions):"
    elif mode == "implement_docker":
        primary_cmd = f"{source_cmd} && erk implement --docker"
        instruction = "To activate and start implementation (Docker isolation):"
    elif mode == "implement_docker_dangerous":
        primary_cmd = f"{source_cmd} && erk implement --docker --dangerous"
        instruction = "To activate and start implementation (Docker isolation):"
    else:  # mode == "implement"
        primary_cmd = f"{source_cmd} && erk implement"
        instruction = "To activate and start implementation:"

    user_output(f"\n{instruction}")
    if copy:
        clipboard_hint = click.style("(copied to clipboard)", dim=True)
        user_output(f"  {primary_cmd}  {clipboard_hint}")
        # Emit OSC 52 to copy the command to clipboard (invisible escape sequence)
        user_output(copy_to_clipboard_osc52(primary_cmd), nl=False)
    else:
        user_output(f"  {primary_cmd}")


def render_land_script() -> str:
    """Return shell script content for land.sh.

    The script wraps `erk land --script` to provide shell integration,
    allowing the command to navigate the shell after landing a PR.

    Uses process substitution with `cat` to read the temp file immediately,
    avoiding race conditions where the file might be deleted before sourcing.
    """
    return """#!/usr/bin/env bash
# erk land wrapper - source this script to land with shell integration
# Usage: source .erk/bin/land.sh [args...]
source <(cat "$(erk land --script "$@")")
"""


def ensure_land_script(worktree_path: Path) -> Path:
    """Ensure land.sh exists at .erk/bin/land.sh in the worktree.

    Creates the script if it doesn't exist. The script wraps
    `erk land --script` to provide shell integration.

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        Path to the land script (.erk/bin/land.sh)
    """
    bin_dir = worktree_path / ".erk" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    script_path = bin_dir / "land.sh"

    if not script_path.exists():
        script_path.write_text(render_land_script(), encoding="utf-8")

    return script_path


def print_temp_script_instructions(
    script_path: Path,
    *,
    instruction: str,
    copy: bool,
) -> None:
    """Print instructions for sourcing a temporary execution script.

    Unlike print_activation_instructions() which is for persistent worktree
    activation scripts at .erk/bin/activate.sh, this is for one-time execution
    scripts (like land's deferred execution script) that contain specific state.

    When copy=True, the source command is auto-copied to the clipboard via OSC 52
    (supported by iTerm2, Kitty, Alacritty, WezTerm, and other modern terminals).

    Args:
        script_path: Path to the temporary script to source
        instruction: Message to show before the command (e.g., "To land the PR:")
        copy: If True, copy the source command to clipboard via OSC 52
    """
    source_cmd = f"source {script_path}"

    user_output(f"\n{instruction}")
    if copy:
        clipboard_hint = click.style("(copied to clipboard)", dim=True)
        user_output(f"  {source_cmd}  {clipboard_hint}")
        user_output(copy_to_clipboard_osc52(source_cmd), nl=False)
    else:
        user_output(f"  {source_cmd}")
