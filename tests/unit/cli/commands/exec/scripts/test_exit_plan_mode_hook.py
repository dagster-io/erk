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
    _gather_inputs,
    abbreviate_for_header,
    build_blocking_message,
    build_step2_message,
    determine_exit_action,
    exit_plan_mode_hook,
    extract_pr_title,
    is_terminal_editor,
)
from erk_shared.context.context import ErkContext
from tests.fakes.gateway.branch_manager import FakeBranchManager
from tests.fakes.gateway.claude_installation import FakeClaudeInstallation
from tests.fakes.gateway.git import FakeGit
from tests.fakes.tests.shared_context import context_for_test

# ============================================================================
# Pure Logic Tests for determine_exit_action() - NO MOCKING REQUIRED
# ============================================================================


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

    def test_plan_saved_marker_blocks_with_step2(self) -> None:
        """Plan-saved marker blocks exit with Step 2 prompt and deletes the marker."""
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                plan_saved_pr_number=42,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "PR #42 saved" in result.message
        assert "erk br co --for-plan 42" in result.message
        assert "erk pr dispatch 42" in result.message
        assert "Session complete" in result.message
        assert result.delete_plan_saved_marker is True
        assert result.delete_implement_now_marker is False

    def test_plan_saved_marker_without_pr_number_fallback(self) -> None:
        """Plan-saved marker without plan number uses fallback message."""
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                plan_saved_pr_number=None,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.BLOCK
        assert "PR saved" in result.message
        assert "Planning session complete" in result.message
        assert result.delete_plan_saved_marker is True

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
        """Plan-saved marker blocks exit and deletes both markers."""
        result = determine_exit_action(
            HookInput.for_test(
                plan_saved_marker_exists=True,
                objective_context_marker_exists=True,
                objective_id=3679,
                plan_file_path=Path("/some/plan.md"),
            )
        )
        assert result.action == ExitAction.BLOCK
        # Plan-saved marker is deleted (session complete)
        assert result.delete_plan_saved_marker is True
        # Objective-context marker is also deleted (one-time use)
        assert result.delete_objective_context_marker is True


# ============================================================================
# Pure Logic Tests for extract_pr_title() - NO MOCKING REQUIRED
# ============================================================================


class TestExtractPlanTitle:
    """Tests for the pure extract_pr_title() function."""

    def test_extracts_h1_heading(self, tmp_path: Path) -> None:
        """Extract title from first H1 heading."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# My Plan Title\n\nSome content here.\n", encoding="utf-8")
        assert extract_pr_title(plan_file) == "My Plan Title"

    def test_extracts_from_task_section(self, tmp_path: Path) -> None:
        """Extract title from ## Task section when no H1."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "## Task\nDo the thing with feature X\n\n## Details\nMore info.",
            encoding="utf-8",
        )
        assert extract_pr_title(plan_file) == "Do the thing with feature X"

    def test_skips_generic_plan_heading(self, tmp_path: Path) -> None:
        """Skip generic '# Plan' heading and fall back to ## Task."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\n## Task\nActual task description\n", encoding="utf-8")
        assert extract_pr_title(plan_file) == "Actual task description"

    def test_skips_generic_implementation_plan_heading(self, tmp_path: Path) -> None:
        """Skip generic '# Implementation Plan' heading."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "# Implementation Plan\n\n## Task\nBuild the widget\n", encoding="utf-8"
        )
        assert extract_pr_title(plan_file) == "Build the widget"

    def test_returns_none_for_no_file(self) -> None:
        """Return None when plan_file_path is None."""
        assert extract_pr_title(None) is None

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Return None when file doesn't exist."""
        nonexistent = tmp_path / "does_not_exist.md"
        assert extract_pr_title(nonexistent) is None

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        """Return None when file is empty."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("", encoding="utf-8")
        assert extract_pr_title(plan_file) is None

    def test_returns_none_when_no_title_found(self, tmp_path: Path) -> None:
        """Return None when no valid title pattern found."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "Some random content\nwithout any headings\nor task section.", encoding="utf-8"
        )
        assert extract_pr_title(plan_file) is None

    def test_prefers_h1_over_task_section(self, tmp_path: Path) -> None:
        """H1 heading takes precedence over ## Task section."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Better Title\n\n## Task\nTask description\n", encoding="utf-8")
        assert extract_pr_title(plan_file) == "Better Title"


# ============================================================================
# Pure Logic Tests for is_terminal_editor() - NO MOCKING REQUIRED
# ============================================================================


class TestIsTerminalEditor:
    """Tests for the pure is_terminal_editor() function."""

    def test_vim_is_terminal_editor(self) -> None:
        """vim is recognized as terminal editor."""
        assert is_terminal_editor("vim") is True

    def test_nvim_is_terminal_editor(self) -> None:
        """nvim is recognized as terminal editor."""
        assert is_terminal_editor("nvim") is True

    def test_nano_is_terminal_editor(self) -> None:
        """nano is recognized as terminal editor."""
        assert is_terminal_editor("nano") is True

    def test_emacs_is_terminal_editor(self) -> None:
        """emacs is recognized as terminal editor."""
        assert is_terminal_editor("emacs") is True

    def test_vi_is_terminal_editor(self) -> None:
        """vi is recognized as terminal editor."""
        assert is_terminal_editor("vi") is True

    def test_code_is_not_terminal_editor(self) -> None:
        """code (VS Code) is not a terminal editor."""
        assert is_terminal_editor("code") is False

    def test_sublime_is_not_terminal_editor(self) -> None:
        """subl (Sublime Text) is not a terminal editor."""
        assert is_terminal_editor("subl") is False

    def test_none_is_not_terminal_editor(self) -> None:
        """None returns False."""
        assert is_terminal_editor(None) is False

    def test_full_path_vim_is_terminal_editor(self) -> None:
        """Full path like /usr/bin/vim is recognized as terminal editor."""
        assert is_terminal_editor("/usr/bin/vim") is True

    def test_full_path_nvim_is_terminal_editor(self) -> None:
        """Full path like /opt/homebrew/bin/nvim is recognized as terminal editor."""
        assert is_terminal_editor("/opt/homebrew/bin/nvim") is True

    def test_full_path_code_is_not_terminal_editor(self) -> None:
        """Full path like /usr/local/bin/code is not a terminal editor."""
        assert is_terminal_editor("/usr/local/bin/code") is False


# ============================================================================
# Pure Logic Tests for abbreviate_for_header() - NO MOCKING REQUIRED
# ============================================================================


class TestAbbreviateForHeader:
    """Tests for the pure abbreviate_for_header() function."""

    def test_short_branch_not_truncated(self) -> None:
        """Short branch names are not truncated."""
        assert abbreviate_for_header("feature-x") == "br:feature-x"

    def test_long_branch_truncated(self) -> None:
        """Long branch names are truncated to 9 chars."""
        # "P4535-add-feature" -> truncated to "P4535-add"
        assert abbreviate_for_header("P4535-add-feature") == "br:P4535-add"

    def test_issue_prefix_branch(self) -> None:
        """Issue-prefixed branches show issue number."""
        assert abbreviate_for_header("P4535-foo") == "br:P4535-foo"

    def test_none_returns_default(self) -> None:
        """None returns 'Plan Action' fallback."""
        assert abbreviate_for_header(None) == "Plan Action"

    def test_exactly_nine_chars(self) -> None:
        """Branch name exactly 9 chars is not truncated."""
        assert abbreviate_for_header("123456789") == "br:123456789"

    def test_ten_chars_truncated(self) -> None:
        """Branch name of 10 chars is truncated to 9."""
        assert abbreviate_for_header("1234567890") == "br:123456789"

    def test_main_branch(self) -> None:
        """Main branch is shown as-is."""
        assert abbreviate_for_header("main") == "br:main"

    def test_master_branch(self) -> None:
        """Master branch is shown as-is."""
        assert abbreviate_for_header("master") == "br:master"


# ============================================================================
# Pure Logic Tests for build_blocking_message() - NO MOCKING REQUIRED
# ============================================================================


class TestBuildBlockingMessage:
    """Tests for the pure build_blocking_message() function."""

    def test_contains_required_elements(self) -> None:
        """Message contains all required elements for the new menu."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "PLAN SAVE PROMPT" in message
        assert "AskUserQuestion" in message
        assert "Implement without saving" in message
        assert "Create new branch and planned PR" in message
        assert "Make current empty branch a planned PR" in message
        assert "View/Edit the Plan" in message
        assert "/erk:plan-save" in message
        assert "Call ExitPlanMode" in message
        assert "erk exec marker create --session-id session-123" in message
        assert "exit-plan-mode-hook.implement-now" in message
        assert "If user chooses 'Implement without saving':" in message
        assert "If user chooses 'Create new branch and planned PR':" in message

    def test_current_branch_option_uses_current_branch_flag(self) -> None:
        """Make current empty branch option passes --current-branch to plan-save command."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # Extract the instruction block
        lines = message.split("\n")
        option_start = None
        option_end = None
        for i, line in enumerate(lines):
            if "If user chooses 'Make current empty branch a planned PR':" in line:
                option_start = i
            elif option_start is not None and line.startswith("If user chooses"):
                option_end = i
                break
        assert option_start is not None, "Make current empty branch instruction block not found"
        if option_end is None:
            option_end = len(lines)
        option_block = "\n".join(lines[option_start:option_end])
        assert "/erk:plan-save --current-branch" in option_block

    def test_includes_header_instruction(self) -> None:
        """Message includes header instruction for AskUserQuestion."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="P4535-add-feature",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name="erk-slot-02",
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # Should have both question: and header: instructions
        assert 'question: "' in message
        # Header uses branch name (truncated to 9 chars)
        assert 'header: "br:P4535-add"' in message

    def test_header_default_when_no_branch(self) -> None:
        """Header defaults to 'Plan Action' when current_branch is None."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch=None,
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert 'header: "Plan Action"' in message

    def test_trunk_branch_main_shows_warning(self) -> None:
        """Warning shown when on main branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="main",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "WARNING" in message
        assert "main" in message
        assert "trunk branch" in message
        assert "dedicated worktree" in message

    def test_trunk_branch_master_shows_warning(self) -> None:
        """Warning shown when on master branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="master",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "WARNING" in message
        assert "master" in message
        assert "trunk branch" in message

    def test_feature_branch_no_warning(self) -> None:
        """No warning when on feature branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "WARNING" not in message
        assert "trunk branch" not in message

    def test_none_branch_no_warning(self) -> None:
        """No warning when branch is None."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch=None,
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "WARNING" not in message
        assert "trunk branch" not in message

    def test_edit_plan_option_included(self) -> None:
        """Fourth option 'View/Edit the Plan' is included in message."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "View/Edit the Plan" in message
        assert "Open plan in editor" in message

    def test_implement_without_saving_option_included(self) -> None:
        """Option 'Implement without saving' is included with instruction block."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "Implement without saving" in message
        assert "If user chooses 'Implement without saving':" in message
        assert "Do NOT run 'erk exec setup-impl' or create a new branch" in message
        assert f"Read the plan from: {plan_path}" in message
        assert "erk pr submit" in message

    def test_edit_plan_instructions_include_path(self) -> None:
        """Edit plan instructions include the plan file path for GUI editors."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "If user chooses 'View/Edit the Plan':" in message
        assert f"${{EDITOR:-code}} {plan_path}" in message
        assert "After user confirms they're done editing" in message
        assert "loop until user chooses Save, Implement, or Incremental" in message

    def test_edit_plan_instructions_omitted_when_no_path(self) -> None:
        """Edit plan instructions omitted when plan_file_path is None."""
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=None,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # The option is still listed (as it's hardcoded), but no instructions
        assert "View/Edit the Plan" in message
        assert "If user chooses 'View/Edit the Plan':" not in message

    def test_save_command_no_objective_issue(self) -> None:
        """Save command does not include --objective-issue."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "/erk:plan-save" in message
        assert "--objective-issue" not in message

    def test_includes_title_in_question(self) -> None:
        """Question includes title when available."""
        plan_path = Path.home() / ".claude" / "plans" / "session-123.md"
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title="Add Feature X",
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "📋 Add Feature X" in message
        assert "What would you like to do with this plan?" in message

    def test_includes_statusline_context_with_all_fields(self) -> None:
        """Question includes statusline-style context with all fields."""
        plan_path = Path.home() / ".claude" / "plans" / "session-123.md"
        message = build_blocking_message(
            session_id="session-123",
            current_branch="P4224-add-feature",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title="Add Feature X",
            worktree_name="erk-slot-02",
            pr_number=4230,
            pr_number_from_plan_ref=4224,
            editor=None,
        )
        # Title should be present
        assert "📋 Add Feature X" in message
        # Statusline-style context should be present
        assert "(wt:erk-slot-02)" in message
        assert "(br:P4224-add-feature)" in message
        assert "(pr:#4230)" in message
        assert "(plan:#4224)" in message
        # Header should include branch context (truncated to 9 chars)
        assert 'header: "br:P4224-add"' in message

    def test_includes_statusline_context_partial(self) -> None:
        """Question includes partial statusline context when some fields are None."""
        plan_path = Path.home() / ".claude" / "plans" / "session-123.md"
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name="erk-slot-02",
            pr_number=None,
            pr_number_from_plan_ref=4224,
            editor=None,
        )
        # No title emoji
        assert "📋" not in message
        # Partial statusline context
        assert "(wt:erk-slot-02)" in message
        assert "(br:feature-branch)" in message
        assert "(pr:#" not in message  # No PR
        assert "(plan:#4224)" in message

    def test_no_context_when_all_none(self) -> None:
        """Question has no context when all context fields are None."""
        message = build_blocking_message(
            session_id="session-123",
            current_branch=None,
            branch_has_commits=False,
            plan_file_path=None,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # Should still have the basic question
        assert "What would you like to do with this plan?" in message
        # But no context
        assert "📋" not in message
        assert "(wt:" not in message
        assert "(br:" not in message

    def test_tui_editor_vim_shows_manual_instructions(self) -> None:
        """When editor=vim, message tells user to open in separate terminal."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor="vim",
        )
        assert "If user chooses 'View/Edit the Plan':" in message
        assert "vim is a terminal-based editor that cannot" in message
        assert "run inside Claude Code" in message
        assert "Please open the plan in a separate terminal" in message
        assert f"vim {plan_path}" in message
        assert "Wait for user to confirm" in message
        # Should NOT have the GUI editor instruction
        assert "${EDITOR:-code}" not in message

    def test_tui_editor_nvim_shows_manual_instructions(self) -> None:
        """When editor=nvim (full path), message tells user to open in separate terminal."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor="/opt/homebrew/bin/nvim",
        )
        assert "nvim is a terminal-based editor" in message
        assert f"/opt/homebrew/bin/nvim {plan_path}" in message

    def test_gui_editor_code_shows_run_instruction(self) -> None:
        """When editor=code, message shows normal run instruction."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor="code",
        )
        assert "If user chooses 'View/Edit the Plan':" in message
        assert f"${{EDITOR:-code}} {plan_path}" in message
        # Should NOT have the TUI editor warning
        assert "terminal-based editor" not in message
        assert "separate terminal" not in message

    def test_none_editor_shows_run_instruction(self) -> None:
        """When editor=None, message shows normal run instruction with fallback."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "If user chooses 'View/Edit the Plan':" in message
        assert f"${{EDITOR:-code}} {plan_path}" in message
        # Should NOT have the TUI editor warning
        assert "terminal-based editor" not in message

    def test_display_plan_instruction_when_plan_file_path_provided(self) -> None:
        """Message includes instruction to display plan when plan_file_path is provided."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title="My Plan",
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "DISPLAY PLAN" in message
        assert str(plan_path) in message
        # Display instruction should appear before PLAN SAVE PROMPT
        display_pos = message.index("DISPLAY PLAN")
        save_prompt_pos = message.index("PLAN SAVE PROMPT")
        assert display_pos < save_prompt_pos

    def test_no_display_plan_instruction_when_no_path(self) -> None:
        """No display plan instruction when plan_file_path is None."""
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=None,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "DISPLAY PLAN" not in message
        # Should still have the save prompt
        assert "PLAN SAVE PROMPT" in message

    def test_new_menu_options(self) -> None:
        """New menu has correct 4 options when branch has no commits."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert '  1. "Create new branch and planned PR. Stays on current branch."' in message
        assert '  2. "Implement without saving"' in message
        assert '  3. "Make current empty branch a planned PR"' in message
        assert '  4. "View/Edit the Plan"' in message

    def test_old_options_not_present(self) -> None:
        """Old menu options are no longer present."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "Create a plan PR on new branch" not in message
        assert "Create a plan PR on the current branch" not in message
        assert "Just implement on the current branch" not in message
        assert "Save and dispatch" not in message

    def test_instruction_blocks_use_new_labels(self) -> None:
        """Instruction blocks use new option labels."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "If user chooses 'Implement without saving':" in message
        assert "If user chooses 'Create new branch and planned PR':" in message
        assert "If user chooses 'Make current empty branch a planned PR':" in message
        assert "If user chooses 'View/Edit the Plan':" in message
        # Old labels absent
        assert "If user chooses 'Save plan as draft PR':" not in message
        assert "If user chooses 'Implement here':" not in message
        assert "If user chooses 'Save plan on current branch':" not in message

    def test_current_branch_option_hidden_when_branch_has_commits(self) -> None:
        """Option 'Make current empty branch a planned PR' hidden when branch has commits."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=True,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # Option should NOT be present
        assert "Make current empty branch a planned PR" not in message
        assert "If user chooses 'Make current empty branch a planned PR':" not in message
        assert "/erk:plan-save --current-branch" not in message
        # Other options should still be present
        assert "Create new branch and planned PR" in message
        assert "Implement without saving" in message
        assert "View/Edit the Plan" in message
        assert "If user chooses 'Create new branch and planned PR':" in message
        assert "If user chooses 'Implement without saving':" in message

    def test_current_branch_option_shown_when_no_commits(self) -> None:
        """Option 'Make current empty branch a planned PR' shown when branch has no commits."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # Option should be present
        assert "Make current empty branch a planned PR" in message
        assert "If user chooses 'Make current empty branch a planned PR':" in message
        assert "/erk:plan-save --current-branch" in message

    def test_current_branch_option_hidden_on_trunk(self) -> None:
        """Option 'Make current empty branch a planned PR' hidden when on master."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="master",
            branch_has_commits=False,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        assert "Make current empty branch a planned PR" not in message
        assert "/erk:plan-save --current-branch" not in message
        # Other options should still be present
        assert "Create new branch and planned PR" in message
        assert "Implement without saving" in message

    def test_options_renumbered_when_current_branch_option_hidden(self) -> None:
        """Options are renumbered correctly when current branch option is hidden."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            branch_has_commits=True,
            plan_file_path=plan_path,
            pr_title=None,
            worktree_name=None,
            pr_number=None,
            pr_number_from_plan_ref=None,
            editor=None,
        )
        # With branch_has_commits=True, should be 3 options numbered 1-3
        assert '  1. "Create new branch and planned PR. Stays on current branch."' in message
        assert '  2. "Implement without saving"' in message
        assert '  3. "View/Edit the Plan"' in message
        # Should NOT have option 4
        assert "  4." not in message


# ============================================================================
# Pure Logic Tests for build_step2_message() - NO MOCKING REQUIRED
# ============================================================================


class TestBuildStep2Message:
    """Tests for the pure build_step2_message() function (Step 2: plain text next-steps)."""

    def test_contains_pr_number(self) -> None:
        """Step 2 message includes the PR number."""
        message = build_step2_message(pr_number=42, url="")
        assert "PR #42 saved" in message

    def test_contains_implement_current_wt_command(self) -> None:
        """Step 2 shows implement-in-current-worktree command."""
        message = build_step2_message(pr_number=42, url="")
        assert "erk br co --for-plan 42 && erk implement" in message

    def test_contains_implement_new_wt_command(self) -> None:
        """Step 2 shows implement-in-new-worktree command."""
        message = build_step2_message(pr_number=42, url="")
        assert "--new-slot --for-plan 42" in message

    def test_contains_checkout_commands(self) -> None:
        """Step 2 shows checkout commands."""
        message = build_step2_message(pr_number=42, url="")
        assert "erk br co --for-plan 42" in message

    def test_contains_dispatch_command(self) -> None:
        """Step 2 shows dispatch commands (CLI and slash command)."""
        message = build_step2_message(pr_number=42, url="")
        assert "erk pr dispatch 42" in message
        assert "/erk:pr-dispatch" in message
        assert "Dispatch planned PR #42:" in message

    def test_session_complete_no_exit_plan_mode(self) -> None:
        """Step 2 tells Claude not to call ExitPlanMode again."""
        message = build_step2_message(pr_number=42, url="")
        assert "Session complete. Do NOT call ExitPlanMode again." in message

    def test_no_ask_user_question(self) -> None:
        """Step 2 does NOT use AskUserQuestion."""
        message = build_step2_message(pr_number=42, url="")
        assert "do NOT use AskUserQuestion" in message

    def test_no_implement_now_marker(self) -> None:
        """Step 2 does NOT reference implement-now marker creation."""
        message = build_step2_message(pr_number=42, url="")
        assert "implement-now" not in message
        assert "marker create" not in message

    def test_no_plan_implement_slash_command(self) -> None:
        """Step 2 does NOT reference /erk:plan-implement."""
        message = build_step2_message(pr_number=42, url="")
        assert "/erk:plan-implement" not in message


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

    def test_plan_saved_marker_flow_blocks_and_cleans_up(self, tmp_path: Path) -> None:
        """Verify plan-saved marker blocks exit with Step 2 and deletes the marker."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create plan-saved marker with plan number on first line
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        plan_saved_marker = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
        plan_saved_marker.write_text("42\nCreated by test", encoding="utf-8")

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 2
        assert "PR #42 saved" in result.output
        assert "erk pr dispatch 42" in result.output
        assert not plan_saved_marker.exists()  # Marker deleted after session ends

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

    def test_objective_context_marker_deleted_on_implement_now(self, tmp_path: Path) -> None:
        """Verify objective-context marker is deleted when implement-now is chosen."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create both implement-now and objective-context markers
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        implement_now_marker = marker_dir / "exit-plan-mode-hook.implement-now.marker"
        implement_now_marker.touch()
        objective_context_marker = marker_dir / "objective-context.marker"
        objective_context_marker.write_text("3679", encoding="utf-8")

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 0
        assert "Implement-now marker found" in result.output
        assert not implement_now_marker.exists()  # Marker deleted
        assert not objective_context_marker.exists()  # Also deleted

    def test_objective_context_marker_deleted_on_plan_saved(self, tmp_path: Path) -> None:
        """Verify both plan-saved and objective-context markers are deleted on plan-saved."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create both plan-saved and objective-context markers
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        plan_saved_marker = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
        plan_saved_marker.write_text("42\nCreated by test", encoding="utf-8")
        objective_context_marker = marker_dir / "objective-context.marker"
        objective_context_marker.write_text("3679", encoding="utf-8")

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 2
        assert "PR #42 saved" in result.output
        assert not plan_saved_marker.exists()  # Marker deleted
        assert not objective_context_marker.exists()  # Objective marker also deleted

    def test_branch_manager_used_for_pr_lookup(self, tmp_path: Path) -> None:
        """Verify branch_manager is created and used correctly for PR lookups.

        Regression test for issue #4238: create_branch_manager was called with
        swapped positional arguments (github and graphite were reversed), causing
        AttributeError: 'RealLocalGitHub' object has no attribute 'get_prs_from_graphite'.

        This test exercises the code path where:
        1. A plan file exists (needs_blocking_message is True)
        2. No markers exist
        3. A current branch is detected
        4. branch_manager.get_pr_for_branch() is called

        Before the fix, this would crash because GraphiteBranchManager received
        a GitHub object where it expected Graphite.
        """
        runner = CliRunner()
        session_id = "session-abc123"
        plan_slug = "test-plan-slug"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create plans directory and plan file
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / f"{plan_slug}.md"
        plan_file.write_text("# Test Plan\n\nSome content", encoding="utf-8")

        # Create FakeClaudeInstallation that returns the plan file
        claude_installation = FakeClaudeInstallation.for_test(
            plans_dir_path=plans_dir,
            session_slugs={session_id: [plan_slug]},
            plans={plan_slug: "# Test Plan\n\nSome content"},
        )

        # Create FakeGit with current branch configured
        git = FakeGit(current_branches={tmp_path: "feature-branch"})

        # Create context with the configured fakes
        ctx = context_for_test(
            repo_root=tmp_path,
            cwd=tmp_path,
            git=git,
            claude_installation=claude_installation,
        )

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        # The hook should block (exit code 2) with the plan save prompt
        # The key assertion is that we didn't crash with AttributeError
        assert result.exit_code == 2, f"Unexpected exit code. Output: {result.output}"
        assert "PLAN SAVE PROMPT" in result.output
        # Verify the branch context is included in the output
        assert "(br:feature-branch)" in result.output


class TestGatherInputsParentBranch:
    """Tests that _gather_inputs uses Graphite stack parent for commit detection."""

    def test_uses_graphite_parent_for_commit_counting(self, tmp_path: Path) -> None:
        """When Graphite parent exists, count commits ahead of parent, not trunk.

        In a Graphite stack, a branch may have 0 commits ahead of its stack parent
        but many commits ahead of trunk (because the parent itself has commits).
        The hook should use the stack parent to determine branch_has_commits.
        """
        session_id = "session-abc123"
        plan_slug = "test-plan"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create plan file so needs_blocking_message is True
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / f"{plan_slug}.md"
        plan_file.write_text("# Test Plan\n\nContent", encoding="utf-8")

        claude_installation = FakeClaudeInstallation.for_test(
            plans_dir_path=plans_dir,
            session_slugs={session_id: [plan_slug]},
            plans={plan_slug: "# Test Plan\n\nContent"},
        )

        # FakeGit: 0 commits ahead of parent-branch, 5 ahead of main
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            commits_ahead={
                (tmp_path, "parent-branch"): 0,
                (tmp_path, "main"): 5,
            },
        )

        # FakeBranchManager with parent configured
        branch_manager = FakeBranchManager(
            parent_branches={"feature-branch": "parent-branch"},
        )

        hook_input = _gather_inputs(
            session_id=session_id,
            repo_root=tmp_path,
            github_planning_enabled=True,
            claude_installation=claude_installation,
            git=git,
            branch_manager=branch_manager,
            global_config=None,
        )

        # Should use parent-branch (0 commits ahead), not main (5 commits ahead)
        assert hook_input.branch_has_commits is False

    def test_falls_back_to_trunk_when_no_parent(self, tmp_path: Path) -> None:
        """When no Graphite parent exists, fall back to trunk for commit counting."""
        session_id = "session-abc123"
        plan_slug = "test-plan"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create plan file so needs_blocking_message is True
        plans_dir = tmp_path / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / f"{plan_slug}.md"
        plan_file.write_text("# Test Plan\n\nContent", encoding="utf-8")

        claude_installation = FakeClaudeInstallation.for_test(
            plans_dir_path=plans_dir,
            session_slugs={session_id: [plan_slug]},
            plans={plan_slug: "# Test Plan\n\nContent"},
        )

        # FakeGit: 3 commits ahead of main (trunk)
        git = FakeGit(
            current_branches={tmp_path: "feature-branch"},
            commits_ahead={(tmp_path, "main"): 3},
        )

        # FakeBranchManager with NO parent configured (plain Git mode)
        branch_manager = FakeBranchManager()

        hook_input = _gather_inputs(
            session_id=session_id,
            repo_root=tmp_path,
            github_planning_enabled=True,
            claude_installation=claude_installation,
            git=git,
            branch_manager=branch_manager,
            global_config=None,
        )

        # Should fall back to trunk (main, 3 commits ahead)
        assert hook_input.branch_has_commits is True
