#!/usr/bin/env python3
"""Exit Plan Mode Hook.

Prompts user before exiting plan mode when a plan exists. This hook intercepts
the ExitPlanMode tool via PreToolUse lifecycle to ask whether to save to GitHub
or implement immediately.

Exit codes:
    0: Success (allow exit - no plan, implement-now marker present, or no session)
    2: Block (plan exists, no implement-now marker - prompt user)

This command is invoked via:
    erk exec exit-plan-mode-hook

Marker File State Machine
=========================

This hook uses marker files in .erk/scratch/sessions/<session-id>/ for state management.
Marker files are self-describing: their names indicate their purpose and their contents
explain their effect.

Marker Files:
    exit-plan-mode-hook.implement-now.marker
        Created by: Agent (when user chooses "Implement now")
        Effect: Next ExitPlanMode call is ALLOWED (exit plan mode, proceed to implementation)
        Lifecycle: Deleted after being read by next hook invocation

    exit-plan-mode-hook.plan-saved.marker
        Created by: /erk:plan-save command
        Effect: Next ExitPlanMode call is BLOCKED (remain in plan mode, session complete)
        Lifecycle: Deleted after being read by next hook invocation

    incremental-plan.marker
        Created by: /local:incremental-plan-mode command (via `erk exec marker create --session-id`)
        Effect: Next ExitPlanMode call is ALLOWED, skipping the save prompt entirely
        Lifecycle: Deleted after being read by next hook invocation
        Purpose: Streamlines "plan → implement → submit" loop for PR iteration

State Transitions:
    1. No marker files + plan exists → BLOCK with prompt
    2. implement-now marker exists → ALLOW (delete marker)
    3. incremental-plan marker exists → ALLOW (delete marker, skip save prompt)
    4. plan-saved marker exists → BLOCK with "session complete" message (delete marker)
"""

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Self

import click

from erk.hooks.decorators import HookContext, hook_command
from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.factory import create_branch_manager
from erk_shared.extraction.claude_installation.abc import ClaudeInstallation
from erk_shared.git.abc import Git
from erk_shared.scratch.plan_snapshots import snapshot_plan_for_session
from erk_shared.scratch.scratch import get_scratch_dir

# Known terminal-based editors that cannot run inside Claude Code
TERMINAL_EDITORS = frozenset(
    {"vim", "vi", "nvim", "nano", "emacs", "pico", "ne", "micro", "jed", "mcedit", "joe", "ed"}
)


def abbreviate_for_header(current_branch: str | None) -> str:
    """Abbreviate branch name to fit in 12-char header for AskUserQuestion.

    Args:
        current_branch: Current git branch name, or None.

    Returns:
        Abbreviated header string, max 12 characters.
        Examples:
        - "P4535-add-feature" -> "br:P4535-ad" (11 chars)
        - "feature-x" -> "br:feature-x" (12 chars)
        - None -> "Plan Action"
    """
    if current_branch is None:
        return "Plan Action"
    # Truncate if too long: "br:" + 9 chars = 12 max
    abbreviated = current_branch
    if len(abbreviated) > 9:
        abbreviated = abbreviated[:9]
    return f"br:{abbreviated}"


def is_terminal_editor(editor: str | None) -> bool:
    """Check if editor is a terminal-based (TUI) editor.

    Terminal editors like vim cannot run inside Claude Code because they
    need exclusive terminal control which conflicts with Claude's UI.

    Args:
        editor: The EDITOR environment variable value, or None.

    Returns:
        True if editor is a known terminal-based editor.
    """
    if editor is None:
        return False
    # Extract basename in case of full path like /usr/bin/vim
    editor_name = Path(editor).name
    return editor_name in TERMINAL_EDITORS


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
    implement_now_marker_exists: bool
    plan_saved_marker_exists: bool
    incremental_plan_marker_exists: bool
    objective_context_marker_exists: bool
    objective_issue: int | None  # Objective issue number if marker exists
    plan_file_path: Path | None  # Path to plan file if exists, None otherwise
    plan_title: str | None  # Title extracted from plan file for display
    current_branch: str | None
    worktree_name: str | None  # Directory name of current worktree
    pr_number: int | None  # PR number if exists for current branch
    plan_issue_number: int | None  # Issue number from .impl/issue.json
    editor: str | None  # Value of EDITOR env var for TUI detection

    @classmethod
    def for_test(
        cls,
        *,
        session_id: str | None = "test-session",
        github_planning_enabled: bool = True,
        implement_now_marker_exists: bool = False,
        plan_saved_marker_exists: bool = False,
        incremental_plan_marker_exists: bool = False,
        objective_context_marker_exists: bool = False,
        objective_issue: int | None = None,
        plan_file_path: Path | None = None,
        plan_title: str | None = None,
        current_branch: str | None = "feature-branch",
        worktree_name: str | None = None,
        pr_number: int | None = None,
        plan_issue_number: int | None = None,
        editor: str | None = None,
    ) -> Self:
        """Create a HookInput with test defaults.

        All fields have sensible defaults for testing:
        - session_id: "test-session"
        - github_planning_enabled: True
        - All marker exists flags: False
        - objective_issue: None
        - plan_file_path: None
        - plan_title: None
        - current_branch: "feature-branch"
        - worktree_name: None
        - pr_number: None
        - plan_issue_number: None
        - editor: None
        """
        return cls(
            session_id=session_id,
            github_planning_enabled=github_planning_enabled,
            implement_now_marker_exists=implement_now_marker_exists,
            plan_saved_marker_exists=plan_saved_marker_exists,
            incremental_plan_marker_exists=incremental_plan_marker_exists,
            objective_context_marker_exists=objective_context_marker_exists,
            objective_issue=objective_issue,
            plan_file_path=plan_file_path,
            plan_title=plan_title,
            current_branch=current_branch,
            worktree_name=worktree_name,
            pr_number=pr_number,
            plan_issue_number=plan_issue_number,
            editor=editor,
        )


@dataclass(frozen=True)
class HookOutput:
    """Decision result from pure logic."""

    action: ExitAction
    message: str
    delete_implement_now_marker: bool = False
    delete_plan_saved_marker: bool = False
    delete_incremental_plan_marker: bool = False
    delete_objective_context_marker: bool = False


# ============================================================================
# Pure Functions (no I/O, fully testable without mocking)
# ============================================================================


def extract_plan_title(plan_file_path: Path | None) -> str | None:
    """Extract title from plan file for display in menu.

    Pure function - only reads file content, no other I/O.

    Looks for:
    1. First H1 heading (# Title)
    2. Content after "## Task" section

    Returns None if file doesn't exist or no title found.
    """
    if plan_file_path is None or not plan_file_path.exists():
        return None

    text = plan_file_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Look for first H1 (skip generic titles)
    for line in lines[:10]:
        if line.startswith("# "):
            title = line[2:].strip()
            if title.lower() not in ("plan", "implementation plan"):
                return title

    # Look for ## Task section
    for i, line in enumerate(lines[:20]):
        if line.strip() == "## Task":
            for next_line in lines[i + 1 : i + 5]:
                if next_line.strip():
                    return next_line.strip()

    return None


def build_blocking_message(
    *,
    session_id: str,
    current_branch: str | None,
    plan_file_path: Path | None,
    objective_issue: int | None,
    plan_title: str | None,
    worktree_name: str | None,
    pr_number: int | None,
    plan_issue_number: int | None,
    editor: str | None,
) -> str:
    """Build the blocking message with AskUserQuestion instructions.

    Pure function - string building only. Testable without mocking.

    Args:
        session_id: Claude session ID for marker creation commands.
        current_branch: Current git branch name.
        plan_file_path: Path to the plan file, if it exists.
        objective_issue: Objective issue number, if this plan is part of an objective.
        plan_title: Title extracted from plan file, if available.
        worktree_name: Directory name of current worktree.
        pr_number: PR number if exists for current branch.
        plan_issue_number: Issue number from .impl/issue.json.
        editor: Value of EDITOR env var for TUI detection.
    """
    # Build context lines for the question
    context_lines: list[str] = []

    # First line: title
    if plan_title:
        context_lines.append(f"📋 {plan_title}")

    # Second line: statusline-style context
    statusline_parts: list[str] = []
    if worktree_name:
        statusline_parts.append(f"wt:{worktree_name}")
    if current_branch:
        statusline_parts.append(f"br:{current_branch}")
    if pr_number is not None:
        statusline_parts.append(f"pr:#{pr_number}")
    if plan_issue_number is not None:
        statusline_parts.append(f"plan:#{plan_issue_number}")

    if statusline_parts:
        statusline = " ".join(f"({part})" for part in statusline_parts)
        context_lines.append(f"Current context: {statusline}")

    context_block = "\n".join(context_lines)

    # Build the question text
    if context_block:
        question_text = f"{context_block}\\n\\nWhat would you like to do with this plan?"
    else:
        question_text = "What would you like to do with this plan?"

    # Build header for AskUserQuestion (max 12 chars)
    header = abbreviate_for_header(current_branch)

    lines = [
        "PLAN SAVE PROMPT",
        "",
        "A plan exists for this session but has not been saved.",
        "",
        "Use AskUserQuestion to ask the user:",
        f'  question: "{question_text}"',
        f'  header: "{header}"',
        "",
        "IMPORTANT: Present options in this exact order:",
        '  1. "Save the plan" (Recommended) - Save plan as a GitHub issue and stop. '
        "Does NOT proceed to implementation.",
        '  2. "Do not save issue and implement here" - Skip saving, implement directly '
        "in current worktree (for small PR iterations that don't need issue tracking).",
        '  3. "Save plan and implement here" - Save to GitHub, then immediately '
        "implement (full workflow).",
        '  4. "View/Edit the plan" - Open plan in editor to review or modify before deciding.',
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

    # Build the save command with optional --objective-issue flag
    if objective_issue is not None:
        save_cmd = f"/erk:plan-save --objective-issue={objective_issue}"
    else:
        save_cmd = "/erk:plan-save"

    lines.extend(
        [
            "",
            "If user chooses 'Save the plan':",
            f"  1. Run {save_cmd}",
            "  2. STOP - Do NOT call ExitPlanMode. The plan-save command handles everything.",
            "     Stay in plan mode and let the user exit manually if desired.",
            "",
            "If user chooses 'Do not save issue and implement here':",
            "  1. Create implement-now marker (skip saving):",
            f"     erk exec marker create --session-id {session_id} \\",
            "       exit-plan-mode-hook.implement-now",
            "  2. Call ExitPlanMode",
            "  3. After exiting plan mode, implement the changes directly",
            "     (no issue tracking - this is for small PR iterations)",
            "",
            "If user chooses 'Save plan and implement here':",
            f"  1. Run {save_cmd}",
            "  2. After save completes, create implement-now marker:",
            f"     erk exec marker create --session-id {session_id} \\",
            "       exit-plan-mode-hook.implement-now",
            "  3. Call ExitPlanMode",
            "  4. After exiting plan mode, run /erk:system:impl-execute to execute implementation",
        ]
    )

    if plan_file_path is not None:
        if is_terminal_editor(editor):
            # TUI editors can't run inside Claude Code
            editor_name = Path(editor).name if editor else "your editor"
            lines.extend(
                [
                    "",
                    "If user chooses 'View/Edit the plan':",
                    f"  1. Tell user: '{editor_name} is a terminal-based editor that cannot",
                    "     run inside Claude Code. Please open the plan in a separate terminal:'",
                    f"     {editor} {plan_file_path}",
                    "  2. Wait for user to confirm they're done editing",
                    "  3. Ask the same question again (loop until Save/Implement/Incremental)",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "If user chooses 'View/Edit the plan':",
                    f"  1. Run: ${{EDITOR:-code}} {plan_file_path}",
                    "  2. After user confirms they're done editing, ask the same question again",
                    "     (loop until user chooses Save, Implement, or Incremental)",
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

    # Implement-now marker present (user chose "Implement now")
    if hook_input.implement_now_marker_exists:
        return HookOutput(
            ExitAction.ALLOW,
            "Implement-now marker found, allowing exit",
            delete_implement_now_marker=True,
            delete_objective_context_marker=hook_input.objective_context_marker_exists,
        )

    # Incremental-plan marker present (session started via /local:incremental-plan-mode)
    # Skip the "save as GitHub issue?" prompt and proceed directly to implementation
    if hook_input.incremental_plan_marker_exists:
        return HookOutput(
            ExitAction.ALLOW,
            "Incremental-plan mode: skipping save prompt, proceeding to implementation",
            delete_incremental_plan_marker=True,
        )

    # Plan-saved marker present (user chose "Save to GitHub")
    if hook_input.plan_saved_marker_exists:
        return HookOutput(
            ExitAction.BLOCK,
            "✅ Plan already saved to GitHub. Session complete - no further action needed.",
            delete_plan_saved_marker=True,
            delete_objective_context_marker=hook_input.objective_context_marker_exists,
        )

    # No plan file
    if hook_input.plan_file_path is None:
        return HookOutput(
            ExitAction.ALLOW,
            "No plan file found for this session, allowing exit",
        )

    # Plan exists, no implement-now marker - block and instruct
    return HookOutput(
        ExitAction.BLOCK,
        build_blocking_message(
            session_id=hook_input.session_id,
            current_branch=hook_input.current_branch,
            plan_file_path=hook_input.plan_file_path,
            objective_issue=hook_input.objective_issue,
            plan_title=hook_input.plan_title,
            worktree_name=hook_input.worktree_name,
            pr_number=hook_input.pr_number,
            plan_issue_number=hook_input.plan_issue_number,
            editor=hook_input.editor,
        ),
    )


# ============================================================================
# I/O Helper Functions
# ============================================================================


def _get_implement_now_marker_path(session_id: str, repo_root: Path) -> Path:
    """Get implement-now marker path in .erk/scratch/sessions/<session_id>/.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to implement-now marker file
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    return scratch_dir / "exit-plan-mode-hook.implement-now.marker"


def _get_plan_saved_marker_path(session_id: str, repo_root: Path) -> Path:
    """Get plan-saved marker path in .erk/scratch/sessions/<session_id>/.

    The plan-saved marker indicates the plan was already saved to GitHub,
    so exit should proceed without triggering implementation.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to plan-saved marker file
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    return scratch_dir / "exit-plan-mode-hook.plan-saved.marker"


def _get_incremental_plan_marker_path(session_id: str, repo_root: Path) -> Path:
    """Get incremental-plan marker path in .erk/scratch/sessions/<session_id>/.

    The incremental-plan marker indicates this session was started via
    /local:incremental-plan, so we should skip the "save as GitHub issue?"
    prompt and proceed directly to implementation.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to incremental-plan marker file
    """
    return get_scratch_dir(session_id, repo_root=repo_root) / "incremental-plan.marker"


def _get_objective_context_marker_path(session_id: str, repo_root: Path) -> Path:
    """Get objective-context marker path in .erk/scratch/sessions/<session_id>/.

    The objective-context marker stores the objective issue number when
    a plan is created via /erk:objective-create-plan. This allows the hook
    to suggest the correct --objective-issue flag in the save command.

    Args:
        session_id: The session ID to build the path for
        repo_root: Path to the git repository root

    Returns:
        Path to objective-context marker file
    """
    return get_scratch_dir(session_id, repo_root=repo_root) / "objective-context.marker"


def _read_objective_context(session_id: str, repo_root: Path) -> int | None:
    """Read objective issue number from marker, if present.

    Args:
        session_id: The session ID to look up
        repo_root: Path to the git repository root

    Returns:
        Objective issue number, or None if marker doesn't exist or is invalid.
    """
    marker_path = _get_objective_context_marker_path(session_id, repo_root)
    if not marker_path.exists():
        return None
    content = marker_path.read_text(encoding="utf-8").strip()
    if not content.isdigit():
        return None
    return int(content)


def _find_session_plan(
    session_id: str, repo_root: Path, claude_installation: ClaudeInstallation
) -> Path | None:
    """Find plan file for the given session using slug lookup.

    Args:
        session_id: The session ID to search for
        repo_root: Path to the git repository root
        claude_installation: Gateway to Claude installation data

    Returns:
        Path to plan file if found, None otherwise
    """
    return claude_installation.find_plan_for_session(repo_root, session_id)


def _get_worktree_name(git: Git, repo_root: Path) -> str | None:
    """Get the directory name of the current worktree.

    Args:
        git: Git gateway for worktree operations
        repo_root: Path to the git repository root

    Returns:
        Worktree directory name, or None if not found
    """
    worktrees = git.list_worktrees(repo_root)
    if not worktrees:
        return None

    for wt in worktrees:
        if wt.path == repo_root:
            return wt.path.name

    return None


def _get_pr_number_for_branch(
    branch_manager: BranchManager, repo_root: Path, branch: str
) -> int | None:
    """Get PR number for the given branch.

    Args:
        branch_manager: BranchManager for PR lookups (Graphite or GitHub)
        repo_root: Path to the git repository root
        branch: Branch name to look up

    Returns:
        PR number if exists, None otherwise
    """
    pr_info = branch_manager.get_pr_for_branch(repo_root, branch)
    if pr_info is None:
        return None
    return pr_info.number


def _get_plan_issue_from_impl(repo_root: Path) -> int | None:
    """Load plan issue number from .impl/issue.json file.

    Args:
        repo_root: Path to the git repository root

    Returns:
        Issue number if found, None otherwise
    """
    issue_file = repo_root / ".impl" / "issue.json"
    if not issue_file.is_file():
        return None

    content = issue_file.read_text(encoding="utf-8")
    if not content.strip():
        return None

    data = json.loads(content)
    # Try "issue_number" first (preferred), then fall back to "number"
    issue_number = data.get("issue_number") or data.get("number")
    if isinstance(issue_number, int):
        return issue_number

    return None


# ============================================================================
# Main Hook Entry Point
# ============================================================================


def _gather_inputs(
    *,
    session_id: str | None,
    repo_root: Path,
    github_planning_enabled: bool,
    claude_installation: ClaudeInstallation,
    git: Git,
    branch_manager: BranchManager,
) -> HookInput:
    """Gather all inputs from environment. All I/O happens here.

    Args:
        session_id: Claude session ID from hook_ctx, or None if not available.
        repo_root: Path to the git repository root.
        github_planning_enabled: Whether github_planning is enabled in config.
        claude_installation: Gateway to Claude installation data.
        git: Git gateway for worktree operations.
        branch_manager: BranchManager for PR lookups.

    Returns:
        HookInput with all gathered state.
    """
    # Determine marker existence
    implement_now_marker_exists = False
    plan_saved_marker_exists = False
    incremental_plan_marker_exists = False
    objective_context_marker_exists = False
    objective_issue: int | None = None
    if session_id is not None:
        implement_now_marker_exists = _get_implement_now_marker_path(session_id, repo_root).exists()
        plan_saved_marker_exists = _get_plan_saved_marker_path(session_id, repo_root).exists()
        marker_path = _get_incremental_plan_marker_path(session_id, repo_root)
        incremental_plan_marker_exists = marker_path.exists()
        objective_context_marker_exists = _get_objective_context_marker_path(
            session_id, repo_root
        ).exists()
        objective_issue = _read_objective_context(session_id, repo_root)

    # Find plan file path (None if doesn't exist)
    plan_file_path: Path | None = None
    if session_id is not None:
        plan_file_path = _find_session_plan(session_id, repo_root, claude_installation)

    # Extract title for display (after finding plan file)
    plan_title: str | None = None
    if plan_file_path is not None:
        plan_title = extract_plan_title(plan_file_path)

    # Get current branch (only if we need to show the blocking message)
    current_branch: str | None = None
    worktree_name: str | None = None
    pr_number: int | None = None
    plan_issue_number: int | None = None

    needs_blocking_message = (
        session_id is not None
        and plan_file_path is not None
        and not implement_now_marker_exists
        and not incremental_plan_marker_exists
        and not plan_saved_marker_exists
    )
    # Get EDITOR env var for TUI detection
    editor: str | None = None
    if needs_blocking_message:
        current_branch = git.get_current_branch(repo_root)
        worktree_name = _get_worktree_name(git, repo_root)
        plan_issue_number = _get_plan_issue_from_impl(repo_root)
        editor = os.environ.get("EDITOR")
        # Only lookup PR if we have a branch
        if current_branch is not None:
            pr_number = _get_pr_number_for_branch(branch_manager, repo_root, current_branch)

    return HookInput(
        session_id=session_id,
        github_planning_enabled=github_planning_enabled,
        implement_now_marker_exists=implement_now_marker_exists,
        plan_saved_marker_exists=plan_saved_marker_exists,
        incremental_plan_marker_exists=incremental_plan_marker_exists,
        objective_context_marker_exists=objective_context_marker_exists,
        objective_issue=objective_issue,
        plan_file_path=plan_file_path,
        plan_title=plan_title,
        current_branch=current_branch,
        worktree_name=worktree_name,
        pr_number=pr_number,
        plan_issue_number=plan_issue_number,
        editor=editor,
    )


def _execute_result(
    result: HookOutput,
    hook_input: HookInput,
    repo_root: Path,
    claude_installation: ClaudeInstallation,
) -> None:
    """Execute the decision result. All I/O happens here."""
    session_id = hook_input.session_id

    if result.delete_implement_now_marker and session_id:
        _get_implement_now_marker_path(session_id, repo_root).unlink()

    if result.delete_plan_saved_marker and session_id:
        _get_plan_saved_marker_path(session_id, repo_root).unlink()

    if result.delete_incremental_plan_marker and session_id:
        _get_incremental_plan_marker_path(session_id, repo_root).unlink()

    if result.delete_objective_context_marker and session_id:
        _get_objective_context_marker_path(session_id, repo_root).unlink()

    # Snapshot plan whenever a plan exists and user made a decision
    # (implement-now or plan-saved, but NOT when blocking to prompt)
    user_made_decision = result.delete_implement_now_marker or result.delete_plan_saved_marker
    if hook_input.plan_file_path is not None and session_id is not None and user_made_decision:
        snapshot_plan_for_session(
            session_id=session_id,
            plan_file_path=hook_input.plan_file_path,
            project_cwd=repo_root,
            claude_installation=claude_installation,
            repo_root=repo_root,
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

    # Get github_planning from injected context (defaults to True if not configured)
    global_config = ctx.obj.global_config
    github_planning_enabled = global_config.github_planning if global_config is not None else True

    # Create branch manager for PR lookups
    branch_manager = create_branch_manager(
        git=ctx.obj.git, github=ctx.obj.github, graphite=ctx.obj.graphite
    )

    # Gather all inputs (I/O layer)
    hook_input = _gather_inputs(
        session_id=hook_ctx.session_id,
        repo_root=hook_ctx.repo_root,
        github_planning_enabled=github_planning_enabled,
        claude_installation=ctx.obj.claude_installation,
        git=ctx.obj.git,
        branch_manager=branch_manager,
    )

    # Pure decision logic (no I/O)
    result = determine_exit_action(hook_input)

    # Execute result (I/O layer)
    _execute_result(result, hook_input, hook_ctx.repo_root, ctx.obj.claude_installation)


if __name__ == "__main__":
    exit_plan_mode_hook()
