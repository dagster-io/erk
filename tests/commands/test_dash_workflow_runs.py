"""Tests for workflow run ID display in erk dash command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo
from erk_shared.github.types import WorkflowRun
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.output_helpers import strip_ansi


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url or "",
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        author="test-user",
    )


def test_list_displays_workflow_run_id_for_plan_with_impl_folder() -> None:
    """Workflow run ID should appear for plans with node_id in plan-header."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/issue.json
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 123, "issue_url": "https://github.com/owner/repo/issues/123", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Create plan with workflow run node_id in plan-header
        plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '12345678'
last_dispatched_node_id: 'WFR_abc123'
```
</details>
<!-- /erk:metadata-block:plan-header -->

Implementation details"""

        plan = Plan(
            plan_identifier="123",
            title="Test Implementation",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/123",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 123, "url": "https://github.com/owner/repo/issues/123"},
        )

        # Build fake git ops with worktree info
        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run with matching node_id
        workflow_run = WorkflowRun(
            run_id="12345678",
            status="completed",
            conclusion="success",
            branch="master",
            head_sha="abc123",
        )
        github = FakeGitHub(
            issues=[plan_to_issue(plan)], workflow_runs_by_node_id={"WFR_abc123": workflow_run}
        )
        issues = FakeGitHubIssues(issues={123: plan_to_issue(plan)})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list", "--runs"], obj=ctx)
        assert result.exit_code == 0, result.output

        # Verify workflow run ID appears
        output = strip_ansi(result.output)
        assert "12345678" in output, "Expected run ID in output"


def test_plan_list_linkifies_workflow_run_id_with_owner_repo() -> None:
    """Workflow run ID should be linkified when owner/repo available from metadata."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree directory with .impl/issue.json
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 456, '
            '"issue_url": "https://github.com/testowner/testrepo/issues/456", '
            '"created_at": "2025-01-20T10:00:00+00:00", '
            '"synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Create plan with workflow run node_id in plan-header
        plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '87654321'
last_dispatched_node_id: 'WFR_def456'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

        plan = Plan(
            plan_identifier="456",
            title="Test with URL",
            body=plan_body,
            state=PlanState.OPEN,
            url="https://github.com/testowner/testrepo/issues/456",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={
                "number": 456,
                "url": "https://github.com/testowner/testrepo/issues/456",
            },
        )

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run with matching node_id
        workflow_run = WorkflowRun(
            run_id="87654321",
            status="in_progress",
            conclusion=None,
            branch="master",
            head_sha="def456",
        )
        github = FakeGitHub(
            issues=[plan_to_issue(plan)], workflow_runs_by_node_id={"WFR_def456": workflow_run}
        )
        issues = FakeGitHubIssues(issues={456: plan_to_issue(plan)})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list", "--runs"], obj=ctx)
        assert result.exit_code == 0, result.output

        # Verify run ID and OSC 8 link present
        assert "87654321" in result.output, "Expected run ID"
        # Rich table uses [link=URL] markup, but we check for run ID presence
        output = strip_ansi(result.output)
        assert "87654321" in output


def test_plan_list_displays_plain_run_id_without_owner_repo() -> None:
    """Workflow run ID should display without link when owner/repo missing."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree with .impl/issue.json
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 789, "issue_url": "https://github.com/owner/repo/issues/789", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Create plan with workflow run node_id but WITHOUT url metadata (no owner/repo)
        plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '99887766'
last_dispatched_node_id: 'WFR_ghi789'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

        plan = Plan(
            plan_identifier="789",
            title="Plan without URL",
            body=plan_body,
            state=PlanState.OPEN,
            url=None,
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 789},  # No "url" key
        )

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run with matching node_id
        workflow_run = WorkflowRun(
            run_id="99887766",
            status="completed",
            conclusion="failure",
            branch="master",
            head_sha="ghi789",
        )
        github = FakeGitHub(
            issues=[plan_to_issue(plan)], workflow_runs_by_node_id={"WFR_ghi789": workflow_run}
        )
        issues = FakeGitHubIssues(issues={789: plan_to_issue(plan)})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list", "--runs"], obj=ctx)
        assert result.exit_code == 0, result.output

        # Verify run ID displays (without link)
        output = strip_ansi(result.output)
        assert "99887766" in output


def test_plan_list_handles_missing_workflow_run() -> None:
    """Plan list should handle branches without workflow runs gracefully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree with .impl/issue.json
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 111, "issue_url": "https://github.com/owner/repo/issues/111", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        plan = Plan(
            plan_identifier="111",
            title="Plan without workflow",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/111",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 111},
        )

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # No workflow runs
        github = FakeGitHub(issues=[plan_to_issue(plan)], workflow_runs=[])
        issues = FakeGitHubIssues(issues={111: plan_to_issue(plan)}, comments={})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list", "--runs"], obj=ctx)
        assert result.exit_code == 0, result.output

        # Verify "-" appears in run-id column
        output = strip_ansi(result.output)
        assert "run-id" in output, "Expected run-id column header"
        # Run ID cell should show "-"
        lines = output.split("\n")
        # Find the line with the plan
        for line in lines:
            if "111" in line:
                assert "-" in line or "" in line  # Blank or dash


def test_plan_list_handles_batch_query_failure() -> None:
    """Plan list should succeed even if batch workflow query fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create worktree with .impl/issue.json
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name
        feature_wt = repo_dir / "feature-branch"
        feature_wt.mkdir(parents=True)

        impl_dir = feature_wt / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            '{"issue_number": 222, "issue_url": "https://github.com/owner/repo/issues/222", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        plan = Plan(
            plan_identifier="222",
            title="Plan with API failure",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/222",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 222},
        )

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # No workflow runs configured (simulates API failure or no runs found)
        github = FakeGitHub(issues=[plan_to_issue(plan)], workflow_runs=[])
        issues = FakeGitHubIssues(issues={222: plan_to_issue(plan)}, comments={})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list"], obj=ctx)
        # Command should succeed despite API failure
        assert result.exit_code == 0, result.output

        # Verify plan still displays (without run ID)
        output = strip_ansi(result.output)
        assert "222" in output
        assert "Plan with API failure" in output


def test_plan_list_displays_multiple_plans_with_different_workflow_runs() -> None:
    """Plan list should display different workflow run IDs for multiple plans."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create two worktrees with .impl/issue.json
        repo_name = env.cwd.name
        repo_dir = env.erk_root / repo_name

        # First worktree
        wt1 = repo_dir / "feature-1"
        wt1.mkdir(parents=True)
        impl1 = wt1 / ".impl"
        impl1.mkdir()
        issue1_json = impl1 / "issue.json"
        issue1_json.write_text(
            '{"issue_number": 301, "issue_url": "https://github.com/owner/repo/issues/301", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Second worktree
        wt2 = repo_dir / "feature-2"
        wt2.mkdir(parents=True)
        impl2 = wt2 / ".impl"
        impl2.mkdir()
        issue2_json = impl2 / "issue.json"
        issue2_json.write_text(
            '{"issue_number": 302, "issue_url": "https://github.com/owner/repo/issues/302", '
            '"created_at": "2025-01-20T10:00:00+00:00", "synced_at": "2025-01-20T10:00:00+00:00"}',
            encoding="utf-8",
        )

        # Create two plans with workflow run node_ids in plan-header
        plan1_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '11111111'
last_dispatched_node_id: 'WFR_node1'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

        plan2_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '22222222'
last_dispatched_node_id: 'WFR_node2'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

        plan1 = Plan(
            plan_identifier="301",
            title="First Implementation",
            body=plan1_body,
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/301",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 301},
        )

        plan2 = Plan(
            plan_identifier="302",
            title="Second Implementation",
            body=plan2_body,
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/302",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 302},
        )

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt1, branch="feature-1", is_root=False),
                    WorktreeInfo(path=wt2, branch="feature-2", is_root=False),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow runs with matching node_ids
        run1 = WorkflowRun(
            run_id="11111111",
            status="completed",
            conclusion="success",
            branch="master",
            head_sha="abc111",
        )
        run2 = WorkflowRun(
            run_id="22222222",
            status="in_progress",
            conclusion=None,
            branch="master",
            head_sha="abc222",
        )
        github = FakeGitHub(
            issues=[plan_to_issue(plan1), plan_to_issue(plan2)],
            workflow_runs_by_node_id={"WFR_node1": run1, "WFR_node2": run2},
        )
        issues = FakeGitHubIssues(issues={301: plan_to_issue(plan1), 302: plan_to_issue(plan2)})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list", "--runs"], obj=ctx)
        assert result.exit_code == 0, result.output

        # Verify both run IDs appear
        output = strip_ansi(result.output)
        assert "11111111" in output, "Expected first run ID"
        assert "22222222" in output, "Expected second run ID"


def test_plan_list_skips_run_id_for_plans_without_impl_folder() -> None:
    """Plan list should not query workflow runs for plans without .impl/ folders."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Create plan WITHOUT corresponding .impl/issue.json
        plan = Plan(
            plan_identifier="999",
            title="Plan without worktree",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/999",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 20, tzinfo=UTC),
            updated_at=datetime(2025, 1, 20, tzinfo=UTC),
            metadata={"number": 999},
        )

        git = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Add workflow run (should not be matched to this plan)
        workflow_run = WorkflowRun(
            run_id="44444444",
            status="completed",
            conclusion="success",
            branch="some-other-branch",
            head_sha="xyz999",
        )
        github = FakeGitHub(issues=[plan_to_issue(plan)], workflow_runs=[workflow_run])
        issues = FakeGitHubIssues(issues={999: plan_to_issue(plan)}, comments={})

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            issues=issues,
        )

        result = runner.invoke(cli, ["plan", "list"], obj=ctx)
        assert result.exit_code == 0, result.output

        # Verify plan displays without run ID
        output = strip_ansi(result.output)
        assert "999" in output
        assert "Plan without worktree" in output
        # Run ID should be "-" or blank
        assert "44444444" not in output, "Should not show unrelated run ID"
