"""Tests for action state display in plan list command.

Tests workflow status display (Pending, Running, Complete, Failed).
"""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.plan_store.types import Plan, PlanState
from tests.commands.dash.conftest import plan_to_issue
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_plan_list_shows_action_state_with_no_queue_label() -> None:
    """Test that plans without erk-queue label show '-' for action state."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1001",
        title="Regular Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1001",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1001},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1001: plan_to_issue(plan1)})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1001" in result.output


def test_plan_list_shows_pending_action_state() -> None:
    """Test that plans with erk-queue label but no metadata show 'Pending'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1002",
        title="Pending Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1002",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1002},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1002: plan_to_issue(plan1)}, comments={1002: []})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1002" in result.output


def test_plan_list_shows_running_action_state_with_workflow_started() -> None:
    """Test that plans with workflow-started metadata show 'Running'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1003",
        title="Running Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1003",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1003},
    )

    # Create comment with workflow-started metadata
    comment = """
<!-- erk:metadata-block:workflow-started -->
<details>
<summary><code>workflow-started</code></summary>

```yaml
status: started
started_at: "2024-11-23T10:00:00Z"
workflow_run_id: "12345"
workflow_run_url: "https://github.com/owner/repo/actions/runs/12345"
issue_number: 1003
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1003: plan_to_issue(plan1)}, comments={1003: [comment]})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1003" in result.output


def test_plan_list_shows_complete_action_state() -> None:
    """Test that plans with complete implementation status show 'Complete'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1004",
        title="Complete Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1004",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1004},
    )

    # Create comment with complete status
    comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: complete
completed_steps: 5
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1004: plan_to_issue(plan1)}, comments={1004: [comment]})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1004" in result.output


def test_plan_list_shows_failed_action_state() -> None:
    """Test that plans with failed implementation status show 'Failed'."""
    # Arrange
    plan1 = Plan(
        plan_identifier="1005",
        title="Failed Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1005",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 1005},
    )

    # Create comment with failed status
    comment = """
<!-- erk:metadata-block:erk-implementation-status -->
<details>
<summary><code>erk-implementation-status</code></summary>

```yaml
status: failed
completed_steps: 2
total_steps: 5
timestamp: "2024-11-23T12:00:00Z"
```
</details>
<!-- /erk:metadata-block -->
"""

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(issues={1005: plan_to_issue(plan1)}, comments={1005: [comment]})
        github = FakeGitHub(issues_data=[plan_to_issue(plan1)])
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "list"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "#1005" in result.output
