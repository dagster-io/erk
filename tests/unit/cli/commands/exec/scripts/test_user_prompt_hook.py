"""Unit tests for user-prompt-hook command.

This test file uses the pure logic extraction pattern. Most tests call the
pure functions directly with no mocking required.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.user_prompt_hook import (
    build_devrun_reminder,
    build_dignified_python_reminder,
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
# Pure Logic Tests for build_devrun_reminder() - NO MOCKING REQUIRED
# ============================================================================


def test_build_devrun_reminder_mentions_devrun() -> None:
    """Devrun reminder mentions devrun agent."""
    result = build_devrun_reminder()
    assert "devrun" in result


def test_build_devrun_reminder_mentions_forbidden_tools() -> None:
    """Devrun reminder lists tools that require devrun agent."""
    result = build_devrun_reminder()
    assert "pytest" in result
    assert "ty" in result
    assert "ruff" in result


# ============================================================================
# Pure Logic Tests for build_dignified_python_reminder() - NO MOCKING REQUIRED
# ============================================================================


def test_build_dignified_python_reminder_mentions_dignified_python() -> None:
    """Reminder mentions dignified-python skill."""
    result = build_dignified_python_reminder()
    assert "dignified-python" in result


def test_build_dignified_python_reminder_mentions_no_try_except() -> None:
    """Reminder mentions LBYL rule (no try/except for control flow)."""
    result = build_dignified_python_reminder()
    assert "NO try/except" in result


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
# Helper for setting up reminder capabilities in state.toml
# ============================================================================


def _setup_reminders(
    tmp_path: Path,
    *,
    devrun: bool,
    dignified_python: bool,
    tripwires: bool,
) -> None:
    """Add reminders to state.toml [reminders] section.

    Each reminder is stored as an entry in the installed list:
    [reminders]
    installed = ["devrun", "dignified-python", "tripwires"]
    """
    import tomli_w

    installed: list[str] = []
    if devrun:
        installed.append("devrun")
    if dignified_python:
        installed.append("dignified-python")
    if tripwires:
        installed.append("tripwires")

    if installed:
        state_path = tmp_path / ".erk" / "state.toml"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with state_path.open("wb") as f:
            tomli_w.dump({"reminders": {"installed": installed}}, f)


# ============================================================================
# Integration Tests - Verify I/O Layer Works
# ============================================================================


class TestHookIntegration:
    """Integration tests that verify the full hook works.

    These tests use ErkContext.for_test() injection. The .erk/ directory
    is created in tmp_path to mark it as a managed project.
    """

    def test_outputs_session_context_and_all_reminders(self, tmp_path: Path) -> None:
        """Verify hook outputs session context and all reminders when installed."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Install all reminder capabilities
        _setup_reminders(tmp_path, devrun=True, dignified_python=True, tripwires=True)

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert f"session: {session_id}" in result.output
        assert "devrun" in result.output
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


# ============================================================================
# Integration Tests for Capability-Based Reminder Behavior
# ============================================================================


class TestReminderCapabilities:
    """Tests verifying reminders are only emitted when capabilities are installed."""

    def test_no_reminders_when_no_capabilities_installed(self, tmp_path: Path) -> None:
        """Verify no reminders are emitted when no capabilities are installed."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ but NO capability markers
        (tmp_path / ".erk").mkdir()

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        # Session context is always included
        assert f"session: {session_id}" in result.output
        # But no reminders
        assert "devrun" not in result.output
        assert "dignified-python" not in result.output
        assert "tripwires.md" not in result.output

    def test_only_devrun_reminder_when_only_devrun_installed(self, tmp_path: Path) -> None:
        """Verify only devrun reminder is emitted when only devrun is installed."""
        runner = CliRunner()
        session_id = "session-abc123"

        (tmp_path / ".erk").mkdir()
        _setup_reminders(tmp_path, devrun=True, dignified_python=False, tripwires=False)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "devrun" in result.output
        assert "dignified-python" not in result.output
        assert "tripwires.md" not in result.output

    def test_only_dignified_python_reminder_when_only_that_installed(self, tmp_path: Path) -> None:
        """Verify only dignified-python reminder when only that capability installed."""
        runner = CliRunner()
        session_id = "session-abc123"

        (tmp_path / ".erk").mkdir()
        _setup_reminders(tmp_path, devrun=False, dignified_python=True, tripwires=False)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "dignified-python" in result.output
        # devrun may appear in dignified-python reminder, so we check specific text
        assert "NO try/except" in result.output
        assert "tripwires.md" not in result.output

    def test_only_tripwires_reminder_when_only_that_installed(self, tmp_path: Path) -> None:
        """Verify only tripwires reminder when only that capability installed."""
        runner = CliRunner()
        session_id = "session-abc123"

        (tmp_path / ".erk").mkdir()
        _setup_reminders(tmp_path, devrun=False, dignified_python=False, tripwires=True)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "tripwires.md" in result.output
        # devrun should not appear in output (though dignified-python won't appear either)
        assert "NO try/except" not in result.output

    def test_partial_capabilities_devrun_and_tripwires(self, tmp_path: Path) -> None:
        """Verify partial capability installation works correctly."""
        runner = CliRunner()
        session_id = "session-abc123"

        (tmp_path / ".erk").mkdir()
        _setup_reminders(tmp_path, devrun=True, dignified_python=False, tripwires=True)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(user_prompt_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        # Check devrun-specific content
        assert "Task(subagent_type='devrun')" in result.output
        assert "tripwires.md" in result.output
        # dignified-python specific content should be absent
        assert "NO try/except" not in result.output
