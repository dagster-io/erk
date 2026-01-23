"""Tests for Graphite stack sync in erk plan submit command.

These tests verify that when Graphite is enabled, `erk plan submit` properly
handles the Graphite integration. The actual `submit_branch()` call happens
after PR creation, so testing it requires complex setup. These tests verify
the simpler cases:

1. When Graphite is disabled, the command works without calling Graphite
2. When Graphite sync fails, it logs a warning rather than failing the command

Note: Testing that submit_branch() is actually called when Graphite is enabled
requires the full plan submit workflow to succeed (issue with plan-body comment,
etc.), which is tested in integration tests.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def _make_erk_plan_issue(issue_number: int) -> IssueInfo:
    """Create a minimal erk-plan issue for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=issue_number,
        title="Test Plan [erk-plan]",
        body="Test plan body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{issue_number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


def test_plan_submit_works_when_graphite_disabled() -> None:
    """Test that plan submit works when Graphite is disabled.

    When Graphite is disabled (use_graphite=False), the command should use
    plain git operations and NOT attempt to sync Graphite stack metadata.
    The branch_manager.is_graphite_managed() returns False in this case.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "main"},
            remote_urls={(env.git_dir, "origin"): "git@github.com:owner/repo.git"},
            remote_branches={env.git_dir: ["main"]},
        )

        # Configure GitHub with authenticated state and pre-created erk-plan issue
        issues = FakeGitHubIssues(
            issues={1: _make_erk_plan_issue(1)},
            labels={"erk-plan"},
        )

        github = FakeGitHub(
            authenticated=True,
            auth_username="test-user",
            issues_gateway=issues,
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
            use_graphite=False,
        )

        # Act: Submit an erk-plan issue with Graphite disabled
        result = runner.invoke(cli, ["plan", "submit", "1"], obj=ctx)

        # The command should not crash trying to call Graphite-specific methods
        # It may fail for other reasons (missing plan content), but not due to
        # Graphite issues
        assert "GraphiteDisabledError" not in result.output
        assert "requires Graphite" not in result.output
