"""Tests for erk plan list command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        author="test-user",
    )


def test_plan_list_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    plan1 = Plan(
        plan_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    plan2 = Plan(
        plan_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeGitHub(issues=[plan_to_issue(plan1), plan_to_issue(plan2)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue 1" in result.output
        assert "#2" in result.output
        assert "Issue 2" in result.output


def test_plan_list_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    open_plan = Plan(
        plan_identifier="1",
        title="Open Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_plan = Plan(
        plan_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        github = FakeGitHub(issues=[plan_to_issue(open_plan), plan_to_issue(closed_plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--state", "open"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Open Issue" in result.output
        assert "#2" not in result.output


def test_plan_list_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    plan_with_both = Plan(
        plan_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    plan_with_one = Plan(
        plan_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(plan_with_both), 2: plan_to_issue(plan_with_one)}
        )
        github = FakeGitHub(issues=[plan_to_issue(plan_with_both), plan_to_issue(plan_with_one)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(
            cli,
            ["plan", "list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Found 1 plan(s)" in result.output
        assert "#1" in result.output
        assert "Issue with both labels" in result.output
        assert "#2" not in result.output


def test_plan_list_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    plans_dict: dict[int, IssueInfo] = {}
    issues_list: list[IssueInfo] = []
    for i in range(1, 6):
        plan = Plan(
            plan_identifier=str(i),
            title=f"Issue {i}",
            body="",
            state=PlanState.OPEN,
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
        )
        issue = plan_to_issue(plan)
        plans_dict[i] = issue
        issues_list.append(issue)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues=plans_dict)
        github = FakeGitHub(issues=issues_list)
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--limit", "2"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output


def test_plan_list_empty_results() -> None:
    """Test querying with filters that match no issues."""
    plan = Plan(
        plan_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeGitHub(issues=[plan_to_issue(plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--state", "closed"], obj=ctx)

        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output


def test_plan_list_runs_flag_shows_run_columns() -> None:
    """Test that --runs flag enables run columns."""
    from erk_shared.github.types import WorkflowRun

    plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '99999'
last_dispatched_node_id: 'WFR_all_flag'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    plan = Plan(
        plan_identifier="200",
        title="Plan with Run",
        body=plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/200",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 200},
    )

    workflow_run = WorkflowRun(
        run_id="99999",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={200: plan_to_issue(plan)})
        github = FakeGitHub(
            issues=[plan_to_issue(plan)],
            workflow_runs_by_node_id={"WFR_all_flag": workflow_run},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--runs"], obj=ctx)

        assert result.exit_code == 0
        assert "#200" in result.output
        assert "99999" in result.output


def test_plan_list_short_runs_flag() -> None:
    """Test that -r short flag works same as --runs."""
    from erk_shared.github.types import WorkflowRun

    plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '88888'
last_dispatched_node_id: 'WFR_short_flag'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    plan = Plan(
        plan_identifier="201",
        title="Plan for short flag test",
        body=plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/201",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 201},
    )

    workflow_run = WorkflowRun(
        run_id="88888",
        status="in_progress",
        conclusion=None,
        branch="master",
        head_sha="def456",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={201: plan_to_issue(plan)})
        github = FakeGitHub(
            issues=[plan_to_issue(plan)],
            workflow_runs_by_node_id={"WFR_short_flag": workflow_run},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "-r"], obj=ctx)

        assert result.exit_code == 0
        assert "#201" in result.output
        assert "88888" in result.output


def test_plan_list_sort_issue_default() -> None:
    """Test that --sort issue (default) returns plans sorted by issue number descending."""
    plan1 = Plan(
        plan_identifier="1",
        title="First Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
    )
    plan2 = Plan(
        plan_identifier="2",
        title="Second Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 2},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeGitHub(issues=[plan_to_issue(plan1), plan_to_issue(plan2)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--sort", "issue"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 2 plan(s)" in result.output
        # Both issues appear (order determined by API, not by sorting since "issue" sort
        # uses the natural API order which is already by issue number descending)
        assert "#1" in result.output
        assert "#2" in result.output


def test_plan_list_sort_activity_with_local_branch() -> None:
    """Test that --sort activity puts plans with recent local branch activity first."""
    from erk_shared.git.abc import WorktreeInfo
    from tests.test_utils.env_helpers import erk_isolated_fs_env

    # Plan 1: older issue, but has local branch with recent activity
    plan1 = Plan(
        plan_identifier="1",
        title="Older Issue with Activity",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
    )
    # Plan 2: newer issue, no local branch
    plan2 = Plan(
        plan_identifier="2",
        title="Newer Issue no Activity",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 2},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/issue.json for plan 1
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-for-issue-1"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json linking worktree to issue 1
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 1, "issue_url": "https://github.com/owner/repo/issues/1", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Build FakeGit with worktree and branch commit times
        from erk_shared.git.fake import FakeGit

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-for-issue-1", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            trunk_branches={env.cwd: "main"},
            branch_last_commit_times={
                "feature-for-issue-1": "2025-01-20T12:00:00+00:00",
            },
        )

        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeGitHub(issues=[plan_to_issue(plan1), plan_to_issue(plan2)])
        ctx = build_workspace_test_context(env, git=git, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--sort", "activity"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Found 2 plan(s)" in result.output

        # Plan 1 (with activity) should appear before Plan 2 (no activity)
        # Check order by finding positions in output
        pos1 = result.output.find("Older Issue with Activity")
        pos2 = result.output.find("Newer Issue no Activity")
        assert pos1 < pos2, (
            f"Plan with activity should appear first. "
            f"pos1={pos1}, pos2={pos2}, output={result.output}"
        )


def test_plan_list_sort_activity_orders_by_recency() -> None:
    """Test that --sort activity orders multiple local branches by recency."""
    from erk_shared.git.abc import WorktreeInfo
    from tests.test_utils.env_helpers import erk_isolated_fs_env

    # Plan 1: has local branch with older commit
    plan1 = Plan(
        plan_identifier="1",
        title="Issue with Older Commit",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
    )
    # Plan 2: has local branch with newer commit
    plan2 = Plan(
        plan_identifier="2",
        title="Issue with Newer Commit",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 2},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name

        # Create worktree for issue 1
        wt1 = repo_dir / "feature-for-issue-1"
        wt1.mkdir(parents=True)
        impl1 = wt1 / ".impl"
        impl1.mkdir()
        (impl1 / "issue.json").write_text(
            '{"issue_number": 1, "issue_url": "https://github.com/owner/repo/issues/1", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Create worktree for issue 2
        wt2 = repo_dir / "feature-for-issue-2"
        wt2.mkdir(parents=True)
        impl2 = wt2 / ".impl"
        impl2.mkdir()
        (impl2 / "issue.json").write_text(
            '{"issue_number": 2, "issue_url": "https://github.com/owner/repo/issues/2", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Build FakeGit - issue 2's branch has MORE RECENT commit
        from erk_shared.git.fake import FakeGit

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt1, branch="feature-for-issue-1", is_root=False),
                    WorktreeInfo(path=wt2, branch="feature-for-issue-2", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            trunk_branches={env.cwd: "main"},
            branch_last_commit_times={
                "feature-for-issue-1": "2025-01-20T10:00:00+00:00",  # Older commit
                "feature-for-issue-2": "2025-01-20T14:00:00+00:00",  # Newer commit
            },
        )

        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeGitHub(issues=[plan_to_issue(plan1), plan_to_issue(plan2)])
        ctx = build_workspace_test_context(env, git=git, issues=issues, github=github)

        result = runner.invoke(cli, ["plan", "list", "--sort", "activity"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Found 2 plan(s)" in result.output

        # Plan 2 (newer commit) should appear before Plan 1 (older commit)
        pos1 = result.output.find("Issue with Older Commit")
        pos2 = result.output.find("Issue with Newer Commit")
        assert pos2 < pos1, (
            f"Plan with newer commit should appear first. "
            f"pos1={pos1}, pos2={pos2}, output={result.output}"
        )
