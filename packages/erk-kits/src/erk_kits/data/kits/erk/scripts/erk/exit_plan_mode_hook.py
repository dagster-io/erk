#!/usr/bin/env python3
"""Exit Plan Mode Hook.

Prompts user before exiting plan mode when a plan exists. This hook intercepts
the ExitPlanMode tool via PreToolUse lifecycle to ask whether to save to GitHub
or implement immediately.

Exit codes:
    0: Success (allow exit - no plan, skip marker present, or no session)
    2: Block (plan exists, no skip marker - prompt user)

This command is invoked via:
    erk kit exec erk exit-plan-mode-hook
"""

import json
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

from erk.kits.hooks.decorators import logged_hook, project_scoped
from erk_kits.data.kits.erk.session_plan_extractor import extract_slugs_from_session

# ============================================================================
# Data Classes for Pure Logic
# ============================================================================


class ExitAction(Enum):
    """Exit action for the hook."""

    ALLOW = 0  # Exit code 0 - allow ExitPlanMode
    BLOCK = 2  # Exit code 2 - block ExitPlanMode


@dataclass(frozen=True)
class HookInput:
    """All inputs needed for decision logic."""

    session_id: str | None
    github_planning_enabled: bool
    skip_marker_exists: bool
    saved_marker_exists: bool
    plan_file_path: Path | None  # Path to plan file if exists, None otherwise
    current_branch: str | None


@dataclass(frozen=True)
class HookOutput:
    """Decision result from pure logic."""

    action: ExitAction
    message: str
    delete_skip_marker: bool = False
    delete_saved_marker: bool = False


# ============================================================================
# Pure Functions (no I/O, fully testable without mocking)
# ============================================================================


def build_blocking_message(
    session_id: str,
    current_branch: str | None,
    plan_file_path: Path | None,
) -> str:
    """Build the blocking message with AskUserQuestion instructions.

    Pure function - string building only. Testable without mocking.
    """
    lines = [
        "PLAN SAVE PROMPT",
        "",
        "A plan exists for this session but has not been saved.",
        "",
        "Use AskUserQuestion to ask the user:",
        '  "Would you like to save this plan, or implement now?"',
        "",
        "IMPORTANT: Present options in this exact order:",
        '  1. "Save the plan" (Recommended) - Save plan as a GitHub issue and stop. '
        "Does NOT proceed to implementation.",
        '  2. "Implement now" - Skip saving, proceed directly to implementation '
        "(edits code in the current worktree).",
        '  3. "View/Edit the plan" - Open plan in editor to review or modify before deciding.',
    ]

    if current_branch in ("master", "main"):
        lines.extend(
            [
                "",
                f"⚠️  WARNING: Currently on '{current_branch}'. "
                "We strongly discourage editing directly on the trunk branch. "
                "Consider saving the plan and implementing in a dedicated worktree instead.",
            ]
        )

    lines.extend(
        [
            "",
            "If user chooses 'Save the plan':",
            "  1. Run /erk:save-plan",
            "  2. STOP - Do NOT call ExitPlanMode. The save-plan command handles everything.",
            "     Stay in plan mode and let the user exit manually if desired.",
            "",
            "If user chooses 'Implement now':",
            "  1. Create skip marker:",
            f"     mkdir -p .erk/scratch/sessions/{session_id} && "
            f"touch .erk/scratch/sessions/{session_id}/skip-plan-save",
            "  2. Call ExitPlanMode",
        ]
    )

    if plan_file_path is not None:
        lines.extend(
            [
                "",
                "If user chooses 'View/Edit the plan':",
                f"  1. Run: ${{EDITOR:-code}} {plan_file_path}",
                "  2. After user confirms they're done editing, ask the same question again",
                "     (loop until user chooses Save or Implement)",
            ]
        )

    return "\n".join(lines)


def determine_exit_action(hook_input: HookInput) -> HookOutput:
    """Determine what action to take based on inputs.

    Pure function - all decision logic, no I/O. Testable without mocking!
    """
    # Early exit if github_planning is disabled
    if not hook_input.github_planning_enabled:
        return HookOutput(ExitAction.ALLOW, "")

    # No session context
    if hook_input.session_id is None:
        return HookOutput(ExitAction.ALLOW, "No session context available, allowing exit")

    # Skip marker present (user chose "Implement now")
    if hook_input.skip_marker_exists:
        return HookOutput(
            ExitAction.ALLOW,
            "Skip marker found, allowing exit",
            delete_skip_marker=True,
        )

    # Saved marker present (user chose "Save to GitHub")
    if hook_input.saved_marker_exists:
        return HookOutput(
            ExitAction.BLOCK,
            "✅ Plan already saved to GitHub. Session complete - no further action needed.",
            delete_saved_marker=True,
        )

    # No plan file
    if hook_input.plan_file_path is None:
        return HookOutput(
            ExitAction.ALLOW,
            "No plan file found for this session, allowing exit",
        )

    # Plan exists, no skip marker - block and instruct
    return HookOutput(
        ExitAction.BLOCK,
        build_blocking_message(
            hook_input.session_id,
            hook_input.current_branch,
            hook_input.plan_file_path,
        ),
    )


# ============================================================================
# I/O Helper Functions
# ============================================================================


def _is_github_planning_enabled() -> bool:
    """Check if github_planning is enabled in ~/.erk/config.toml.

    Returns True (enabled) if config doesn't exist or flag is missing.
    """
    config_path = Path.home() / ".erk" / "config.toml"
    if not config_path.exists():
        return True  # Default enabled

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return bool(data.get("github_planning", True))


def _get_session_id_from_stdin() -> str | None:
    """Read session ID from stdin if available."""
    if sys.stdin.isatty():
        return None
    try:
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            context = json.loads(stdin_data)
            return context.get("session_id")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _get_scratch_dir(session_id: str) -> Path | None:
    """Get scratch directory path in .erk/scratch/sessions/<session_id>/.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to scratch directory, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root / ".erk" / "scratch" / "sessions" / session_id
    except subprocess.CalledProcessError:
        return None


def _get_skip_marker_path(session_id: str) -> Path | None:
    """Get skip marker path in .erk/scratch/sessions/<session_id>/.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to skip marker file, or None if not in a git repo
    """
    scratch_dir = _get_scratch_dir(session_id)
    if scratch_dir is None:
        return None
    return scratch_dir / "skip-plan-save"


def _get_saved_marker_path(session_id: str) -> Path | None:
    """Get saved marker path in .erk/scratch/sessions/<session_id>/.

    The saved marker indicates the plan was already saved to GitHub,
    so exit should proceed without triggering implementation.

    Args:
        session_id: The session ID to build the path for

    Returns:
        Path to saved marker file, or None if not in a git repo
    """
    scratch_dir = _get_scratch_dir(session_id)
    if scratch_dir is None:
        return None
    return scratch_dir / "plan-saved-to-github"


def _find_session_plan(session_id: str) -> Path | None:
    """Find plan file for the given session using slug lookup.

    Args:
        session_id: The session ID to search for

    Returns:
        Path to plan file if found, None otherwise
    """
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return None

    cwd = os.getcwd()
    slugs = extract_slugs_from_session(session_id, cwd_hint=cwd)
    if not slugs:
        return None

    # Use most recent slug (last in list)
    slug = slugs[-1]
    plan_file = plans_dir / f"{slug}.md"

    if plan_file.exists() and plan_file.is_file():
        return plan_file

    return None


def _get_current_branch_within_hook() -> str | None:
    """Get the current git branch name.

    Returns:
        Branch name, or None if detached HEAD
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ============================================================================
# Main Hook Entry Point
# ============================================================================


def _gather_inputs() -> HookInput:
    """Gather all inputs from environment. All I/O happens here."""
    session_id = _get_session_id_from_stdin()

    # Determine marker existence
    skip_marker_exists = False
    saved_marker_exists = False
    if session_id:
        skip_marker = _get_skip_marker_path(session_id)
        skip_marker_exists = skip_marker is not None and skip_marker.exists()
        saved_marker = _get_saved_marker_path(session_id)
        saved_marker_exists = saved_marker is not None and saved_marker.exists()

    # Find plan file path (None if doesn't exist)
    plan_file_path: Path | None = None
    if session_id:
        plan_file_path = _find_session_plan(session_id)

    # Get current branch (only if we need to show the blocking message)
    current_branch = None
    needs_blocking_message = (
        session_id
        and plan_file_path is not None
        and not skip_marker_exists
        and not saved_marker_exists
    )
    if needs_blocking_message:
        current_branch = _get_current_branch_within_hook()

    return HookInput(
        session_id=session_id,
        github_planning_enabled=_is_github_planning_enabled(),
        skip_marker_exists=skip_marker_exists,
        saved_marker_exists=saved_marker_exists,
        plan_file_path=plan_file_path,
        current_branch=current_branch,
    )


def _execute_result(result: HookOutput, session_id: str | None) -> None:
    """Execute the decision result. All I/O happens here."""
    if result.delete_skip_marker and session_id:
        skip_marker = _get_skip_marker_path(session_id)
        if skip_marker:
            skip_marker.unlink()

    if result.delete_saved_marker and session_id:
        saved_marker = _get_saved_marker_path(session_id)
        if saved_marker:
            saved_marker.unlink()

    if result.message:
        click.echo(result.message, err=True)

    sys.exit(result.action.value)


@click.command(name="exit-plan-mode-hook")
@logged_hook
@project_scoped
def exit_plan_mode_hook() -> None:
    """Prompt user about plan saving when ExitPlanMode is called.

    This PreToolUse hook intercepts ExitPlanMode calls to ask the user
    whether to save the plan to GitHub or implement immediately.

    Exit codes:
        0: Success - allow exit (no plan, skip marker, or no session)
        2: Block - plan exists, prompt user for action
    """
    # Gather all inputs (I/O layer)
    hook_input = _gather_inputs()

    # Pure decision logic (no I/O)
    result = determine_exit_action(hook_input)

    # Execute result (I/O layer)
    _execute_result(result, hook_input.session_id)


if __name__ == "__main__":
    exit_plan_mode_hook()
