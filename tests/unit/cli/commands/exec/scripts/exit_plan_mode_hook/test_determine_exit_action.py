"""Tests for the pure determine_exit_action() function."""

from pathlib import Path

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import (
    ExitAction,
    HookInput,
    determine_exit_action,
)


class TestDetermineExitAction:
    """Tests for the pure determine_exit_action() function."""

    def test_github_planning_disabled_allows_exit(self) -> None:
        """When github_planning is disabled, always allow exit."""
        result = determine_exit_action(
            HookInput.for_test(
                github_planning_enabled=False,
                implement_now_marker_exists=True,  # Even with markers
                plan_saved_marker_exists=True,
                incremental_plan_marker_exists=True,
                objective_context_marker_exists=True,
                objective_id=3679,
                plan_file_path=Path("/some/plan.md"),
                current_branch="main",
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.message == ""

    def test_no_session_id_allows_exit(self) -> None:
        """When no session ID provided, allow exit."""
        result = determine_exit_action(HookInput.for_test(session_id=None))
        assert result.action == ExitAction.ALLOW
        assert "No session context" in result.message

    def test_implement_now_marker_allows_exit_and_deletes(self) -> None:
        """Implement-now marker allows exit and markers deletion."""
        result = determine_exit_action(
            HookInput.for_test(
                implement_now_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),  # Even if plan exists
            )
        )
        assert result.action == ExitAction.ALLOW
        assert "Implement-now marker found" in result.message
        assert result.delete_implement_now_marker is True
        assert result.delete_plan_saved_marker is False

    def test_implement_now_marker_takes_precedence_over_plan_saved_marker(self) -> None:
        """Implement-now marker is checked before plan-saved marker."""
        result = determine_exit_action(
            HookInput.for_test(
                implement_now_marker_exists=True,  # Both exist
                plan_saved_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_implement_now_marker is True
        assert result.delete_plan_saved_marker is False  # Not touched

    def test_incremental_plan_marker_allows_exit_and_deletes(self) -> None:
        """Incremental-plan marker allows exit and markers deletion."""
        result = determine_exit_action(
            HookInput.for_test(
                incremental_plan_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),  # Even if plan exists
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
            HookInput.for_test(
                implement_now_marker_exists=True,
                incremental_plan_marker_exists=True,  # Both exist
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_implement_now_marker is True
        assert result.delete_incremental_plan_marker is False  # Not touched

    def test_incremental_plan_takes_precedence_over_plan_saved(self) -> None:
        """Incremental-plan marker is checked before plan-saved marker."""
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                incremental_plan_marker_exists=True,  # Both exist
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_incremental_plan_marker is True
        assert result.delete_plan_saved_marker is False  # Not touched

    def test_plan_saved_marker_blocks_and_preserves(self) -> None:
        """Plan-saved marker blocks exit but preserves the marker.

        The marker is preserved so subsequent ExitPlanMode calls continue to block
        with "session complete" instead of prompting the user again (which would
        cause duplicate plan creation if the agent ignores the block).
        """
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "Plan PR already created" in result.message
        assert result.delete_plan_saved_marker is False
        assert result.delete_implement_now_marker is False

    def test_plan_saved_marker_message_uses_draft_pr_language(self) -> None:
        """Plan-saved marker uses draft PR language."""
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "Plan PR already created" in result.message

    def test_no_plan_file_allows_exit(self) -> None:
        """No plan file allows exit."""
        result = determine_exit_action(HookInput.for_test(plan_file_path=None))
        assert result.action == ExitAction.ALLOW
        assert "No plan file found" in result.message

    def test_plan_exists_blocks_with_instructions(self) -> None:
        """Plan exists without markers - blocks with instructions."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        result = determine_exit_action(HookInput.for_test(plan_file_path=plan_path))
        assert result.action == ExitAction.BLOCK
        assert "PLAN SAVE PROMPT" in result.message
        assert "AskUserQuestion" in result.message
        assert result.delete_implement_now_marker is False
        assert result.delete_plan_saved_marker is False

    def test_implement_now_deletes_objective_context_marker_when_present(self) -> None:
        """Implement-now marker also deletes objective-context marker if present."""
        result = determine_exit_action(
            HookInput.for_test(
                implement_now_marker_exists=True,
                objective_context_marker_exists=True,
                objective_id=3679,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.ALLOW
        assert result.delete_implement_now_marker is True
        assert result.delete_objective_context_marker is True

    def test_plan_saved_deletes_objective_context_marker_when_present(self) -> None:
        """Plan-saved marker deletes objective-context marker but preserves plan-saved marker."""
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                objective_context_marker_exists=True,
                objective_id=3679,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.BLOCK
        # Plan-saved marker is preserved (see test_plan_saved_marker_blocks_and_preserves)
        assert result.delete_plan_saved_marker is False
        # But objective-context marker is deleted (one-time use)
        assert result.delete_objective_context_marker is True
