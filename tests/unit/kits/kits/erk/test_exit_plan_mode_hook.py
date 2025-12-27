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
                implement_now_signal_exists=True,  # Even with signals
                plan_saved_signal_exists=True,
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
                implement_now_signal_exists=False,
                plan_saved_signal_exists=False,
                plan_file_path=None,
                current_branch=None,
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "No session context" in result.message

    def test_implement_now_signal_allows_exit_and_deletes(self) -> None:
        """Implement-now signal allows exit and signals deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_signal_exists=True,
                plan_saved_signal_exists=False,
                plan_file_path=Path("/some/plan.md"),  # Even if plan exists
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "Implement-now signal found" in result.message
        assert result.delete_implement_now_signal is True
        assert result.delete_plan_saved_signal is False

    def test_implement_now_signal_takes_precedence_over_plan_saved_signal(self) -> None:
        """Implement-now signal is checked before plan-saved signal."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_signal_exists=True,  # Both exist
                plan_saved_signal_exists=True,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_implement_now_signal is True
        assert result.delete_plan_saved_signal is False  # Not touched

    def test_plan_saved_signal_blocks_and_deletes(self) -> None:
        """Plan-saved signal blocks exit and signals deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_signal_exists=False,
                plan_saved_signal_exists=True,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "Plan already saved to GitHub" in result.message
        assert result.delete_plan_saved_signal is True
        assert result.delete_implement_now_signal is False

    def test_no_plan_file_allows_exit(self) -> None:
        """No plan file allows exit."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_signal_exists=False,
                plan_saved_signal_exists=False,
                plan_file_path=None,
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "No plan file found" in result.message

    def test_plan_exists_blocks_with_instructions(self) -> None:
        """Plan exists without signals - blocks with instructions."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_signal_exists=False,
                plan_saved_signal_exists=False,
                plan_file_path=plan_path,
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "PLAN SAVE PROMPT" in result.message
        assert "AskUserQuestion" in result.message
        assert result.delete_implement_now_signal is False
        assert result.delete_plan_saved_signal is False


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
        assert "exit-plan-mode-hook.implement-now.signal" in message

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

    def test_implement_now_signal_flow(self, tmp_path: Path) -> None:
        """Verify implement-now signal is actually deleted when present."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create implement-now signal
        signal_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        signal_dir.mkdir(parents=True)
        implement_now_signal = signal_dir / "exit-plan-mode-hook.implement-now.signal"
        implement_now_signal.touch()

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
        assert "Implement-now signal found" in result.output
        assert not implement_now_signal.exists()  # Signal deleted

    def test_plan_saved_signal_flow(self, tmp_path: Path) -> None:
        """Verify plan-saved signal is actually deleted when present."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create plan-saved signal
        signal_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        signal_dir.mkdir(parents=True)
        plan_saved_signal = signal_dir / "exit-plan-mode-hook.plan-saved.signal"
        plan_saved_signal.touch()

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
        assert not plan_saved_signal.exists()  # Signal deleted

    def test_no_stdin_allows_exit(self) -> None:
        """Verify hook works when no stdin provided."""
        runner = CliRunner()

        with patch("erk.kits.hooks.decorators.is_in_managed_project", return_value=True):
            result = runner.invoke(exit_plan_mode_hook)

        assert result.exit_code == 0
