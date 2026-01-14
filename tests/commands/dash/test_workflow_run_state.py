"""Tests for --run-state filtering in plan list command.

Tests filtering plans by workflow run state (queued, in_progress, success).
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.types import WorkflowRun
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_plan_list_filter_by_run_state_queued() -> None:
    """Test filtering plans by workflow run state (queued)."""
    # Arrange - Create plans with workflow run node_ids in plan-header
    queued_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '11111'
last_dispatched_node_id: 'WFR_queued'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    running_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '22222'
last_dispatched_node_id: 'WFR_running'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    queued_plan = Plan(
        plan_identifier="1010",
        title="Queued Plan",
        body=queued_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1010",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1010},
    )

    running_plan = Plan(
        plan_identifier="1011",
        title="Running Plan",
        body=running_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1011",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 1011},
    )

    # Configure workflow runs with node_id lookup
    queued_run = WorkflowRun(
        run_id="11111",
        status="queued",
        conclusion=None,
        branch="master",
        head_sha="abc123",
    )
    running_run = WorkflowRun(
        run_id="22222",
        status="in_progress",
        conclusion=None,
        branch="master",
        head_sha="def456",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1010: plan_to_issue(queued_plan), 1011: plan_to_issue(running_plan)},
        )
        github = FakeGitHub(
            issues_data=[plan_to_issue(queued_plan), plan_to_issue(running_plan)],
            workflow_runs_by_node_id={"WFR_queued": queued_run, "WFR_running": running_run},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for queued workflow runs
        result = runner.invoke(cli, ["plan", "list", "--run-state", "queued"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1010" in result.output
        assert "Queued Plan" in result.output
        assert "#1011" not in result.output


def test_plan_list_filter_by_run_state_success() -> None:
    """Test filtering plans by workflow run state (success)."""
    # Arrange - Create plans with workflow run node_ids in plan-header
    success_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '11111'
last_dispatched_node_id: 'WFR_success'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    failed_plan_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: '2'
last_dispatched_run_id: '22222'
last_dispatched_node_id: 'WFR_failed'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    success_plan = Plan(
        plan_identifier="1020",
        title="Success Plan",
        body=success_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1020",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1020},
    )

    failed_plan = Plan(
        plan_identifier="1021",
        title="Failed Plan",
        body=failed_plan_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1021",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={"number": 1021},
    )

    # Configure workflow runs with node_id lookup
    success_run = WorkflowRun(
        run_id="11111",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
    )
    failed_run = WorkflowRun(
        run_id="22222",
        status="completed",
        conclusion="failure",
        branch="master",
        head_sha="def456",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(
            issues={1020: plan_to_issue(success_plan), 1021: plan_to_issue(failed_plan)},
        )
        github = FakeGitHub(
            issues_data=[plan_to_issue(success_plan), plan_to_issue(failed_plan)],
            workflow_runs_by_node_id={"WFR_success": success_run, "WFR_failed": failed_run},
        )
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for success workflow runs
        result = runner.invoke(cli, ["plan", "list", "--run-state", "success"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1020" in result.output
        assert "Success Plan" in result.output
        assert "#1021" not in result.output


def test_plan_list_run_state_filter_no_matches() -> None:
    """Test run-state filter with no matching plans."""
    # Arrange - Plan with workflow run that doesn't match filter
    plan = Plan(
        plan_identifier="1030",
        title="Regular Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1030",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1030},
    )

    # Configure workflow run with completed/success state
    success_run = WorkflowRun(
        run_id="11111",
        status="completed",
        conclusion="success",
        branch="master",
        head_sha="abc123",
        display_title="Regular Plan",
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1030: plan_to_issue(plan)}, comments={})
        github = FakeGitHub(workflow_runs=[success_run])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act - Filter for "in_progress" which won't match (run is completed/success)
        result = runner.invoke(cli, ["plan", "list", "--run-state", "in_progress"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "No plans found matching the criteria" in result.output
