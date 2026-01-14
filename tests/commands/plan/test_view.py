"""Tests for plan view command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


def test_view_plan_displays_issue() -> None:
    """Test fetching and displaying a plan issue."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue description",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Test Issue" in result.output
        assert "OPEN" in result.output
        assert "42" in result.output
        assert "erk-plan" in result.output
        assert "bug" in result.output
        assert "alice" in result.output
        # Body should NOT be displayed without --full
        assert "This is a test issue description" not in result.output


def test_view_plan_with_full_flag() -> None:
    """Test viewing plan with --full flag shows the body."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue description",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42", "--full"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Test Issue" in result.output
        # Body SHOULD be displayed with --full
        assert "This is a test issue description" in result.output
        assert "--- Plan ---" in result.output


def test_view_plan_with_short_full_flag() -> None:
    """Test viewing plan with -f flag (short form of --full)."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="This is a test issue description",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42", "-f"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        # Body SHOULD be displayed with -f
        assert "This is a test issue description" in result.output


def test_view_plan_not_found() -> None:
    """Test fetching a plan issue that doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Issue #999 not found" in result.output


def test_view_plan_minimal_fields() -> None:
    """Test displaying issue with minimal fields (no labels, assignees, body)."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="1",
        title="Minimal Issue",
        body="minimal content",  # GitHubPlanStore requires non-empty body
        state=PlanState.CLOSED,
        url="https://github.com/owner/repo/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"1": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "1"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Minimal Issue" in result.output
        assert "CLOSED" in result.output


def test_view_plan_with_github_url() -> None:
    """Test fetching plan using GitHub issue URL."""
    # Arrange
    plan_issue = Plan(
        plan_identifier="123",
        title="URL Test Issue",
        body="Issue from URL",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/123",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"123": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - use GitHub URL instead of plain number
        result = runner.invoke(
            cli, ["plan", "view", "https://github.com/owner/repo/issues/123"], obj=ctx
        )

        # Assert
        assert result.exit_code == 0
        assert "URL Test Issue" in result.output


def test_view_plan_invalid_url() -> None:
    """Test error handling for invalid identifier format."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act - use invalid identifier
        result = runner.invoke(cli, ["plan", "view", "invalid-input"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Invalid issue number or URL" in result.output


def test_view_plan_with_header_info() -> None:
    """Test displaying plan with plan-header metadata.

    Note: The test helper converts Plan.body to IssueInfo.body,
    and GitHubPlanStore._convert_to_plan sets metadata["issue_body"]
    from IssueInfo.body. So we put the raw issue body with the
    plan-header block in Plan.body.
    """
    # Arrange - create plan with body containing plan-header
    # This is what the raw issue body would look like on GitHub
    issue_body = """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

created_by: schrockn
schema_version: 2
worktree_name: test-worktree
source_repo: dagster-io/erk
objective_issue: 100

```

</details>
<!-- /erk:metadata-block:plan-header -->

Some other content here.
"""

    plan_issue = Plan(
        plan_identifier="42",
        title="Plan with Header",
        body=issue_body,  # Raw issue body with plan-header goes here
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Plan with Header" in result.output
        assert "--- Header Info ---" in result.output
        assert "Created by: schrockn" in result.output
        assert "Schema version: 2" in result.output
        assert "Worktree: test-worktree" in result.output
        assert "Source repo: dagster-io/erk" in result.output
        assert "Objective: #100" in result.output


def test_view_plan_with_implementation_info() -> None:
    """Test displaying plan with local implementation metadata."""
    # Arrange
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

created_by: schrockn
schema_version: 2
last_local_impl_at: 2024-01-15T10:30:00Z
last_local_impl_event: ended
last_local_impl_session: abc123
last_local_impl_user: testuser

```

</details>
<!-- /erk:metadata-block:plan-header -->
"""

    plan_issue = Plan(
        plan_identifier="42",
        title="Plan with Impl Info",
        body=issue_body,  # Raw issue body with plan-header
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "--- Local Implementation ---" in result.output
        assert "Last impl: 2024-01-15T10:30:00Z (ended)" in result.output
        assert "Session: abc123" in result.output
        assert "User: testuser" in result.output


def test_view_plan_without_header_info() -> None:
    """Test displaying plan without plan-header metadata shows no header section."""
    # Arrange - plan without issue_body metadata
    plan_issue = Plan(
        plan_identifier="42",
        title="Plan without Header",
        body="The plan content here",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Plan without Header" in result.output
        # Should NOT show header info section when no metadata
        assert "--- Header Info ---" not in result.output


def test_view_plan_learn_section_no_evaluation() -> None:
    """Test that Learn section shows 'No learn evaluation' when learn hasn't been run."""
    # Arrange - plan with header but no learn data
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

created_by: schrockn
schema_version: 2
created_from_session: abc123-session-id

```

</details>
<!-- /erk:metadata-block:plan-header -->
"""

    plan_issue = Plan(
        plan_identifier="42",
        title="Plan with no learn",
        body=issue_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "--- Learn ---" in result.output
        assert "Plan created from session: abc123-session-id" in result.output
        assert "No learn evaluation" in result.output


def test_view_plan_learn_section_with_evaluation() -> None:
    """Test that Learn section shows learn data when available."""
    # Arrange - plan with header and learn data
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

created_by: schrockn
schema_version: 2
created_from_session: abc123-session-id
last_learn_at: 2024-01-20T15:00:00Z
last_learn_session: def456-learn-session

```

</details>
<!-- /erk:metadata-block:plan-header -->
"""

    plan_issue = Plan(
        plan_identifier="42",
        title="Plan with learn data",
        body=issue_body,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        store, _ = create_plan_store_with_plans({"42": plan_issue})
        ctx = build_workspace_test_context(env, plan_store=store)

        # Act
        result = runner.invoke(cli, ["plan", "view", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "--- Learn ---" in result.output
        assert "Plan created from session: abc123-session-id" in result.output
        assert "Last learn: 2024-01-20T15:00:00Z" in result.output
        assert "Learn session: def456-learn-session" in result.output
        # Should NOT show "No learn evaluation" when learn data is present
        assert "No learn evaluation" not in result.output
