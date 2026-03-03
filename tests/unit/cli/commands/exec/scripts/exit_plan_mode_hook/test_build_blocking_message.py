"""Tests for the pure build_blocking_message() function."""

from pathlib import Path

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import build_blocking_message


class TestBuildBlockingMessage:
    """Tests for the pure build_blocking_message() function."""

    def test_contains_required_elements(self) -> None:
        """Message contains all required elements for the new menu."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "PLAN SAVE PROMPT" in message
        assert "AskUserQuestion" in message
        assert "Implement here" in message
        assert "Save as draft PR" in message
        assert "Save and dispatch" in message
        assert "View/Edit the Plan" in message
        assert "/erk:plan-save" in message
        assert "Do NOT call ExitPlanMode" in message
        assert "erk exec marker create --session-id session-123" in message
        assert "exit-plan-mode-hook.implement-now" in message
        assert "If user chooses 'Implement here':" in message
        assert "If user chooses 'Save as draft PR':" in message
        assert "If user chooses 'Save and dispatch':" in message

    def test_save_and_dispatch_instruction_block(self) -> None:
        """Save and dispatch option runs plan-save then pr-dispatch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "If user chooses 'Save and dispatch':" in message
        assert "/erk:pr-dispatch" in message

    def test_includes_header_instruction(self) -> None:
        """Message includes header instruction for AskUserQuestion."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="P4535-add-feature",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name="erk-slot-02",
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert 'header: "Plan Action"' in message

    def test_trunk_branch_main_shows_warning(self) -> None:
        """Warning shown when on main branch."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="main",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "View/Edit the Plan" in message
        assert "Open plan in editor" in message

    def test_implement_here_option_included(self) -> None:
        """Option 'Implement here' is included with instruction block."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "Implement here" in message
        assert "If user chooses 'Implement here':" in message
        assert "Do NOT run 'erk exec setup-impl' or create a new branch" in message
        assert f"Read the plan from: {plan_path}" in message
        assert "erk pr submit" in message

    def test_edit_plan_instructions_include_path(self) -> None:
        """Edit plan instructions include the plan file path for GUI editors."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=None,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title="Add Feature X",
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "\U0001f4cb Add Feature X" in message
        assert "What would you like to do with this plan?" in message

    def test_includes_statusline_context_with_all_fields(self) -> None:
        """Question includes statusline-style context with all fields."""
        plan_path = Path.home() / ".claude" / "plans" / "session-123.md"
        message = build_blocking_message(
            session_id="session-123",
            current_branch="P4224-add-feature",
            plan_file_path=plan_path,
            plan_title="Add Feature X",
            worktree_name="erk-slot-02",
            pr_number=4230,
            plan_number=4224,
            editor=None,
        )
        # Title should be present
        assert "\U0001f4cb Add Feature X" in message
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name="erk-slot-02",
            pr_number=None,
            plan_number=4224,
            editor=None,
        )
        # No title emoji
        assert "\U0001f4cb" not in message
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
            plan_file_path=None,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        # Should still have the basic question
        assert "What would you like to do with this plan?" in message
        # But no context
        assert "\U0001f4cb" not in message
        assert "(wt:" not in message
        assert "(br:" not in message

    def test_tui_editor_vim_shows_manual_instructions(self) -> None:
        """When editor=vim, message tells user to open in separate terminal."""
        plan_path = Path("/home/user/.claude/plans/my-plan.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=plan_path,
            plan_title="My Plan",
            worktree_name=None,
            pr_number=None,
            plan_number=None,
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
            plan_file_path=None,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "DISPLAY PLAN" not in message
        # Should still have the save prompt
        assert "PLAN SAVE PROMPT" in message

    def test_new_menu_options(self) -> None:
        """New menu has correct 4 options."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert '  1. "Implement here"' in message
        assert '  2. "Save as draft PR"' in message
        assert '  3. "Save and dispatch"' in message
        assert '  4. "View/Edit the Plan"' in message

    def test_old_options_not_present(self) -> None:
        """Old menu options are no longer present."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "Create a plan PR on new branch" not in message
        assert "Create a plan PR on the current branch" not in message
        assert "Just implement on the current branch without creating a PR." not in message

    def test_instruction_blocks_use_new_labels(self) -> None:
        """Instruction blocks use new option labels."""
        plan_path = Path("/home/user/.claude/plans/session-123.md")
        message = build_blocking_message(
            session_id="session-123",
            current_branch="feature-branch",
            plan_file_path=plan_path,
            plan_title=None,
            worktree_name=None,
            pr_number=None,
            plan_number=None,
            editor=None,
        )
        assert "If user chooses 'Implement here':" in message
        assert "If user chooses 'Save as draft PR':" in message
        assert "If user chooses 'Save and dispatch':" in message
        assert "If user chooses 'View/Edit the Plan':" in message
        # Old labels absent
        assert "If user chooses 'Create a plan PR on new branch':" not in message
        assert "If user chooses 'Create a plan PR on the current branch':" not in message
