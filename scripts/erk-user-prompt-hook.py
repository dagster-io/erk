#!/usr/bin/env python3
"""Unified UserPromptSubmit hook.

Consolidates multiple hooks into a single script:
1. Venv activation check (block if wrong venv)
2. Session ID injection + file persistence
3. Coding standards reminders
4. Tripwires reminder

Exit codes:
- 0: All checks pass, stdout goes to Claude's context
- 2: Blocking error (venv mismatch), stderr shown to user, prompt blocked
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _get_repo_root() -> Path | None:
    """Get the repository root via git rev-parse.

    Returns:
        Path to the git repository root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def _is_in_managed_project(repo_root: Path) -> bool:
    """Check if repo is a managed project (has .erk/kits.toml)."""
    return (repo_root / ".erk" / "kits.toml").exists()


def check_venv(repo_root: Path, session_id: str) -> tuple[bool, str]:
    """Check venv activation. Returns (should_block, message).

    Verifies that VIRTUAL_ENV matches the expected .venv path for this worktree.
    A bypass signal file can be used to skip this check for a session.

    Args:
        repo_root: Path to the git repository root.
        session_id: The current session ID.

    Returns:
        Tuple of (should_block, message). If should_block is True, the message
        is an error to display. If False, message is empty.
    """
    # Check for bypass signal
    bypass_signal = repo_root / ".erk" / "scratch" / "sessions" / session_id / "venv-bypass.signal"
    if bypass_signal.exists():
        return (False, "")

    expected_venv = repo_root / ".venv"
    actual_venv = os.environ.get("VIRTUAL_ENV")

    # If no venv is expected (doesn't exist), don't block
    if not expected_venv.exists():
        return (False, "")

    # If no venv is activated but one is expected, block
    if actual_venv is None:
        return (
            True,
            f"❌ No virtual environment activated.\n"
            f"Expected: {expected_venv}\n"
            f"Run: source {expected_venv}/bin/activate",
        )

    # Normalize paths for comparison
    expected_resolved = expected_venv.resolve()
    actual_resolved = Path(actual_venv).resolve()

    if actual_resolved != expected_resolved:
        return (
            True,
            f"❌ Wrong virtual environment activated.\n"
            f"Expected: {expected_resolved}\n"
            f"Actual: {actual_resolved}\n"
            f"Run: source {expected_venv}/bin/activate",
        )

    return (False, "")


def persist_session_id(repo_root: Path, session_id: str) -> str:
    """Write session ID to file, return context string.

    Args:
        repo_root: Path to the git repository root.
        session_id: The current session ID.

    Returns:
        Context string to include in output (or empty if no session ID).
    """
    if session_id == "unknown":
        return ""

    session_file = repo_root / ".erk" / "scratch" / "current-session-id"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id, encoding="utf-8")

    return f"📌 session: {session_id}"


def coding_standards_reminder() -> str:
    """Return coding standards context."""
    return """📌 fake-driven-testing: If not loaded, load now. Always abide by its rules.
🚫 No direct Bash for: pytest/pyright/ruff/prettier/make/gt
✅ Use Task(subagent_type='devrun') instead.
📌 dignified-python: CRITICAL RULES (examples - full skill has more):
❌ NO try/except for control flow (use LBYL - check conditions first)
❌ NO default parameter values (no `foo: bool = False`)
❌ NO mutable/non-frozen dataclasses (always `@dataclass(frozen=True)`)
⚠️ MANDATORY: Load and READ the full dignified-python skill documents.
   These are examples only. You MUST strictly abide by ALL rules in the skill.
🧪 AFTER completing Python changes: Verify sufficient test coverage.
Behavior changes ALWAYS need tests."""


def tripwires_reminder() -> str:
    """Return tripwires context."""
    return "🚧 Ensure docs/learned/tripwires.md is loaded and follow its directives."


def main() -> None:
    """Main entry point for the unified hook."""
    # Parse stdin for session context
    stdin_data: dict[str, str] = {}
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip()
        if stdin_content:
            stdin_data = json.loads(stdin_content)

    session_id = stdin_data.get("session_id", "unknown")

    # Check if we're in a git repo
    repo_root = _get_repo_root()
    if repo_root is None:
        # Not in a git repo - exit silently
        return

    # Check if this is a managed project
    if not _is_in_managed_project(repo_root):
        # Not a managed project - exit silently
        return

    # Check venv first - may block
    should_block, block_msg = check_venv(repo_root, session_id)
    if should_block:
        print(block_msg, file=sys.stderr)
        sys.exit(2)

    # Collect context
    context_parts = [
        persist_session_id(repo_root, session_id),
        coding_standards_reminder(),
        tripwires_reminder(),
    ]
    print("\n".join(p for p in context_parts if p))


if __name__ == "__main__":
    main()
