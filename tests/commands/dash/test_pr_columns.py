"""Tests for PR status column display in plan list command.

Tests PR emoji display (open 👀, draft 🚧, merged 🎉, closed ⛔, conflict 💥).
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.types import PullRequestInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_plan_list_pr_column_open_pr() -> None:
    """Test PR column displays open PR with 👀 emoji."""
    # Arrange
    plan = Plan(
        plan_identifier="100",
        title="Plan with Open PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/100",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 100},
    )

    pr = PullRequestInfo(
        number=200,
        state="OPEN",
        url="https://github.com/owner/repo/pull/200",
        is_draft=False,
        title="PR for issue 100",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={100: plan_to_issue(plan)})
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={100: [pr]},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - PR columns are always visible now
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#200[/link] 👀
        assert "#200" in result.output
        assert "👀" in result.output  # Open PR emoji
        assert "✅" in result.output  # Checks passing


def test_plan_list_pr_column_draft_pr() -> None:
    """Test PR column displays draft PR with 🚧 emoji."""
    # Arrange
    plan = Plan(
        plan_identifier="101",
        title="Plan with Draft PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/101",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 101},
    )

    pr = PullRequestInfo(
        number=201,
        state="DRAFT",
        url="https://github.com/owner/repo/pull/201",
        is_draft=True,
        title="Draft PR for issue 101",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={101: plan_to_issue(plan)})
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={101: [pr]},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - PR columns are always visible now
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#201[/link] 🚧
        assert "#201" in result.output
        assert "🚧" in result.output  # Draft PR emoji
        assert "🔄" in result.output  # Checks pending


def test_plan_list_pr_column_merged_pr() -> None:
    """Test PR column displays merged PR with 🎉 emoji."""
    # Arrange
    plan = Plan(
        plan_identifier="102",
        title="Plan with Merged PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/102",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 102},
    )

    pr = PullRequestInfo(
        number=202,
        state="MERGED",
        url="https://github.com/owner/repo/pull/202",
        is_draft=False,
        title="Merged PR for issue 102",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={102: plan_to_issue(plan)})
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={102: [pr]},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - PR columns are always visible now
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#202[/link] 🎉
        assert "#202" in result.output
        assert "🎉" in result.output  # Merged PR emoji
        assert "✅" in result.output  # Checks passing


def test_plan_list_pr_column_closed_pr() -> None:
    """Test PR column displays closed PR with ⛔ emoji."""
    # Arrange
    plan = Plan(
        plan_identifier="103",
        title="Plan with Closed PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/103",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 103},
    )

    pr = PullRequestInfo(
        number=203,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/203",
        is_draft=False,
        title="Closed PR for issue 103",
        checks_passing=False,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={103: plan_to_issue(plan)})
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={103: [pr]},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - PR columns are always visible now
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#203[/link] ⛔
        assert "#203" in result.output
        assert "⛔" in result.output  # Closed PR emoji
        assert "🚫" in result.output  # Checks failing


def test_plan_list_pr_column_with_conflicts() -> None:
    """Test PR column shows conflict indicator 💥 for open/draft PRs with conflicts."""
    # Arrange
    plan = Plan(
        plan_identifier="104",
        title="Plan with Conflicted PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/104",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 104},
    )

    pr = PullRequestInfo(
        number=204,
        state="OPEN",
        url="https://github.com/owner/repo/pull/204",
        is_draft=False,
        title="Conflicted PR for issue 104",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=True,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={104: plan_to_issue(plan)})
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={104: [pr]},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - PR columns are always visible now
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#204[/link] 👀💥
        assert "#204" in result.output
        assert "👀" in result.output  # Open PR emoji
        assert "💥" in result.output  # Conflict indicator


def test_plan_list_pr_column_multiple_prs_prefers_open() -> None:
    """Test PR column shows most recent open PR when multiple PRs exist."""
    # Arrange
    plan = Plan(
        plan_identifier="105",
        title="Plan with Multiple PRs",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/105",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 105},
    )

    # Older closed PR
    closed_pr = PullRequestInfo(
        number=205,
        state="CLOSED",
        url="https://github.com/owner/repo/pull/205",
        is_draft=False,
        title="Old closed PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )

    # Recent open PR (should be selected)
    open_pr = PullRequestInfo(
        number=206,
        state="OPEN",
        url="https://github.com/owner/repo/pull/206",
        is_draft=False,
        title="Recent open PR",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={105: plan_to_issue(plan)})
        # PRs already sorted by created_at descending
        github = FakeGitHub(
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={105: [open_pr, closed_pr]},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - PR columns are always visible now
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # PR cell uses Rich markup: [link=url]#206[/link] 👀
        assert "#206" in result.output  # Shows open PR, not closed
        assert "👀" in result.output  # Open PR emoji


def test_plan_list_pr_column_no_pr_linked() -> None:
    """Test PR column shows '-' when no PR is linked to issue."""
    # Arrange
    plan = Plan(
        plan_identifier="106",
        title="Plan without PR",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/106",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 106},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={106: plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan)])
        # No PR linkages configured
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#106" in result.output
        # PR and Checks columns should both show "-"
        # Can't easily assert the exact column position, but verifying no emojis appear
        assert "👀" not in result.output
        assert "🚧" not in result.output
        assert "🎉" not in result.output
        assert "⛔" not in result.output
