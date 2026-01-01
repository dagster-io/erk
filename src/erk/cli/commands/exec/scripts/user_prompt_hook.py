#!/usr/bin/env python3
"""UserPromptSubmit hook for erk.

Consolidates multiple hooks into a single script:
1. Session ID injection + file persistence
2. Coding standards reminders
3. Tripwires reminder

Exit codes:
    0: All checks pass, stdout goes to Claude's context

This command is invoked via:
    ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook
"""

from pathlib import Path

import click

from erk.hooks.decorators import HookContext, hook_command

# ============================================================================
# Pure Functions for Output Building
# ============================================================================


def build_session_context(session_id: str | None) -> str:
    """Build the session ID context string.

    Pure function - string building only.
    """
    if session_id is None:
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


def _persist_session_id(repo_root: Path, session_id: str | None) -> None:
    """Write session ID to file.

    Args:
        repo_root: Path to the git repository root.
        session_id: The current session ID, or None if not available.
    """
    if session_id is None:
        return

    session_file = repo_root / ".erk" / "scratch" / "current-session-id"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id, encoding="utf-8")


# ============================================================================
# Main Hook Entry Point
# ============================================================================


@hook_command(name="user-prompt-hook")
def user_prompt_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """UserPromptSubmit hook for session persistence and coding reminders.

    This hook runs on every user prompt submission in erk-managed projects.

    Exit codes:
        0: Success - context emitted to stdout
    """
    # Scope check: only run in erk-managed projects
    if not hook_ctx.is_erk_project:
        return

    # Persist session ID
    _persist_session_id(hook_ctx.repo_root, hook_ctx.session_id)

    # Build and emit context
    context_parts = [
        build_session_context(hook_ctx.session_id),
        build_coding_standards_reminder(),
        build_tripwires_reminder(),
    ]
    click.echo("\n".join(p for p in context_parts if p))


if __name__ == "__main__":
    user_prompt_hook()
