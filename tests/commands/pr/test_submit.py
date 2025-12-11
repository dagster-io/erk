"""Tests for erk pr submit command.

These tests verify the CLI layer behavior of the submit command.
The command now uses Python orchestration with two-layer architecture:
- Core layer: git push + gh pr create (via execute_core_submit)
- Graphite layer: Optional enhancement (via execute_graphite_enhance)
"""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.gt.events import CompletionEvent
from erk_shared.integrations.gt.types import FinalizeResult, PostAnalysisError
from erk_shared.integrations.pr.types import (
    CoreSubmitError,
    CoreSubmitResult,
    GraphiteSkipped,
)

from erk.cli.commands.pr import pr_group
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_submit_fails_when_claude_not_available() -> None:
    """Test that command fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output
        assert "claude.com/download" in result.output


@patch("erk.cli.commands.pr.submit_cmd.execute_core_submit")
def test_pr_submit_fails_when_core_submit_returns_error(
    mock_core_submit: Mock,
) -> None:
    """Test that command fails when core submit returns CoreSubmitError."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Mock core_submit to return an error
        mock_core_submit.return_value = iter(
            [
                CompletionEvent(
                    CoreSubmitError(
                        success=False,
                        error_type="github_auth_failed",
                        message="GitHub CLI is not authenticated. Run 'gh auth login'.",
                        details={},
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "not authenticated" in result.output


@patch("erk.cli.commands.pr.submit_cmd.execute_diff_extraction")
@patch("erk.cli.commands.pr.submit_cmd.execute_core_submit")
def test_pr_submit_fails_when_diff_extraction_fails(
    mock_core_submit: Mock,
    mock_diff_extraction: Mock,
) -> None:
    """Test that command fails when diff extraction returns None."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Mock core submit to succeed
        mock_core_submit.return_value = iter(
            [
                CompletionEvent(
                    CoreSubmitResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        branch_name="feature",
                        issue_number=None,
                        was_created=True,
                        message="Created PR #123",
                    )
                )
            ]
        )

        # Mock diff extraction to fail
        mock_diff_extraction.return_value = iter([CompletionEvent(None)])

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to extract diff" in result.output


@patch("erk.cli.commands.pr.submit_cmd.execute_graphite_enhance")
@patch("erk.cli.commands.pr.submit_cmd.execute_diff_extraction")
@patch("erk.cli.commands.pr.submit_cmd.execute_core_submit")
def test_pr_submit_fails_when_commit_message_generation_fails(
    mock_core_submit: Mock,
    mock_diff_extraction: Mock,
    mock_graphite_enhance: Mock,
    tmp_path: Path,
) -> None:
    """Test that command fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        # Create diff file that will be referenced
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff content", encoding="utf-8")

        # Configure executor to fail on prompt
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_error="Claude CLI execution failed",
        )

        # Mock core submit to succeed
        mock_core_submit.return_value = iter(
            [
                CompletionEvent(
                    CoreSubmitResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        branch_name="feature",
                        issue_number=None,
                        was_created=True,
                        message="Created PR #123",
                    )
                )
            ]
        )

        # Mock diff extraction to succeed
        mock_diff_extraction.return_value = iter([CompletionEvent(diff_file)])

        # Mock graphite enhance (should not be called since message gen fails first)
        mock_graphite_enhance.return_value = iter(
            [
                CompletionEvent(
                    GraphiteSkipped(
                        success=True,
                        reason="not_called",
                        message="Not called",
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output


@patch("erk.cli.commands.pr.submit_cmd.execute_finalize")
@patch("erk.cli.commands.pr.submit_cmd.execute_graphite_enhance")
@patch("erk.cli.commands.pr.submit_cmd.execute_diff_extraction")
@patch("erk.cli.commands.pr.submit_cmd.execute_core_submit")
def test_pr_submit_fails_when_finalize_fails(
    mock_core_submit: Mock,
    mock_diff_extraction: Mock,
    mock_graphite_enhance: Mock,
    mock_finalize: Mock,
    tmp_path: Path,
) -> None:
    """Test that command fails when finalize returns an error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        # Create diff file
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff content", encoding="utf-8")

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add feature\n\nThis adds a new feature.",
        )

        # Mock core submit to succeed
        mock_core_submit.return_value = iter(
            [
                CompletionEvent(
                    CoreSubmitResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        branch_name="feature",
                        issue_number=None,
                        was_created=True,
                        message="Created PR #123",
                    )
                )
            ]
        )

        # Mock diff extraction to succeed
        mock_diff_extraction.return_value = iter([CompletionEvent(diff_file)])

        # Mock graphite enhance to skip
        mock_graphite_enhance.return_value = iter(
            [
                CompletionEvent(
                    GraphiteSkipped(
                        success=True,
                        reason="not_tracked",
                        message="Branch not tracked",
                    )
                )
            ]
        )

        # Mock finalize to fail
        mock_finalize.return_value = iter(
            [
                CompletionEvent(
                    PostAnalysisError(
                        success=False,
                        error_type="pr_update_failed",
                        message="Failed to update PR metadata",
                        details={},
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to update PR metadata" in result.output


@patch("erk.cli.commands.pr.submit_cmd.execute_finalize")
@patch("erk.cli.commands.pr.submit_cmd.execute_graphite_enhance")
@patch("erk.cli.commands.pr.submit_cmd.execute_diff_extraction")
@patch("erk.cli.commands.pr.submit_cmd.execute_core_submit")
def test_pr_submit_success(
    mock_core_submit: Mock,
    mock_diff_extraction: Mock,
    mock_graphite_enhance: Mock,
    mock_finalize: Mock,
    tmp_path: Path,
) -> None:
    """Test successful PR submission with all phases completing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        # Create diff file
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff content", encoding="utf-8")

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Add awesome feature\n\nThis PR adds an awesome new feature.",
        )

        # Mock core submit to succeed
        mock_core_submit.return_value = iter(
            [
                CompletionEvent(
                    CoreSubmitResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        branch_name="feature",
                        issue_number=None,
                        was_created=True,
                        message="Created PR #123",
                    )
                )
            ]
        )

        # Mock diff extraction to succeed
        mock_diff_extraction.return_value = iter([CompletionEvent(diff_file)])

        # Mock graphite enhance to skip
        mock_graphite_enhance.return_value = iter(
            [
                CompletionEvent(
                    GraphiteSkipped(
                        success=True,
                        reason="not_tracked",
                        message="Branch not tracked by Graphite",
                    )
                )
            ]
        )

        # Mock finalize to succeed
        mock_finalize.return_value = iter(
            [
                CompletionEvent(
                    FinalizeResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        pr_title="Add awesome feature",
                        graphite_url="https://app.graphite.dev/github/pr/123",
                        branch_name="feature",
                        issue_number=None,
                        message="Successfully updated PR",
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code == 0
        # Verify output contains PR URL
        assert "https://github.com/org/repo/pull/123" in result.output

        # Verify commit message was generated
        assert len(claude_executor.prompt_calls) == 1
        prompt = claude_executor.prompt_calls[0]
        assert "feature" in prompt  # Branch name in context
        assert "main" in prompt  # Parent branch in context


@patch("erk.cli.commands.pr.submit_cmd.execute_finalize")
@patch("erk.cli.commands.pr.submit_cmd.execute_graphite_enhance")
@patch("erk.cli.commands.pr.submit_cmd.execute_diff_extraction")
@patch("erk.cli.commands.pr.submit_cmd.execute_core_submit")
def test_pr_submit_with_no_graphite_flag(
    mock_core_submit: Mock,
    mock_diff_extraction: Mock,
    mock_graphite_enhance: Mock,
    mock_finalize: Mock,
    tmp_path: Path,
) -> None:
    """Test that --no-graphite flag skips Graphite enhancement."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        diff_file = tmp_path / "test.diff"
        diff_file.write_text("diff content", encoding="utf-8")

        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_prompt_output="Title\n\nBody",
        )

        mock_core_submit.return_value = iter(
            [
                CompletionEvent(
                    CoreSubmitResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        branch_name="feature",
                        issue_number=None,
                        was_created=True,
                        message="Created PR #123",
                    )
                )
            ]
        )

        mock_diff_extraction.return_value = iter([CompletionEvent(diff_file)])

        mock_finalize.return_value = iter(
            [
                CompletionEvent(
                    FinalizeResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        pr_title="Title",
                        graphite_url="",
                        branch_name="feature",
                        issue_number=None,
                        message="Successfully updated PR",
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit", "--no-graphite"], obj=ctx)

        assert result.exit_code == 0
        # Graphite enhance should not have been called
        mock_graphite_enhance.assert_not_called()
