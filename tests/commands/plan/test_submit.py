"""Tests for erk plan submit command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_submit_exits_cleanly_when_parent_branch_untracked() -> None:
    """Test that submit fails gracefully when stacking on untracked Graphite branch.

    When stacking a plan on a parent branch that exists locally but isn't tracked
    with Graphite, the command should exit with a friendly error message instead
    of raising an exception.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create an issue with erk-plan label
        issue = IssueInfo(
            number=123,
            title="[erk-plan] Test Plan",
            body="Test plan body",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/123",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            author="testuser",
        )
        issues = FakeGitHubIssues(issues={123: issue})

        # Configure git with the untracked parent branch existing on remote
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "untracked-parent"},
            local_branches={env.cwd: ["main", "untracked-parent"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            # Remote branches must be in format "remote/branch"
            remote_branches={env.cwd: ["origin/main", "origin/untracked-parent"]},
        )

        # Configure Graphite with main tracked but NOT untracked-parent
        # This is the key setup: parent branch exists but isn't tracked by Graphite
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=[],
                    is_trunk=True,
                    commit_sha=None,
                ),
                # Note: untracked-parent is intentionally NOT in branches dict
                # so is_branch_tracked() returns False for it
            },
        )

        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            issues=issues,
            use_graphite=True,  # Enable Graphite mode
        )

        # Run the submit command with --base pointing to the untracked branch
        result = runner.invoke(
            cli, ["plan", "submit", "123", "--base", "untracked-parent"], obj=ctx
        )

        # Should exit with code 1 (not an exception traceback)
        assert result.exit_code == 1

        # Should show friendly error message with remediation steps
        assert "not tracked by Graphite" in result.output
        assert "untracked-parent" in result.output
        assert "gt checkout" in result.output
        assert "gt track" in result.output

        # Should NOT show a traceback
        assert "Traceback" not in result.output


def test_submit_succeeds_when_parent_branch_tracked() -> None:
    """Test that submit works when parent branch is tracked by Graphite.

    This is a positive control test to ensure the tracking check doesn't
    break the happy path.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create an issue with erk-plan label
        issue = IssueInfo(
            number=456,
            title="[erk-plan] Test Plan",
            body="Test plan body",
            state="OPEN",
            url="https://github.com/test-owner/test-repo/issues/456",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            author="testuser",
        )
        issues = FakeGitHubIssues(issues={456: issue})

        # Configure git with the tracked parent branch existing on remote
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "tracked-parent"},
            local_branches={env.cwd: ["main", "tracked-parent"]},
            default_branches={env.cwd: "main"},
            remote_urls={(env.cwd, "origin"): "https://github.com/test-owner/test-repo.git"},
            # Remote branches must be in format "remote/branch"
            remote_branches={env.cwd: ["origin/main", "origin/tracked-parent"]},
            repository_roots={env.cwd: env.cwd},
        )

        # Configure Graphite with tracked-parent tracked
        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["tracked-parent"],
                    is_trunk=True,
                    commit_sha=None,
                ),
                "tracked-parent": BranchMetadata(
                    name="tracked-parent",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
            },
        )

        github = FakeGitHub(
            authenticated=True,
            polled_run_id="12345",  # For workflow dispatch polling
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            issues=issues,
            use_graphite=True,  # Enable Graphite mode
        )

        # Run the submit command with --base pointing to a tracked branch
        result = runner.invoke(cli, ["plan", "submit", "456", "--base", "tracked-parent"], obj=ctx)

        # Should NOT fail with untracked branch error
        assert "not tracked by Graphite" not in result.output
