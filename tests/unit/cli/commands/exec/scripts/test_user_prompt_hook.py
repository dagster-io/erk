"""Unit tests for user-prompt-hook command.

This test file uses the pure logic extraction pattern. Most tests call the
pure functions directly with no mocking required.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.user_prompt_hook import (
    build_coding_standards_reminder,
    build_session_context,
    build_tripwires_reminder,
    user_prompt_hook,
)
from erk_shared.context import ErkContext

# ============================================================================
# Pure Logic Tests for build_session_context() - NO MOCKING REQUIRED
# ============================================================================


def test_build_session_context_returns_session_prefix() -> None:
    """Session context includes session ID."""
    result = build_session_context("abc123")
    assert "session: abc123" in result


def test_build_session_context_returns_empty_for_none() -> None:
    """None session returns empty string."""
    result = build_session_context(None)
    assert result == ""


def test_build_session_context_with_uuid_format() -> None:
    """Session context works with UUID-style session IDs."""
    session_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    result = build_session_context(session_id)
    assert session_id in result


# ============================================================================
# Pure Logic Tests for build_coding_standards_reminder() - NO MOCKING REQUIRED
# ============================================================================


def test_build_coding_standards_reminder_mentions_dignified_python() -> None:
    """Reminder mentions dignified-python skill."""
    result = build_coding_standards_reminder()
    assert "dignified-python" in result


def test_build_coding_standards_reminder_mentions_devrun() -> None:
    """Reminder mentions devrun agent for CI commands."""
    result = build_coding_standards_reminder()
    assert "devrun" in result


def test_build_coding_standards_reminder_mentions_no_try_except() -> None:
    """Reminder mentions LBYL rule (no try/except for control flow)."""
    result = build_coding_standards_reminder()
    assert "NO try/except" in result


def test_build_coding_standards_reminder_mentions_forbidden_tools() -> None:
    """Reminder lists tools that require devrun agent."""
    result = build_coding_standards_reminder()
    assert "pytest" in result
    assert "pyright" in result
    assert "ruff" in result


# ============================================================================
# Pure Logic Tests for build_tripwires_reminder() - NO MOCKING REQUIRED
# ============================================================================


def test_build_tripwires_reminder_mentions_tripwires_file() -> None:
    """Reminder mentions tripwires.md file."""
    result = build_tripwires_reminder()
    assert "tripwires.md" in result


def test_build_tripwires_reminder_mentions_docs_path() -> None:
    """Reminder includes full docs path."""
    result = build_tripwires_reminder()
    assert "docs/learned/tripwires.md" in result


# ============================================================================
# Integration Tests - Verify I/O Layer Works
# ============================================================================


class TestHookIntegration:
    """Integration tests that verify the full hook works.

    These tests use ErkContext.for_test() injection. The .erk/ directory
    is created in tmp_path to mark it as a managed project.
    """

    def test_outputs_session_context_and_reminders(self, tmp_path: Path) -> None:
        """Verify hook outputs session context and coding reminders."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert f"session: {session_id}" in result.output
        assert "dignified-python" in result.output
        assert "tripwires.md" in result.output

    def test_persists_session_id_to_file(self, tmp_path: Path) -> None:
        """Verify hook writes session ID to .erk/scratch/current-session-id."""
        runner = CliRunner()
        session_id = "session-xyz789"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Inject via ErkContext
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0

        # Verify file was created with correct content
        session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
        assert session_file.exists()
        assert session_file.read_text(encoding="utf-8") == session_id

    def test_silent_when_not_in_managed_project(self, tmp_path: Path) -> None:
        """Verify hook produces no output when not in a managed project."""
        runner = CliRunner()
        session_id = "session-abc123"

        # No .erk/ directory - NOT a managed project
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert result.output == ""

        # Verify file was NOT created
        session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
        assert not session_file.exists()
