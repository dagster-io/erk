"""Unit tests for exit-plan-mode-hook command.

This test file uses the pure logic extraction pattern. Most tests call the
`determine_exit_action()` pure function directly with no mocking required.
Only a few integration tests use CliRunner to verify the full hook works.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import (
    ExitAction,
    HookInput,
    build_blocking_message,
    determine_exit_action,
    exit_plan_mode_hook,
)
from erk_shared.context.context import ErkContext

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
                implement_now_marker_exists=True,  # Even with markers
                plan_saved_marker_exists=True,
                incremental_plan_marker_exists=True,
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
                implement_now_marker_exists=False,
                plan_saved_marker_exists=False,
                incremental_plan_marker_exists=False,
                plan_file_path=None,
                current_branch=None,
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "No session context" in result.message

    def test_implement_now_marker_allows_exit_and_deletes(self) -> None:
        """Implement-now marker allows exit and markers deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=True,
                plan_saved_marker_exists=False,
                incremental_plan_marker_exists=False,
                plan_file_path=Path("/some/plan.md"),  # Even if plan exists
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "Implement-now marker found" in result.message
        assert result.delete_implement_now_marker is True
        assert result.delete_plan_saved_marker is False

    def test_implement_now_marker_takes_precedence_over_plan_saved_marker(self) -> None:
        """Implement-now marker is checked before plan-saved marker."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=True,  # Both exist
                plan_saved_marker_exists=True,
                incremental_plan_marker_exists=False,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_implement_now_marker is True
        assert result.delete_plan_saved_marker is False  # Not touched

    def test_incremental_plan_marker_allows_exit_and_deletes(self) -> None:
        """Incremental-plan marker allows exit and markers deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=False,
                plan_saved_marker_exists=False,
                incremental_plan_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),  # Even if plan exists
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "Incremental-plan mode" in result.message
        assert "skipping save prompt" in result.message
        assert result.delete_incremental_plan_marker is True
        assert result.delete_implement_now_marker is False
        assert result.delete_plan_saved_marker is False

    def test_implement_now_takes_precedence_over_incremental_plan(self) -> None:
        """Implement-now marker is checked before incremental-plan marker."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=True,
                plan_saved_marker_exists=False,
                incremental_plan_marker_exists=True,  # Both exist
                plan_file_path=Path("/some/plan.md"),
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_implement_now_marker is True
        assert result.delete_incremental_plan_marker is False  # Not touched

    def test_incremental_plan_takes_precedence_over_plan_saved(self) -> None:
        """Incremental-plan marker is checked before plan-saved marker."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=False,
                plan_saved_marker_exists=True,
                incremental_plan_marker_exists=True,  # Both exist
                plan_file_path=Path("/some/plan.md"),
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_incremental_plan_marker is True
        assert result.delete_plan_saved_marker is False  # Not touched

    def test_plan_saved_marker_blocks_and_deletes(self) -> None:
        """Plan-saved marker blocks exit and markers deletion."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=False,
                plan_saved_marker_exists=True,
                incremental_plan_marker_exists=False,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "Plan already saved to GitHub" in result.message
        assert result.delete_plan_saved_marker is True
        assert result.delete_implement_now_marker is False

    def test_no_plan_file_allows_exit(self) -> None:
        """No plan file allows exit."""
        result = determine_exit_action(
            HookInput(
                session_id="abc123",
                github_planning_enabled=True,
                implement_now_marker_exists=False,
                plan_saved_marker_exists=False,
                incremental_plan_marker_exists=False,
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
                implement_now_marker_exists=False,
                plan_saved_marker_exists=False,
                incremental_plan_marker_exists=False,
                plan_file_path=plan_path,
                current_branch="feature-branch",
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "PLAN SAVE PROMPT" in result.message
        assert "AskUserQuestion" in result.message
        assert result.delete_implement_now_marker is False
        assert result.delete_plan_saved_marker is False


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
        assert "/erk:plan-save" in message
        assert "Do NOT call ExitPlanMode" in message
        assert "erk exec marker create --session-id $CLAUDE_CODE_SESSION_ID" in message
        assert "exit-plan-mode-hook.implement-now" in message

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
    """Integration tests that verify the full hook works.

    These tests use ErkContext.for_test() injection. The .erk/ directory
    is created in tmp_path to mark it as a managed project.
    """

    def test_implement_now_marker_flow(self, tmp_path: Path) -> None:
        """Verify implement-now marker is actually deleted when present."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create implement-now marker in tmp_path
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        implement_now_marker = marker_dir / "exit-plan-mode-hook.implement-now.marker"
        implement_now_marker.touch()

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "Implement-now marker found" in result.output
        assert not implement_now_marker.exists()  # Marker deleted

    def test_plan_saved_marker_flow(self, tmp_path: Path) -> None:
        """Verify plan-saved marker is actually deleted when present."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create plan-saved marker in tmp_path
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        plan_saved_marker = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
        plan_saved_marker.touch()

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 2  # Block
        assert "Plan already saved to GitHub" in result.output
        assert not plan_saved_marker.exists()  # Marker deleted

    def test_incremental_plan_marker_flow(self, tmp_path: Path) -> None:
        """Verify incremental-plan marker is deleted and exit is allowed."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create incremental-plan marker in tmp_path
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        incremental_plan_marker = marker_dir / "incremental-plan.marker"
        incremental_plan_marker.touch()

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "Incremental-plan mode" in result.output
        assert not incremental_plan_marker.exists()  # Marker deleted

    def test_no_stdin_allows_exit(self, tmp_path: Path) -> None:
        """Verify hook works when no stdin provided."""
        runner = CliRunner()

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(exit_plan_mode_hook, obj=ctx)

        assert result.exit_code == 0

    def test_silent_when_not_in_managed_project(self, tmp_path: Path) -> None:
        """Verify hook produces no output when not in a managed project."""
        runner = CliRunner()

        # No .erk/ directory - NOT a managed project
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        result = runner.invoke(exit_plan_mode_hook, obj=ctx)

        assert result.exit_code == 0
        assert result.output == ""
