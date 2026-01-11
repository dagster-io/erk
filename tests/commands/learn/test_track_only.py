"""Tests for erk learn --track-only flag.

Layer 4 (Business Logic Tests): Tests learn command --track-only behavior using fakes.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.issues.fake import FakeGitHubIssues
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.github_helpers import create_test_issue


def test_track_only_posts_comment_and_exits() -> None:
    """Track-only mode posts tracking comment without session discovery."""
    issue = create_test_issue(number=42, title="Plan #42", body="content")
    issues = FakeGitHubIssues(issues={42: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(
            cli,
            ["learn", "42", "--track-only", "--session-id=test-session-123"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Learn evaluation tracked" in result.output
        assert "#42" in result.output

        # Verify tracking comment was posted
        assert len(issues.added_comments) == 1
        issue_num, comment_body, _comment_id = issues.added_comments[0]
        assert issue_num == 42
        assert "learn-invoked" in comment_body
        assert "test-session-123" in comment_body


def test_track_only_without_session_id() -> None:
    """Track-only works without session ID."""
    issue = create_test_issue(number=100, title="Plan #100", body="content")
    issues = FakeGitHubIssues(issues={100: issue})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["learn", "100", "--track-only"], obj=ctx)

        assert result.exit_code == 0
        assert "Learn evaluation tracked" in result.output

        # Verify comment was posted
        assert len(issues.added_comments) == 1


def test_track_only_requires_issue_number() -> None:
    """Track-only fails if no issue number provided and branch doesn't match."""
    issues = FakeGitHubIssues(issues={})

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        ctx = build_workspace_test_context(env, issues=issues)

        result = runner.invoke(cli, ["learn", "--track-only"], obj=ctx)

        # Should fail because no issue number provided
        assert result.exit_code == 1
        assert "No issue specified" in result.output or "could not infer" in result.output
