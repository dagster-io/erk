"""Tests for erk learn tracking behavior.

Layer 4 (Business Logic Tests): Tests learn command tracking using fakes.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.issues.fake import FakeGitHubIssues
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.github_helpers import create_test_issue


def test_no_interactive_tracks_evaluation() -> None:
    """Non-interactive mode posts tracking comment."""
    issue = create_test_issue(number=42, title="Plan #42", body="content")
    issues = FakeGitHubIssues(issues={42: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["learn", "42", "--no-interactive", "--session-id=test-session-123"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify tracking comment was posted
        assert len(issues.added_comments) == 1
        issue_num, comment_body, _comment_id = issues.added_comments[0]
        assert issue_num == 42
        assert "learn-invoked" in comment_body
        assert "test-session-123" in comment_body


def test_json_mode_tracks_evaluation() -> None:
    """JSON output mode also tracks evaluation."""
    issue = create_test_issue(number=100, title="Plan #100", body="content")
    issues = FakeGitHubIssues(issues={100: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["learn", "100", "--json", "--session-id=session-456"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify tracking comment was posted
        assert len(issues.added_comments) == 1


def test_no_track_suppresses_tracking() -> None:
    """--no-track flag prevents tracking even in non-interactive mode."""
    issue = create_test_issue(number=42, title="Plan #42", body="content")
    issues = FakeGitHubIssues(issues={42: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["learn", "42", "--no-interactive", "--no-track"],
            obj=ctx,
        )

        assert result.exit_code == 0

        # Verify NO tracking comment was posted
        assert len(issues.added_comments) == 0


def test_requires_issue_number() -> None:
    """Command fails if no issue number provided and branch doesn't match."""
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["learn", "--no-interactive"], obj=ctx)

        # Should fail because no issue number provided
        assert result.exit_code == 1
        assert "No issue specified" in result.output or "could not infer" in result.output
