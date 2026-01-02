#!/usr/bin/env python3
"""Exit Plan Mode Hook.

Prompts user before exiting plan mode when a plan exists. This hook intercepts
the ExitPlanMode tool via PreToolUse lifecycle to ask whether to save to GitHub
or implement immediately.

Exit codes:
    0: Success (allow exit - no plan, implement-now signal present, or no session)
    2: Block (plan exists, no implement-now signal - prompt user)

This command is invoked via:
    erk exec exit-plan-mode-hook

Signal File State Machine
=========================

This hook uses signal files in .erk/scratch/sessions/<session-id>/ for state management.
Signal files are self-describing: their names indicate their purpose and their contents
explain their effect.

Signal Files:
    exit-plan-mode-hook.implement-now.signal
        Created by: Agent (when user chooses "Implement now")
        Effect: Next ExitPlanMode call is ALLOWED (exit plan mode, proceed to implementation)
        Lifecycle: Deleted after being read by next hook invocation

    exit-plan-mode-hook.plan-saved.signal
        Created by: /erk:plan-save command
        Effect: Next ExitPlanMode call is BLOCKED (remain in plan mode, session complete)
        Lifecycle: Deleted after being read by next hook invocation

    incremental-plan.signal
        Created by: /local:incremental-plan-mode command (via agent creating signal file)
        Effect: Next ExitPlanMode call is ALLOWED, skipping the save prompt entirely
        Lifecycle: Deleted after being read by next hook invocation
        Purpose: Streamlines "plan → implement → submit" loop for PR iteration

State Transitions:
    1. No signal files + plan exists → BLOCK with prompt
    2. implement-now signal exists → ALLOW (delete signal)
    3. incremental-plan signal exists → ALLOW (delete signal, skip save prompt)
    4. plan-saved signal exists → BLOCK with "session complete" message (delete signal)
"""

import subprocess
import sys
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

from erk.hooks.decorators import HookContext, hook_command
from erk_shared.extraction.local_plans import extract_slugs_from_session
from erk_shared.scratch.plan_snapshots import snapshot_plan_for_session
from erk_shared.scratch.scratch import get_scratch_dir

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
    implement_now_signal_exists: bool
    plan_saved_signal_exists: bool
    incremental_plan_signal_exists: bool
    plan_file_path: Path | None  # Path to plan file if exists, None otherwise
    current_branch: str | None


@dataclass(frozen=True)
class HookOutput:
    """Decision result from pure logic."""

    action: ExitAction
    message: str
    delete_implement_now_signal: bool = False
    delete_plan_saved_signal: bool = False
    delete_incremental_plan_signal: bool = False


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
            "  1. Run /erk:plan-save",
            "  2. STOP - Do NOT call ExitPlanMode. The plan-save command handles everything.",
            "     Stay in plan mode and let the user exit manually if desired.",
            "",
            "If user chooses 'Implement now':",
            "  1. Create implement-now signal:",
            f"     mkdir -p .erk/scratch/sessions/{session_id} && "
            f"touch .erk/scratch/sessions/{session_id}/exit-plan-mode-hook.implement-now.signal",
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

    # Implement-now signal present (user chose "Implement now")
    if hook_input.implement_now_signal_exists:
        return HookOutput(
            ExitAction.ALLOW,
            "Implement-now signal found, allowing exit",
            delete_implement_now_signal=True,
        )

    # Incremental-plan signal present (session started via /local:incremental-plan-mode)
    # Skip the "save as GitHub issue?" prompt and proceed directly to implementation
    if hook_input.incremental_plan_signal_exists:
        return HookOutput(
            ExitAction.ALLOW,
            "Incremental-plan mode: skipping save prompt, proceeding to implementation",
            delete_incremental_plan_signal=True,
        )

    # Plan-saved signal present (user chose "Save to GitHub")
    if hook_input.plan_saved_signal_exists:
        return HookOutput(
            ExitAction.BLOCK,
            "✅ Plan already saved to GitHub. Session complete - no further action needed.",
            delete_plan_saved_signal=True,
        )

    # No plan file
    if hook_input.plan_file_path is None:
        return HookOutput(
            ExitAction.ALLOW,
            "No plan file found for this session, allowing exit",
        )

    # Plan exists, no implement-now signal - block and instruct
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


def _get_implement_now_signal_path(session_id: str, repo_root: Path) -> Path:
    """Get implement-now signal path in .erk/scratch/sessions/<session_id>/.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to implement-now signal file
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    return scratch_dir / "exit-plan-mode-hook.implement-now.signal"


def _get_plan_saved_signal_path(session_id: str, repo_root: Path) -> Path:
    """Get plan-saved signal path in .erk/scratch/sessions/<session_id>/.

    The plan-saved signal indicates the plan was already saved to GitHub,
    so exit should proceed without triggering implementation.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to plan-saved signal file
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    return scratch_dir / "exit-plan-mode-hook.plan-saved.signal"


def _get_incremental_plan_signal_path(session_id: str, repo_root: Path) -> Path:
    """Get incremental-plan signal path in .erk/scratch/sessions/<session_id>/.

    The incremental-plan signal indicates this session was started via
    /local:incremental-plan, so we should skip the "save as GitHub issue?"
    prompt and proceed directly to implementation.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to incremental-plan signal file
    """
    return get_scratch_dir(session_id, repo_root=repo_root) / "incremental-plan.signal"


def _find_session_plan(session_id: str, repo_root: Path) -> Path | None:
    """Find plan file for the given session using slug lookup.

    Args:
        session_id: The session ID to search for
        repo_root: Path to the git repository root

    Returns:
        Path to plan file if found, None otherwise
    """
    plans_dir = Path.home() / ".claude" / "plans"
    if not plans_dir.exists():
        return None

    slugs = extract_slugs_from_session(session_id, cwd_hint=str(repo_root))
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


def _gather_inputs(session_id: str | None, repo_root: Path) -> HookInput:
    """Gather all inputs from environment. All I/O happens here.

    Args:
        session_id: Claude session ID from hook_ctx, or None if not available.
        repo_root: Path to the git repository root.

    Returns:
        HookInput with all gathered state.
    """
    # Determine signal existence
    implement_now_signal_exists = False
    plan_saved_signal_exists = False
    incremental_plan_signal_exists = False
    if session_id is not None:
        implement_now_signal_exists = _get_implement_now_signal_path(session_id, repo_root).exists()
        plan_saved_signal_exists = _get_plan_saved_signal_path(session_id, repo_root).exists()
        signal_path = _get_incremental_plan_signal_path(session_id, repo_root)
        incremental_plan_signal_exists = signal_path.exists()

    # Find plan file path (None if doesn't exist)
    plan_file_path: Path | None = None
    if session_id is not None:
        plan_file_path = _find_session_plan(session_id, repo_root)

    # Get current branch (only if we need to show the blocking message)
    current_branch = None
    needs_blocking_message = (
        session_id is not None
        and plan_file_path is not None
        and not implement_now_signal_exists
        and not incremental_plan_signal_exists
        and not plan_saved_signal_exists
    )
    if needs_blocking_message:
        current_branch = _get_current_branch_within_hook()

    return HookInput(
        session_id=session_id,
        github_planning_enabled=_is_github_planning_enabled(),
        implement_now_signal_exists=implement_now_signal_exists,
        plan_saved_signal_exists=plan_saved_signal_exists,
        incremental_plan_signal_exists=incremental_plan_signal_exists,
        plan_file_path=plan_file_path,
        current_branch=current_branch,
    )


def _execute_result(result: HookOutput, hook_input: HookInput, repo_root: Path) -> None:
    """Execute the decision result. All I/O happens here."""
    session_id = hook_input.session_id

    if result.delete_implement_now_signal and session_id:
        _get_implement_now_signal_path(session_id, repo_root).unlink()

    if result.delete_plan_saved_signal and session_id:
        _get_plan_saved_signal_path(session_id, repo_root).unlink()

    if result.delete_incremental_plan_signal and session_id:
        _get_incremental_plan_signal_path(session_id, repo_root).unlink()

    # Snapshot plan whenever a plan exists and user made a decision
    # (implement-now or plan-saved, but NOT when blocking to prompt)
    user_made_decision = result.delete_implement_now_signal or result.delete_plan_saved_signal
    if hook_input.plan_file_path is not None and session_id is not None and user_made_decision:
        snapshot_plan_for_session(
            session_id=session_id,
            plan_file_path=hook_input.plan_file_path,
            cwd_hint=str(repo_root),
        )

    if result.message:
        click.echo(result.message, err=True)

    sys.exit(result.action.value)


@hook_command(name="exit-plan-mode-hook")
def exit_plan_mode_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """Prompt user about plan saving when ExitPlanMode is called.

    This PreToolUse hook intercepts ExitPlanMode calls to ask the user
    whether to save the plan to GitHub or implement immediately.

    Exit codes:
        0: Success - allow exit (no plan, skip marker, or no session)
        2: Block - plan exists, prompt user for action
    """
    # Scope check: only run in erk-managed projects
    if not hook_ctx.is_erk_project:
        return

    # Gather all inputs (I/O layer)
    hook_input = _gather_inputs(hook_ctx.session_id, hook_ctx.repo_root)

    # Pure decision logic (no I/O)
    result = determine_exit_action(hook_input)

    # Execute result (I/O layer)
    _execute_result(result, hook_input, hook_ctx.repo_root)


if __name__ == "__main__":
    exit_plan_mode_hook()
