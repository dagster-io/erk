"""Integration tests that verify the full exit-plan-mode hook works.

These tests use ErkContext.for_test() injection. The .erk/ directory
is created in tmp_path to mark it as a managed project.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import exit_plan_mode_hook
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.claude_installation.fake import FakeClaudeInstallation
from erk_shared.gateway.git.fake import FakeGit


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
        """Verify plan-saved marker blocks exit but is preserved for subsequent calls.

        The marker is preserved so subsequent ExitPlanMode calls continue to block
        with "session complete" instead of prompting the user again (which would
        cause duplicate plan creation if the agent ignores the block).
        """
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
        assert "Plan PR already created" in result.output
        assert plan_saved_marker.exists()  # Marker preserved for subsequent calls

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
        """Verify objective-context marker is deleted but plan-saved marker preserved."""
        runner = CliRunner()
        session_id = "session-abc123"

        # Create .erk/ to mark as managed project
        (tmp_path / ".erk").mkdir()

        # Create both plan-saved and objective-context markers
        marker_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
        marker_dir.mkdir(parents=True)
        plan_saved_marker = marker_dir / "exit-plan-mode-hook.plan-saved.marker"
        plan_saved_marker.touch()
        objective_context_marker = marker_dir / "objective-context.marker"
        objective_context_marker.write_text("3679", encoding="utf-8")

        # Inject via ErkContext - NO mocking needed
        ctx = ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)

        stdin_data = json.dumps({"session_id": session_id})
        result = runner.invoke(exit_plan_mode_hook, input=stdin_data, obj=ctx)

        assert result.exit_code == 2  # Block
        assert "Plan PR already created" in result.output
        assert plan_saved_marker.exists()  # Marker preserved
        assert not objective_context_marker.exists()  # But objective marker deleted

    def test_branch_manager_used_for_pr_lookup(self, tmp_path: Path) -> None:
        """Verify branch_manager is created and used correctly for PR lookups.

        Regression test for issue #4238: create_branch_manager was called with
        swapped positional arguments (github and graphite were reversed), causing
        AttributeError: 'RealGitHub' object has no attribute 'get_prs_from_graphite'.

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
