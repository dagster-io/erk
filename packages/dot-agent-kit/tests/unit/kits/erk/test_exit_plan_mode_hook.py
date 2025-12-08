"""Unit tests for exit-plan-mode-hook command."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.exit_plan_mode_hook import (
    exit_plan_mode_hook,
)


def test_no_session_id_allows_exit() -> None:
    """Test when no session ID is provided (no stdin)."""
    runner = CliRunner()

    result = runner.invoke(exit_plan_mode_hook)

    # No session ID means exit 0 (allow exit)
    assert result.exit_code == 0


def test_skip_marker_present_deletes_and_allows(tmp_path: Path) -> None:
    """Test when skip marker exists - should delete marker and allow exit."""
    runner = CliRunner()

    # Create skip marker at correct path with sessions/ segment
    session_id = "session-abc123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    skip_marker = marker_dir / "skip-plan-save"
    skip_marker.touch()

    # Mock git to return our tmp_path as repo root
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    with patch("subprocess.run", return_value=mock_git_result):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "Skip marker found" in result.output
    # Marker should be deleted
    assert not skip_marker.exists()


def test_saved_marker_present_blocks_to_prevent_plan_dialog(
    tmp_path: Path,
) -> None:
    """Test when saved marker exists - should block ExitPlanMode to prevent plan approval dialog."""
    runner = CliRunner()
    session_id = "session-abc123"

    # Create saved marker at correct path with sessions/ segment
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    saved_marker = marker_dir / "plan-saved-to-github"
    saved_marker.touch()

    # Mock git to return our tmp_path as repo root
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    with patch("subprocess.run", return_value=mock_git_result):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    # Exit 2 = block, prevents plan approval dialog from appearing
    assert result.exit_code == 2
    assert "Plan already saved to GitHub" in result.output
    assert "Session complete" in result.output
    # Marker should be deleted
    assert not saved_marker.exists()


def test_skip_marker_takes_precedence_over_saved_marker(tmp_path: Path) -> None:
    """Test that skip marker is checked before saved marker."""
    runner = CliRunner()

    # Create both markers at correct path with sessions/ segment
    session_id = "session-abc123"
    marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    marker_dir.mkdir(parents=True)
    skip_marker = marker_dir / "skip-plan-save"
    skip_marker.touch()
    saved_marker = marker_dir / "plan-saved-to-github"
    saved_marker.touch()

    # Mock git to return our tmp_path as repo root
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    with patch("subprocess.run", return_value=mock_git_result):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    # Skip marker should be processed first
    assert "Skip marker found" in result.output
    # Skip marker deleted, saved marker untouched
    assert not skip_marker.exists()
    assert saved_marker.exists()


def test_plan_exists_no_marker_blocks(tmp_path: Path) -> None:
    """Test when plan exists but no skip marker - should block with instructions."""
    runner = CliRunner()
    session_id = "session-abc123"

    # Create plans directory with a plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "test-slug.md"
    plan_file.write_text("# Test Plan", encoding="utf-8")

    # Mock git to return tmp_path as repo root (no skip marker there)
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    # Mock extract_slugs_from_session to return our slug
    with (
        patch("subprocess.run", return_value=mock_git_result),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.exit_plan_mode_hook.extract_slugs_from_session",
            return_value=["test-slug"],
        ),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    # Exit code 2 blocks ExitPlanMode
    assert result.exit_code == 2
    assert "PLAN SAVE PROMPT" in result.output
    assert "AskUserQuestion" in result.output
    # Updated messaging: Save to GitHub is default and terminal
    assert "Save to GitHub" in result.output
    assert "(default)" in result.output
    assert "Does NOT proceed to implementation" in result.output
    assert "Implement now" in result.output
    # Skip marker path should be documented with sessions/ segment (for "Implement now" flow)
    assert f".erk/scratch/sessions/{session_id}/skip-plan-save" in result.output
    # Saved marker is NOT documented - /erk:save-plan handles it internally
    assert "Do NOT call ExitPlanMode" in result.output


def test_no_plan_allows_exit(tmp_path: Path) -> None:
    """Test when session ID is provided but no plan exists."""
    runner = CliRunner()
    session_id = "session-abc123"

    # Create empty plans directory (no plan files)
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Mock git to return tmp_path as repo root
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    # Mock extract_slugs_from_session to return empty (no plan)
    with (
        patch("subprocess.run", return_value=mock_git_result),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.exit_plan_mode_hook.extract_slugs_from_session",
            return_value=[],
        ),
    ):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "No plan file found" in result.output


def test_git_not_in_repo_allows_plan_check(tmp_path: Path) -> None:
    """Test when not in a git repo - skip marker check fails gracefully, plan check proceeds."""
    runner = CliRunner()
    session_id = "session-abc123"

    # Create plans directory with a plan file
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)
    plan_file = plans_dir / "test-slug.md"
    plan_file.write_text("# Test Plan", encoding="utf-8")

    # Mock git to fail (not in a repo)
    mock_git_error = subprocess.CalledProcessError(128, "git")

    # Mock extract_slugs_from_session to return our slug
    with (
        patch("subprocess.run", side_effect=mock_git_error),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.exit_plan_mode_hook.extract_slugs_from_session",
            return_value=["test-slug"],
        ),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    # Should still block because plan exists (skip marker check fails gracefully)
    assert result.exit_code == 2
    assert "PLAN SAVE PROMPT" in result.output


def test_invalid_json_stdin_allows_exit() -> None:
    """Test when stdin contains invalid JSON."""
    runner = CliRunner()

    result = runner.invoke(exit_plan_mode_hook, input="not valid json")

    # Invalid JSON means exit 0 (allow exit)
    assert result.exit_code == 0


def test_stdin_missing_session_id_key_allows_exit() -> None:
    """Test when stdin JSON doesn't have session_id key."""
    runner = CliRunner()

    stdin_data = json.dumps({"other_key": "value"})
    result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "No session context available" in result.output


def test_plans_dir_not_exists_allows_exit(tmp_path: Path) -> None:
    """Test when ~/.claude/plans/ doesn't exist."""
    runner = CliRunner()
    session_id = "session-abc123"

    # Don't create plans directory - it doesn't exist

    # Mock git to return tmp_path as repo root
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    with (
        patch("subprocess.run", return_value=mock_git_result),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "No plan file found" in result.output


def test_slug_exists_but_plan_file_missing(tmp_path: Path) -> None:
    """Test when slug is found but plan file doesn't exist."""
    runner = CliRunner()
    session_id = "session-abc123"

    # Create empty plans directory (no plan file for the slug)
    plans_dir = tmp_path / ".claude" / "plans"
    plans_dir.mkdir(parents=True)

    # Mock git to return tmp_path as repo root
    mock_git_result = MagicMock()
    mock_git_result.stdout = str(tmp_path) + "\n"

    # Mock extract_slugs_from_session to return a slug, but plan file won't exist
    with (
        patch("subprocess.run", return_value=mock_git_result),
        patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.exit_plan_mode_hook.extract_slugs_from_session",
            return_value=["nonexistent-slug"],
        ),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

    assert result.exit_code == 0
    assert "No plan file found" in result.output
