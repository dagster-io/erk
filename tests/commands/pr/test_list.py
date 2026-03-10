"""Tests for erk pr list command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.context_builders import (
    build_fake_plan_list_service,
    build_workspace_test_context,
)
from tests.test_utils.env_helpers import erk_inmem_env


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.pr_identifier),
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
        pr_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    plan2 = Plan(
        pr_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])
        plan_service = build_fake_plan_list_service([plan1, plan2])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 2 PR(s)" in result.output
        assert "#1" in result.output
        assert "#2" in result.output


def test_plan_list_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    open_plan = Plan(
        pr_identifier="1",
        title="Open Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    closed_plan = Plan(
        pr_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(open_plan), 2: plan_to_issue(closed_plan)}
        )
        github = FakeLocalGitHub(issues_data=[plan_to_issue(open_plan), plan_to_issue(closed_plan)])
        plan_service = build_fake_plan_list_service([open_plan, closed_plan])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list", "--state", "open"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 1 PR(s)" in result.output
        assert "#1" in result.output
        assert "#2" not in result.output


def test_plan_list_filter_by_labels() -> None:
    """Test filtering plan issues by labels with AND logic."""
    plan_with_both = Plan(
        pr_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )
    plan_with_one = Plan(
        pr_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(plan_with_both), 2: plan_to_issue(plan_with_one)}
        )
        github = FakeLocalGitHub(
            issues_data=[plan_to_issue(plan_with_both), plan_to_issue(plan_with_one)]
        )
        plan_service = build_fake_plan_list_service([plan_with_both, plan_with_one])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(
            cli,
            ["pr", "list", "--label", "erk-plan", "--label", "erk-queue"],
            obj=ctx,
        )

        assert result.exit_code == 0
        assert "Found 1 PR(s)" in result.output
        assert "#1" in result.output
        assert "#2" not in result.output


def test_plan_list_with_limit() -> None:
    """Test limiting the number of returned plan issues."""
    plans_dict: dict[int, IssueInfo] = {}
    issues_list: list[IssueInfo] = []
    all_plans: list[Plan] = []
    for i in range(1, 6):
        plan = Plan(
            pr_identifier=str(i),
            title=f"Issue {i}",
            body="",
            state=PlanState.OPEN,
            url=f"https://github.com/owner/repo/issues/{i}",
            labels=["erk-pr", "erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, i, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        issue = plan_to_issue(plan)
        plans_dict[i] = issue
        issues_list.append(issue)
        all_plans.append(plan)

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues=plans_dict)
        github = FakeLocalGitHub(issues_data=issues_list)
        plan_service = build_fake_plan_list_service(all_plans)
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list", "--limit", "2"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 2 PR(s)" in result.output


def test_plan_list_empty_results() -> None:
    """Test querying with filters that match no issues."""
    plan = Plan(
        pr_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan)])
        plan_service = build_fake_plan_list_service([plan])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list", "--state", "closed"], obj=ctx)

        assert result.exit_code == 0
        assert "No PRs found matching the criteria" in result.output


def test_plan_list_run_columns_always_shown() -> None:
    """Test that run columns are always shown (runs are always enabled)."""
    from erk_shared.gateway.github.types import WorkflowRun

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
        pr_identifier="200",
        title="Plan with Run",
        body=plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/200",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 200},
        objective_id=None,
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
        github = FakeLocalGitHub(
            issues_data=[plan_to_issue(plan)],
            workflow_runs_by_node_id={"WFR_all_flag": workflow_run},
        )
        plan_service = build_fake_plan_list_service(
            [plan],
            workflow_runs={200: workflow_run},
        )
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "#200" in result.output
        assert "99999" in result.output


def test_plan_list_sort_issue_default() -> None:
    """Test that --sort issue (default) returns plans sorted by issue number descending."""
    plan1 = Plan(
        pr_identifier="1",
        title="First Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
        objective_id=None,
    )
    plan2 = Plan(
        pr_identifier="2",
        title="Second Issue",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 2},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])
        plan_service = build_fake_plan_list_service([plan1, plan2])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list", "--sort", "pr"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 2 PR(s)" in result.output
        # Both issues appear (order determined by API, not by sorting since "issue" sort
        # uses the natural API order which is already by issue number descending)
        assert "#1" in result.output
        assert "#2" in result.output


def test_plan_list_sort_activity_with_local_branch() -> None:
    """Test that --sort activity puts plans with recent local branch activity first."""
    from erk_shared.gateway.git.abc import WorktreeInfo
    from tests.test_utils.env_helpers import erk_isolated_fs_env

    # Plan 1: older issue, but has local branch with recent activity
    plan1 = Plan(
        pr_identifier="1",
        title="Older Issue with Activity",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
        objective_id=None,
    )
    # Plan 2: newer issue, no local branch
    plan2 = Plan(
        pr_identifier="2",
        title="Newer Issue no Activity",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 2},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Create worktree directory with branch-scoped impl folder for plan 1
        from erk_shared.impl_folder import get_impl_dir, save_plan_ref

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-for-issue-1"
        feature_wt.mkdir(parents=True)

        # Create branch-scoped .erk/impl-context/<branch>/ with plan ref
        branch_name = "P1-feature-for-issue-1"
        impl_dir = get_impl_dir(feature_wt, branch_name=branch_name)
        impl_dir.mkdir(parents=True, exist_ok=True)
        save_plan_ref(
            impl_dir,
            provider="github",
            plan_id="1",
            url="https://github.com/owner/repo/issues/1",
            labels=(),
            objective_id=None,
            node_ids=None,
        )

        # Build FakeGit with worktree and branch commit times
        from tests.fakes.gateway.git import FakeGit

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch=branch_name, is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            trunk_branches={env.cwd: "main"},
            current_branches={feature_wt: branch_name},
            branch_commits_with_authors={
                (env.cwd, branch_name, "main", 1): [
                    {
                        "hash": "abc123",
                        "timestamp": "2025-01-20T12:00:00+00:00",
                        "author": "test-user",
                        "message": "test commit",
                    }
                ],
            },
        )

        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])
        plan_service = build_fake_plan_list_service([plan1, plan2])
        ctx = build_workspace_test_context(
            env, git=git, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list", "--sort", "activity"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Found 2 PR(s)" in result.output

        # Plan 1 (with activity) should appear before Plan 2 (no activity)
        # Use plan IDs since title column is no longer displayed
        lines = result.output.split("\n")
        plan_lines = [line for line in lines if "#1" in line or "#2" in line]
        assert len(plan_lines) >= 2
        first_with_1 = next(i for i, line in enumerate(plan_lines) if "#1" in line)
        first_with_2 = next(i for i, line in enumerate(plan_lines) if "#2" in line)
        assert first_with_1 < first_with_2, (
            f"Plan #1 (with activity) should appear first. output={result.output}"
        )


def test_plan_list_sort_activity_orders_by_recency() -> None:
    """Test that --sort activity orders multiple local branches by recency."""
    from erk_shared.gateway.git.abc import WorktreeInfo
    from tests.test_utils.env_helpers import erk_isolated_fs_env

    # Plan 1: has local branch with older commit
    plan1 = Plan(
        pr_identifier="1",
        title="Issue with Older Commit",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
        objective_id=None,
    )
    # Plan 2: has local branch with newer commit
    plan2 = Plan(
        pr_identifier="2",
        title="Issue with Newer Commit",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 2},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        from erk_shared.impl_folder import get_impl_dir, save_plan_ref

        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name

        # Create worktree for issue 1
        wt1 = repo_dir / "feature-for-issue-1"
        wt1.mkdir(parents=True)
        branch1 = "P1-feature-for-issue-1"
        impl1 = get_impl_dir(wt1, branch_name=branch1)
        impl1.mkdir(parents=True, exist_ok=True)
        save_plan_ref(
            impl1,
            provider="github",
            plan_id="1",
            url="https://github.com/owner/repo/issues/1",
            labels=(),
            objective_id=None,
            node_ids=None,
        )

        # Create worktree for issue 2
        wt2 = repo_dir / "feature-for-issue-2"
        wt2.mkdir(parents=True)
        branch2 = "P2-feature-for-issue-2"
        impl2 = get_impl_dir(wt2, branch_name=branch2)
        impl2.mkdir(parents=True, exist_ok=True)
        save_plan_ref(
            impl2,
            provider="github",
            plan_id="2",
            url="https://github.com/owner/repo/issues/2",
            labels=(),
            objective_id=None,
            node_ids=None,
        )

        # Build FakeGit - issue 2's branch has MORE RECENT commit
        from tests.fakes.gateway.git import FakeGit

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt1, branch=branch1, is_root=False),
                    WorktreeInfo(path=wt2, branch=branch2, is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
            trunk_branches={env.cwd: "main"},
            current_branches={wt1: branch1, wt2: branch2},
            branch_commits_with_authors={
                (env.cwd, branch1, "main", 1): [
                    {
                        "hash": "abc123",
                        "timestamp": "2025-01-20T10:00:00+00:00",
                        "author": "test-user",
                        "message": "old commit",
                    }
                ],
                (env.cwd, branch2, "main", 1): [
                    {
                        "hash": "def456",
                        "timestamp": "2025-01-20T14:00:00+00:00",
                        "author": "test-user",
                        "message": "newer commit",
                    }
                ],
            },
        )

        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan1), 2: plan_to_issue(plan2)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan1), plan_to_issue(plan2)])
        plan_service = build_fake_plan_list_service([plan1, plan2])
        ctx = build_workspace_test_context(
            env, git=git, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list", "--sort", "activity"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "Found 2 PR(s)" in result.output

        # Plan 2 (newer commit) should appear before Plan 1 (older commit)
        # Use plan IDs since title column is no longer displayed
        lines = result.output.split("\n")
        plan_lines = [line for line in lines if "#1" in line or "#2" in line]
        assert len(plan_lines) >= 2
        first_with_1 = next(i for i, line in enumerate(plan_lines) if "#1" in line)
        first_with_2 = next(i for i, line in enumerate(plan_lines) if "#2" in line)
        assert first_with_2 < first_with_1, (
            f"Plan #2 (newer commit) should appear first. output={result.output}"
        )


def _make_plan_body_with_stage(stage: str) -> str:
    """Create a plan body with lifecycle_stage in plan-header metadata."""
    return (
        "<!-- erk:metadata-block:plan-header -->\n"
        "<details>\n"
        "<summary><code>plan-header</code></summary>\n\n"
        "```yaml\n"
        "schema_version: '2'\n"
        f"lifecycle_stage: '{stage}'\n"
        "```\n"
        "</details>\n"
        "<!-- /erk:metadata-block:plan-header -->"
    )


def test_pr_list_stage_filter() -> None:
    """Test that --stage filters plans by lifecycle stage."""
    # Plan 1: lifecycle_stage=planned via plan-header metadata
    planned_plan = Plan(
        pr_identifier="1",
        title="Planned Issue",
        body=_make_plan_body_with_stage("planned"),
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
        header_fields={"lifecycle_stage": "planned"},
    )
    # Plan 2: lifecycle_stage=impl via plan-header metadata → lifecycle_display resolves to "impl"
    impl_plan = Plan(
        pr_identifier="2",
        title="Impl Issue",
        body=_make_plan_body_with_stage("impl"),
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/2",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
        header_fields={"lifecycle_stage": "impl"},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1: plan_to_issue(planned_plan), 2: plan_to_issue(impl_plan)}
        )
        github = FakeLocalGitHub(
            issues_data=[plan_to_issue(planned_plan), plan_to_issue(impl_plan)]
        )
        plan_service = build_fake_plan_list_service([planned_plan, impl_plan])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        # Filter to only "planned" stage
        result = runner.invoke(cli, ["pr", "list", "--stage", "planned"], obj=ctx)

        assert result.exit_code == 0
        assert "Found 1 PR(s)" in result.output
        assert "#1" in result.output
        assert "#2" not in result.output


def test_pr_list_displays_enrichment_warnings() -> None:
    """Test that enrichment warnings from PlanListData are displayed to the user."""
    plan = Plan(
        pr_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan)])
        plan_service = build_fake_plan_list_service(
            [plan],
            warnings=(
                "GraphQL enrichment failed for 2/5 PRs "
                "— branch, draft status, and check indicators may be missing",
            ),
        )
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "Warning:" in result.output
        assert "GraphQL enrichment failed for 2/5 PRs" in result.output


def test_pr_list_no_warnings_when_enrichment_succeeds() -> None:
    """Test that no warnings are displayed when enrichment succeeds fully."""
    plan = Plan(
        pr_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeLocalGitHub(issues_data=[plan_to_issue(plan)])
        plan_service = build_fake_plan_list_service([plan])
        ctx = build_workspace_test_context(
            env, issues=issues, github=github, plan_list_service=plan_service
        )

        result = runner.invoke(cli, ["pr", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "Warning:" not in result.output
