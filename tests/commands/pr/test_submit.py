"""Tests for erk pr submit command.

These tests verify the CLI layer behavior of the submit command.
The command now uses Python orchestration (preflight -> generate -> finalize)
rather than delegating to a Claude slash command.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.gt.events import CompletionEvent
from erk_shared.integrations.gt.types import (
    FinalizeResult,
    PostAnalysisError,
    PreAnalysisError,
    PreflightResult,
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


@patch("erk.cli.commands.pr.submit_cmd.execute_preflight")
def test_pr_submit_fails_when_preflight_returns_pre_analysis_error(
    mock_preflight: Mock,
) -> None:
    """Test that command fails when preflight returns PreAnalysisError."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Mock preflight to return an error
        mock_preflight.return_value = iter(
            [
                CompletionEvent(
                    PreAnalysisError(
                        success=False,
                        error_type="gt_not_authenticated",
                        message="Graphite CLI (gt) is not authenticated",
                        details={"authenticated": False},
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "not authenticated" in result.output


@patch("erk.cli.commands.pr.submit_cmd.execute_preflight")
def test_pr_submit_fails_when_preflight_returns_post_analysis_error(
    mock_preflight: Mock,
) -> None:
    """Test that command fails when preflight returns PostAnalysisError."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        # Mock preflight to return a submit error
        mock_preflight.return_value = iter(
            [
                CompletionEvent(
                    PostAnalysisError(
                        success=False,
                        error_type="submit_failed",
                        message="Failed to submit branch",
                        details={"branch_name": "feature"},
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "submit" in result.output.lower()


@patch("erk.cli.commands.pr.submit_cmd.execute_finalize")
@patch("erk.cli.commands.pr.submit_cmd.execute_preflight")
def test_pr_submit_fails_when_commit_message_generation_fails(
    mock_preflight: Mock,
    mock_finalize: Mock,
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

        # Mock preflight to succeed
        mock_preflight.return_value = iter(
            [
                CompletionEvent(
                    PreflightResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        graphite_url="https://app.graphite.dev/github/pr/123",
                        branch_name="feature",
                        diff_file=str(diff_file),
                        repo_root=str(tmp_path),
                        current_branch="feature",
                        parent_branch="main",
                        issue_number=None,
                        message="Preflight complete",
                    )
                )
            ]
        )

        ctx = build_workspace_test_context(env, git=git, claude_executor=claude_executor)

        result = runner.invoke(pr_group, ["submit"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output

        # Finalize should not be called when message generation fails
        mock_finalize.assert_not_called()


@patch("erk.cli.commands.pr.submit_cmd.execute_finalize")
@patch("erk.cli.commands.pr.submit_cmd.execute_preflight")
def test_pr_submit_fails_when_finalize_fails(
    mock_preflight: Mock,
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

        # Mock preflight to succeed
        mock_preflight.return_value = iter(
            [
                CompletionEvent(
                    PreflightResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        graphite_url="https://app.graphite.dev/github/pr/123",
                        branch_name="feature",
                        diff_file=str(diff_file),
                        repo_root=str(tmp_path),
                        current_branch="feature",
                        parent_branch="main",
                        issue_number=None,
                        message="Preflight complete",
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
@patch("erk.cli.commands.pr.submit_cmd.execute_preflight")
def test_pr_submit_success(
    mock_preflight: Mock,
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

        # Mock preflight to succeed
        mock_preflight.return_value = iter(
            [
                CompletionEvent(
                    PreflightResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        graphite_url="https://app.graphite.dev/github/pr/123",
                        branch_name="feature",
                        diff_file=str(diff_file),
                        repo_root=str(tmp_path),
                        current_branch="feature",
                        parent_branch="main",
                        issue_number=None,
                        message="Preflight complete",
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
@patch("erk.cli.commands.pr.submit_cmd.execute_preflight")
def test_pr_submit_shows_graphite_url(
    mock_preflight: Mock,
    mock_finalize: Mock,
    tmp_path: Path,
) -> None:
    """Test that Graphite URL is displayed on success."""
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

        mock_preflight.return_value = iter(
            [
                CompletionEvent(
                    PreflightResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        graphite_url="https://app.graphite.dev/github/pr/123",
                        branch_name="feature",
                        diff_file=str(diff_file),
                        repo_root=str(tmp_path),
                        current_branch="feature",
                        parent_branch="main",
                        issue_number=None,
                        message="Preflight complete",
                    )
                )
            ]
        )

        mock_finalize.return_value = iter(
            [
                CompletionEvent(
                    FinalizeResult(
                        success=True,
                        pr_number=123,
                        pr_url="https://github.com/org/repo/pull/123",
                        pr_title="Title",
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
        # Both URLs should be in output
        assert "github.com/org/repo/pull/123" in result.output
        assert "app.graphite.dev" in result.output
