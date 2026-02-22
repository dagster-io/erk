"""Tests for implementation column display in plan list command.

Tests impl column headers (lcl-impl, remote-impl) which are always shown.
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PullRequestInfo, WorkflowRun
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_plan_list_shows_run_columns() -> None:
    """Test that run columns are always visible."""
    # Arrange - Create plan with PR and workflow run data
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
        title="Plan with PR and Run",
        body=plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/200",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 200},
        objective_id=None,
    )

    pr = PullRequestInfo(
        number=300,
        state="OPEN",
        url="https://github.com/owner/repo/pull/300",
        is_draft=False,
        title="PR for issue 200",
        checks_passing=True,
        owner="owner",
        repo="repo",
        has_conflicts=False,
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
            issues_data=[plan_to_issue(plan)],
            pr_issue_linkages={200: [pr]},
            workflow_runs_by_node_id={"WFR_all_flag": workflow_run},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Run columns always shown (no --runs flag needed)
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#200" in result.output
        # PR columns always appear
        assert "#300" in result.output  # PR number
        assert "👀" in result.output  # Open PR emoji
        assert "✅" in result.output  # Checks passing
        # Run columns always appear
        assert "99999" in result.output  # run-id


def test_dash_displays_impl_column_headers() -> None:
    """Verify local-impl and remote-impl column headers render correctly."""
    # Arrange - Create plan with local and remote impl timestamps
    body_with_impl = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_local_impl_at: '2024-11-20T10:00:00Z'
last_remote_impl_at: '2024-11-21T12:00:00Z'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    plan = Plan(
        plan_identifier="1",
        title="Test Plan",
        body=body_with_impl,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1},
        objective_id=None,
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1: plan_to_issue(plan)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Both local-impl and remote-impl columns always shown
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert - Column headers should appear in output
        assert result.exit_code == 0
        assert "lcl-impl" in result.output
        assert "remote-impl" in result.output
