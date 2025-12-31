#!/usr/bin/env python3
"""UserPromptSubmit hook for erk.

Consolidates multiple hooks into a single script:
1. Venv activation check (block if wrong venv)
2. Session ID injection + file persistence
3. Coding standards reminders
4. Tripwires reminder

Exit codes:
    0: All checks pass, stdout goes to Claude's context
    2: Blocking error (venv mismatch), stderr shown to user, prompt blocked

This command is invoked via:
    ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook
"""

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

from erk.hooks.decorators import logged_hook, project_scoped
from erk_shared.scratch.scratch import _get_repo_root

# ============================================================================
# Data Classes for Pure Logic
# ============================================================================


class HookAction(Enum):
    """Hook action result."""

    ALLOW = 0  # Exit code 0 - allow prompt, emit context
    BLOCK = 2  # Exit code 2 - block prompt, show error


@dataclass(frozen=True)
class HookInput:
    """All inputs needed for decision logic."""

    session_id: str
    repo_root: Path
    expected_venv: Path | None  # None if .venv doesn't exist
    actual_venv: Path | None  # None if VIRTUAL_ENV not set
    bypass_signal_exists: bool


@dataclass(frozen=True)
class VenvCheckResult:
    """Result of venv validation."""

    action: HookAction
    error_message: str  # Empty if action is ALLOW


# ============================================================================
# Pure Functions (no I/O, fully testable without mocking)
# ============================================================================


def check_venv(hook_input: HookInput) -> VenvCheckResult:
    """Check venv activation. Returns result with action and optional error.

    Pure function - all decision logic, no I/O.
    """
    # Bypass signal present - skip check
    if hook_input.bypass_signal_exists:
        return VenvCheckResult(HookAction.ALLOW, "")

    # No venv expected (doesn't exist) - allow
    if hook_input.expected_venv is None:
        return VenvCheckResult(HookAction.ALLOW, "")

    # No venv activated but one is expected - block
    if hook_input.actual_venv is None:
        return VenvCheckResult(
            HookAction.BLOCK,
            f"No virtual environment activated.\n"
            f"Expected: {hook_input.expected_venv}\n"
            f"Run: source {hook_input.expected_venv}/bin/activate",
        )

    # Wrong venv activated - block
    if hook_input.actual_venv != hook_input.expected_venv:
        return VenvCheckResult(
            HookAction.BLOCK,
            f"Wrong virtual environment activated.\n"
            f"Expected: {hook_input.expected_venv}\n"
            f"Actual: {hook_input.actual_venv}\n"
            f"Run: source {hook_input.expected_venv}/bin/activate",
        )

    # Correct venv - allow
    return VenvCheckResult(HookAction.ALLOW, "")


def build_session_context(session_id: str) -> str:
    """Build the session ID context string.

    Pure function - string building only.
    """
    if session_id == "unknown":
        return ""
    return f"session: {session_id}"


def build_coding_standards_reminder() -> str:
    """Return coding standards context.

    Pure function - returns static string.
    """
    return """No direct Bash for: pytest/pyright/ruff/prettier/make/gt
Use Task(subagent_type='devrun') instead.
dignified-python: CRITICAL RULES (examples - full skill has more):
NO try/except for control flow (use LBYL - check conditions first)
NO default parameter values (no `foo: bool = False`)
NO mutable/non-frozen dataclasses (always `@dataclass(frozen=True)`)
MANDATORY: Load and READ the full dignified-python skill documents.
   These are examples only. You MUST strictly abide by ALL rules in the skill.
AFTER completing Python changes: Verify sufficient test coverage.
Behavior changes ALWAYS need tests."""


def build_tripwires_reminder() -> str:
    """Return tripwires context.

    Pure function - returns static string.
    """
    return "Ensure docs/learned/tripwires.md is loaded and follow its directives."


# ============================================================================
# I/O Helper Functions
# ============================================================================


def _get_session_id_from_stdin() -> str:
    """Read session ID from stdin if available."""
    if sys.stdin.isatty():
        return "unknown"
    stdin_content = sys.stdin.read().strip()
    if not stdin_content:
        return "unknown"
    stdin_data = json.loads(stdin_content)
    return stdin_data.get("session_id", "unknown")


def _get_bypass_signal_path(repo_root: Path, session_id: str) -> Path:
    """Get bypass signal path in .erk/scratch/sessions/<session_id>/.

    Args:
        repo_root: Path to the git repository root
        session_id: The session ID to build the path for

    Returns:
        Path to venv-bypass signal file
    """
    return repo_root / ".erk" / "scratch" / "sessions" / session_id / "venv-bypass.signal"


def _persist_session_id(repo_root: Path, session_id: str) -> None:
    """Write session ID to file.

    Args:
        repo_root: Path to the git repository root.
        session_id: The current session ID.
    """
    if session_id == "unknown":
        return

    session_file = repo_root / ".erk" / "scratch" / "current-session-id"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id, encoding="utf-8")


def _gather_inputs(repo_root: Path) -> HookInput:
    """Gather all inputs from environment. All I/O happens here."""
    session_id = _get_session_id_from_stdin()

    # Check for expected venv
    expected_venv_path = repo_root / ".venv"
    expected_venv: Path | None = None
    if expected_venv_path.exists():
        expected_venv = expected_venv_path.resolve()

    # Check for actual venv from environment
    actual_venv: Path | None = None
    actual_venv_env = os.environ.get("VIRTUAL_ENV")
    if actual_venv_env:
        actual_venv = Path(actual_venv_env).resolve()

    # Check for bypass signal
    bypass_signal_exists = _get_bypass_signal_path(repo_root, session_id).exists()

    return HookInput(
        session_id=session_id,
        repo_root=repo_root,
        expected_venv=expected_venv,
        actual_venv=actual_venv,
        bypass_signal_exists=bypass_signal_exists,
    )


# ============================================================================
# Main Hook Entry Point
# ============================================================================


@click.command(name="user-prompt-hook")
@logged_hook
@project_scoped
def user_prompt_hook() -> None:
    """UserPromptSubmit hook for venv check, session persistence, and coding reminders.

    This hook runs on every user prompt submission in erk-managed projects.

    Exit codes:
        0: Success - allow prompt, context emitted to stdout
        2: Block - venv mismatch, error shown to user
    """
    # Get repo root (we're project-scoped, so this should exist)
    repo_root = _get_repo_root()

    # Gather all inputs (I/O layer)
    hook_input = _gather_inputs(repo_root)

    # Check venv (pure decision logic)
    venv_result = check_venv(hook_input)
    if venv_result.action == HookAction.BLOCK:
        click.echo(venv_result.error_message, err=True)
        sys.exit(HookAction.BLOCK.value)

    # Persist session ID
    _persist_session_id(repo_root, hook_input.session_id)

    # Build and emit context
    context_parts = [
        build_session_context(hook_input.session_id),
        build_coding_standards_reminder(),
        build_tripwires_reminder(),
    ]
    click.echo("\n".join(p for p in context_parts if p))


if __name__ == "__main__":
    user_prompt_hook()
