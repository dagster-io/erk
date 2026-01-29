"""Unit tests for pre-tool-use-hook command.

Pure function tests require no mocking. Integration tests use CliRunner
with ErkContext injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.pre_tool_use_hook import (
    build_pretool_dignified_python_reminder,
    extract_file_path_from_stdin,
    is_python_file,
    pre_tool_use_hook,
)
from erk_shared.context.context import ErkContext

# ============================================================================
# Pure Logic Tests for extract_file_path_from_stdin()
# ============================================================================


def test_extract_file_path_valid_json() -> None:
    """Extracts file_path from valid PreToolUse stdin JSON."""
    stdin = json.dumps({"tool_input": {"file_path": "/src/foo.py"}})
    assert extract_file_path_from_stdin(stdin) == "/src/foo.py"


def test_extract_file_path_empty_string() -> None:
    """Returns None for empty stdin."""
    assert extract_file_path_from_stdin("") is None


def test_extract_file_path_whitespace_only() -> None:
    """Returns None for whitespace-only stdin."""
    assert extract_file_path_from_stdin("   ") is None


def test_extract_file_path_missing_tool_input() -> None:
    """Returns None when tool_input key is missing."""
    stdin = json.dumps({"other_key": "value"})
    assert extract_file_path_from_stdin(stdin) is None


def test_extract_file_path_missing_file_path() -> None:
    """Returns None when file_path is missing from tool_input."""
    stdin = json.dumps({"tool_input": {"content": "hello"}})
    assert extract_file_path_from_stdin(stdin) is None


def test_extract_file_path_tool_input_not_dict() -> None:
    """Returns None when tool_input is not a dict."""
    stdin = json.dumps({"tool_input": "string_value"})
    assert extract_file_path_from_stdin(stdin) is None


def test_extract_file_path_file_path_not_string() -> None:
    """Returns None when file_path is not a string."""
    stdin = json.dumps({"tool_input": {"file_path": 123}})
    assert extract_file_path_from_stdin(stdin) is None


def test_extract_file_path_empty_file_path() -> None:
    """Returns None when file_path is empty string."""
    stdin = json.dumps({"tool_input": {"file_path": ""}})
    assert extract_file_path_from_stdin(stdin) is None


# ============================================================================
# Pure Logic Tests for is_python_file()
# ============================================================================


def test_is_python_file_py_extension() -> None:
    """Returns True for .py files."""
    assert is_python_file("/src/foo.py") is True


def test_is_python_file_js_extension() -> None:
    """Returns False for .js files."""
    assert is_python_file("/src/foo.js") is False


def test_is_python_file_md_extension() -> None:
    """Returns False for .md files."""
    assert is_python_file("README.md") is False


def test_is_python_file_none() -> None:
    """Returns False for None."""
    assert is_python_file(None) is False


def test_is_python_file_no_extension() -> None:
    """Returns False for files with no extension."""
    assert is_python_file("Makefile") is False


def test_is_python_file_pyi_extension() -> None:
    """Returns False for .pyi stub files (not .py)."""
    assert is_python_file("foo.pyi") is False


# ============================================================================
# Pure Logic Tests for build_pretool_dignified_python_reminder()
# ============================================================================


def test_reminder_mentions_dignified_python() -> None:
    """Reminder mentions dignified-python."""
    result = build_pretool_dignified_python_reminder()
    assert "dignified-python" in result


def test_reminder_mentions_lbyl() -> None:
    """Reminder mentions LBYL pattern."""
    result = build_pretool_dignified_python_reminder()
    assert "LBYL" in result


def test_reminder_mentions_frozen_dataclasses() -> None:
    """Reminder mentions frozen dataclasses."""
    result = build_pretool_dignified_python_reminder()
    assert "frozen dataclasses" in result


def test_reminder_mentions_agents_md() -> None:
    """Reminder references AGENTS.md for full rules."""
    result = build_pretool_dignified_python_reminder()
    assert "AGENTS.md" in result


# ============================================================================
# Helper for setting up reminder capabilities in state.toml
# ============================================================================


def _setup_dignified_python_reminder(tmp_path: Path) -> None:
    """Install dignified-python reminder in state.toml."""
    import tomli_w

    state_path = tmp_path / ".erk" / "state.toml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("wb") as f:
        tomli_w.dump({"reminders": {"installed": ["dignified-python"]}}, f)


# ============================================================================
# Integration Tests
# ============================================================================


class TestHookIntegration:
    """Integration tests using CliRunner with ErkContext injection."""

    def test_outputs_reminder_for_python_file(self, tmp_path: Path) -> None:
        """Emits reminder when editing a .py file with capability installed."""
        runner = CliRunner()
        (tmp_path / ".erk").mkdir()
        _setup_dignified_python_reminder(tmp_path)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps(
            {
                "session_id": "test-session",
                "tool_input": {"file_path": "/src/foo.py"},
            }
        )
        result = runner.invoke(pre_tool_use_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "dignified-python" in result.output
        assert "LBYL" in result.output

    def test_silent_for_javascript_file(self, tmp_path: Path) -> None:
        """No output when editing a .js file."""
        runner = CliRunner()
        (tmp_path / ".erk").mkdir()
        _setup_dignified_python_reminder(tmp_path)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps(
            {
                "session_id": "test-session",
                "tool_input": {"file_path": "/src/app.js"},
            }
        )
        result = runner.invoke(pre_tool_use_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert result.output == ""

    def test_silent_without_capability(self, tmp_path: Path) -> None:
        """No output when dignified-python capability is not installed."""
        runner = CliRunner()
        (tmp_path / ".erk").mkdir()
        # No capability installed

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps(
            {
                "session_id": "test-session",
                "tool_input": {"file_path": "/src/foo.py"},
            }
        )
        result = runner.invoke(pre_tool_use_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert result.output == ""

    def test_silent_outside_erk_project(self, tmp_path: Path) -> None:
        """No output when not in an erk-managed project."""
        runner = CliRunner()
        # No .erk/ directory

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps(
            {
                "session_id": "test-session",
                "tool_input": {"file_path": "/src/foo.py"},
            }
        )
        result = runner.invoke(pre_tool_use_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert result.output == ""

    def test_silent_when_no_file_path_in_stdin(self, tmp_path: Path) -> None:
        """No output when stdin has no file_path."""
        runner = CliRunner()
        (tmp_path / ".erk").mkdir()
        _setup_dignified_python_reminder(tmp_path)

        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)
        stdin_data = json.dumps(
            {
                "session_id": "test-session",
                "tool_input": {"content": "some content"},
            }
        )
        result = runner.invoke(pre_tool_use_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert result.output == ""
