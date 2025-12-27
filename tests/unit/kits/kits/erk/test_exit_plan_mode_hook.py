"""Unit tests for exit-plan-mode-hook command.

This test file uses the pure logic extraction pattern. Most tests call the
`determine_exit_action()` pure function directly with no mocking required.
Only a few integration tests use CliRunner to verify the full hook works.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.exit_plan_mode_hook import (
    ExitAction,
    HookInput,
    build_blocking_message,
    determine_exit_action,
    exit_plan_mode_hook,
)

# ============================================================================
# Pure Logic Tests for determine_exit_action() - NO MOCKING REQUIRED
# ============================================================================


class TestDetermineExitAction:
    """Tests for the pure determine_exit_action() function."""

    def test_github_planning_disabled_allows_exit(self) -> None:
        """When github_planning is disabled, always allow exit."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=False,
                skip_marker_exists=True,  # Even with markers
                saved_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.message == ""

    def test_no_session_id_allows_exit(self) -> None:
        """When no session ID provided, allow exit."""
        result = determine_exit_action(
            HookInput(
                session_id=None,
                github_planning_enabled=True,
                skip_marker_exists=False,
                saved_marker_exists=False,
                plan_file_path=None,
                current_branch=None,
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "No session context" in result.message

    def test_skip_marker_allows_exit_and_deletes(self) -> None:
        """Skip marker allows exit and signals deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                skip_marker_exists=True,
                saved_marker_exists=False,
                plan_file_path=Path("/some/plan.md"),  # Even if plan exists
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "Skip marker found" in result.message
        assert result.delete_skip_marker is True
        assert result.delete_saved_marker is False

    def test_skip_marker_takes_precedence_over_saved_marker(self) -> None:
        """Skip marker is checked before saved marker."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                skip_marker_exists=True,  # Both exist
                saved_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_skip_marker is True
        assert result.delete_saved_marker is False  # Not touched

    def test_saved_marker_blocks_and_deletes(self) -> None:
        """Saved marker blocks exit and signals deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                skip_marker_exists=False,
                saved_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "Plan already saved to GitHub" in result.message
        assert result.delete_saved_marker is True
        assert result.delete_skip_marker is False

    def test_no_plan_file_allows_exit(self) -> None:
        """No plan file allows exit."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                skip_marker_exists=False,
                saved_marker_exists=False,
                plan_file_path=None,
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "No plan file found" in result.message

    def test_plan_exists_blocks_with_instructions(self) -> None:
        """Plan exists without markers - blocks with instructions."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                skip_marker_exists=False,
                saved_marker_exists=False,
                plan_file_path=plan_path,
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "PLAN SAVE PROMPT" in result.message
        assert "AskUserQuestion" in result.message
        assert result.delete_skip_marker is False
        assert result.delete_saved_marker is False


# ============================================================================
# Pure Logic Tests for build_blocking_message() - NO MOCKING REQUIRED
# ============================================================================


class TestBuildBlockingMessage:
    """Tests for the pure build_blocking_message() function."""

    def test_contains_required_elements(self) -> None:
        """Message contains all required elements."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message("session-123", "feature-branch", plan_path)
        assert "PLAN SAVE PROMPT" in message
        assert "AskUserQuestion" in message
        assert "Save the plan" in message
        assert "(Recommended)" in message
        assert "Implement now" in message
        assert "edits code in the current worktree" in message
        assert "/erk:save-plan" in message
        assert "Do NOT call ExitPlanMode" in message
        assert ".erk/scratch/sessions/session-123/skip-plan-save" in message

    def test_trunk_branch_main_shows_warning(self) -> None:
        """Warning shown when on main branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message("session-123", "main", plan_path)
        assert "WARNING" in message
        assert "main" in message
        assert "trunk branch" in message
        assert "dedicated worktree" in message

    def test_trunk_branch_master_shows_warning(self) -> None:
        """Warning shown when on master branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message("session-123", "master", plan_path)
        assert "WARNING" in message
        assert "master" in message
        assert "trunk branch" in message

    def test_feature_branch_no_warning(self) -> None:
        """No warning when on feature branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message("session-123", "feature-branch", plan_path)
        assert "WARNING" not in message
        assert "trunk branch" not in message

    def test_none_branch_no_warning(self) -> None:
        """No warning when branch is None."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message("session-123", None, plan_path)
        assert "WARNING" not in message
        assert "trunk branch" not in message

    def test_edit_plan_option_included(self) -> None:
        """Third option 'View/Edit the plan' is included in message."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message("session-123", "feature-branch", plan_path)
        assert "View/Edit the plan" in message
        assert "Open plan in editor" in message

    def test_edit_plan_instructions_include_path(self) -> None:
        """Edit plan instructions include the plan file path."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message("session-123", "feature-branch", plan_path)
        assert "If user chooses 'View/Edit the plan':" in message
        assert f"${{EDITOR:-code}} {plan_path}" in message
        assert "After user confirms they're done editing" in message
        assert "loop until user chooses Save or Implement" in message

    def test_edit_plan_instructions_omitted_when_no_path(self) -> None:
        """Edit plan instructions omitted when plan_file_path is None."""
        message = build_blocking_message("session-123", "feature-branch", None)
        # The option is still listed (as it's hardcoded), but no instructions
        assert "View/Edit the plan" in message
        assert "If user chooses 'View/Edit the plan':" not in message


# ============================================================================
# Integration Tests - Verify I/O Layer Works (minimal mocking)
# ============================================================================


class TestHookIntegration:
    """Integration tests that verify the full hook works."""

    def test_skip_marker_flow(self, tmp_path: Path) -> None:
        """Verify skip marker is actually deleted when present."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create skip marker
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        skip_marker = marker_dir / "skip-plan-save"
        skip_marker.touch()

        # Mock git repo root to point to tmp_path
        mock_git_result = MagicMock()
        mock_git_result.stdout = str(tmp_path) + "\n"

        with (
            patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=True),
            patch("subprocess.run", return_value=mock_git_result),
            patch(
                "erk_kits.data.kits.erk.scripts.erk.exit_plan_mode_hook.extract_slugs_from_session",
                return_value=[],
            ),
        ):
            stdin_data = json.dumps({"session_id": session_id})
            result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

        assert result.exit_code == 0
        assert "Skip marker found" in result.output
        assert not skip_marker.exists()  # Marker deleted

    def test_saved_marker_flow(self, tmp_path: Path) -> None:
        """Verify saved marker is actually deleted when present."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create saved marker
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        saved_marker = marker_dir / "plan-saved-to-github"
        saved_marker.touch()

        # Mock git repo root
        mock_git_result = MagicMock()
        mock_git_result.stdout = str(tmp_path) + "\n"

        with (
            patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=True),
            patch("subprocess.run", return_value=mock_git_result),
            patch(
                "erk_kits.data.kits.erk.scripts.erk.exit_plan_mode_hook.extract_slugs_from_session",
                return_value=[],
            ),
        ):
            stdin_data = json.dumps({"session_id": session_id})
            result = runner.invoke(exit_plan_mode_hook, input=stdin_data)

        assert result.exit_code == 2  # Block
        assert "Plan already saved to GitHub" in result.output
        assert not saved_marker.exists()  # Marker deleted

    def test_no_stdin_allows_exit(self) -> None:
        """Verify hook works when no stdin provided."""
        runner = CliRunner()

        with patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=True):
            result = runner.invoke(exit_plan_mode_hook)

        assert result.exit_code == 0
