"""Unit tests for exit-plan-mode-hook command."""

import json
import subprocess
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.exit_plan_mode_hook import (
    exit_plan_mode_hook,
)


def test_no_session_id_skips_save() -> None:
    """Test when no session ID is provided (no stdin)."""
    runner = CliRunner()

    result = runner.invoke(exit_plan_mode_hook)

    assert result.exit_code == 0
    assert "No session context available" in result.output


def test_session_id_plan_saved_successfully() -> None:
    """Test successful plan save to GitHub."""
    runner = CliRunner()

    mock_result = MagicMock()
    mock_result.stdout = json.dumps(
        {
            "success": True,
            "issue_number": 123,
            "issue_url": "https://github.com/test/repo/issues/123",
        }
    )

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        stdin_data = json.dumps({"session_id": "session-abc123"})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "Plan saved to GitHub" in result.output
    assert "https://github.com/test/repo/issues/123" in result.output

    # Verify subprocess was called with correct args
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "dot-agent" in call_args
    assert "plan-save-to-issue" in call_args
    assert "--session-id" in call_args
    assert "session-abc123" in call_args


def test_session_id_no_plan_found() -> None:
    """Test when session ID is provided but no plan exists."""
    runner = CliRunner()

    # Simulate CalledProcessError with "No plan found" in stdout
    mock_error = subprocess.CalledProcessError(1, "cmd")
    mock_error.stdout = json.dumps({"success": False, "error": "No plan found in ~/.claude/plans/"})
    mock_error.stderr = ""

    with patch("subprocess.run", side_effect=mock_error):
        stdin_data = json.dumps({"session_id": "session-abc123"})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "No plan file found" in result.output


def test_session_id_github_save_fails() -> None:
    """Test when plan exists but GitHub save fails."""
    runner = CliRunner()

    mock_error = subprocess.CalledProcessError(1, "cmd")
    mock_error.stdout = json.dumps({"success": False, "error": "gh auth failed"})
    mock_error.stderr = ""

    with patch("subprocess.run", side_effect=mock_error):
        stdin_data = json.dumps({"session_id": "session-abc123"})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    # Exit code 2 blocks ExitPlanMode
    assert result.exit_code == 2
    assert "Failed to save plan" in result.output
    assert "gh auth failed" in result.output
    assert "/erk:save-plan" in result.output


def test_session_id_subprocess_error_with_stderr() -> None:
    """Test when subprocess fails with stderr message."""
    runner = CliRunner()

    mock_error = subprocess.CalledProcessError(1, "cmd")
    mock_error.stdout = ""
    mock_error.stderr = "Command not found"

    with patch("subprocess.run", side_effect=mock_error):
        stdin_data = json.dumps({"session_id": "session-abc123"})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 2
    assert "Failed to save plan" in result.output


def test_invalid_json_stdin() -> None:
    """Test when stdin contains invalid JSON."""
    runner = CliRunner()

    result = runner.invoke(exit_plan_mode_hook, input="not valid json")

    assert result.exit_code == 0
    assert "No session context available" in result.output


def test_stdin_missing_session_id_key() -> None:
    """Test when stdin JSON doesn't have session_id key."""
    runner = CliRunner()

    stdin_data = json.dumps({"other_key": "value"})
    result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "No session context available" in result.output


def test_malformed_response_from_subprocess() -> None:
    """Test when subprocess returns malformed JSON."""
    runner = CliRunner()

    mock_result = MagicMock()
    mock_result.stdout = "not json"

    with patch("subprocess.run", return_value=mock_result):
        stdin_data = json.dumps({"session_id": "session-abc123"})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    # JSON decode error treated as failure, but not blocking since we can't parse
    assert result.exit_code == 2
    assert "Failed to save plan" in result.output
