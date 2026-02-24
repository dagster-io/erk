"""Unit tests for plan IR types and builder functions."""

from datetime import UTC, datetime

from erk.cli.commands.plan.ir_types import (
    build_plan_view_output,
    plan_row_to_list_entry,
)
from erk.tui.data.types import PlanRowData
from erk_shared.plan_store.types import Plan, PlanState


def _make_plan_row(
    *,
    plan_id: int,
    title: str,
    author: str,
    pr_number: int | None = None,
    pr_url: str | None = None,
    pr_state: str | None = None,
    objective_issue: int | None = None,
    exists_locally: bool = False,
    run_id: str | None = None,
    run_url: str | None = None,
    run_status: str | None = None,
    run_conclusion: str | None = None,
) -> PlanRowData:
    """Create a minimal PlanRowData for testing."""
    return PlanRowData(
        plan_id=plan_id,
        plan_url=f"https://github.com/owner/repo/issues/{plan_id}",
        pr_number=pr_number,
        pr_url=pr_url,
        pr_display=f"#{pr_number}" if pr_number else "-",
        checks_display="-",
        worktree_name="",
        exists_locally=exists_locally,
        local_impl_display="-",
        remote_impl_display="-",
        run_id_display=run_id or "-",
        run_state_display="-",
        run_url=run_url,
        full_title=title,
        plan_body="",
        pr_title=None,
        pr_state=pr_state,
        pr_head_branch=None,
        worktree_branch=None,
        last_local_impl_at=None,
        last_remote_impl_at=None,
        run_id=run_id,
        run_status=run_status,
        run_conclusion=run_conclusion,
        log_entries=(),
        resolved_comment_count=0,
        total_comment_count=0,
        comments_display="-",
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_issue_closed=None,
        learn_plan_pr=None,
        learn_run_url=None,
        learn_display="-",
        learn_display_icon="-",
        objective_issue=objective_issue,
        objective_url=None,
        objective_display="-",
        objective_done_nodes=0,
        objective_total_nodes=0,
        objective_progress_display="-",
        objective_slug_display="-",
        objective_state_display="-",
        objective_deps_display="-",
        objective_deps_plans=(),
        objective_next_node_display="-",
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_display="1d ago",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        created_display="2d ago",
        author=author,
        is_learn_plan=False,
        lifecycle_display="planned",
        status_display="-",
    )


def test_plan_row_to_list_entry_basic() -> None:
    """Test conversion of PlanRowData to PlanListEntry."""
    row = _make_plan_row(plan_id=42, title="Test Plan", author="alice")
    entry = plan_row_to_list_entry(row)

    assert entry.plan_id == 42
    assert entry.plan_url == "https://github.com/owner/repo/issues/42"
    assert entry.title == "Test Plan"
    assert entry.author == "alice"
    assert entry.created_at == "2024-01-01T00:00:00Z"
    assert entry.pr_number is None
    assert entry.pr_state is None
    assert entry.exists_locally is False
    assert entry.objective_issue is None
    assert entry.resolved_comment_count == 0
    assert entry.total_comment_count == 0


def test_plan_row_to_list_entry_with_pr() -> None:
    """Test conversion preserves PR fields."""
    row = _make_plan_row(
        plan_id=10,
        title="PR Plan",
        author="bob",
        pr_number=100,
        pr_url="https://github.com/owner/repo/pull/100",
        pr_state="OPEN",
    )
    entry = plan_row_to_list_entry(row)

    assert entry.pr_number == 100
    assert entry.pr_url == "https://github.com/owner/repo/pull/100"
    assert entry.pr_state == "OPEN"


def test_plan_row_to_list_entry_with_run() -> None:
    """Test conversion preserves workflow run fields."""
    row = _make_plan_row(
        plan_id=20,
        title="Run Plan",
        author="carol",
        run_id="99999",
        run_url="https://github.com/owner/repo/actions/runs/99999",
        run_status="completed",
        run_conclusion="success",
    )
    entry = plan_row_to_list_entry(row)

    assert entry.run_id == "99999"
    assert entry.run_url == "https://github.com/owner/repo/actions/runs/99999"
    assert entry.run_status == "completed"
    assert entry.run_conclusion == "success"


def test_plan_row_to_list_entry_no_rich_markup() -> None:
    """Verify IR entry fields contain no Rich markup."""
    row = _make_plan_row(
        plan_id=5,
        title="Clean Title",
        author="dave",
        exists_locally=True,
        objective_issue=100,
    )
    entry = plan_row_to_list_entry(row)

    # Verify fields are plain strings, not Rich markup
    assert "[" not in entry.title
    assert "[" not in entry.author
    assert entry.exists_locally is True
    assert entry.objective_issue == 100


def test_build_plan_view_output_basic() -> None:
    """Test building PlanViewOutput from Plan with empty header."""
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Plan body content",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    output = build_plan_view_output(
        plan=plan,
        plan_id="42",
        header_info={},
        include_body=False,
    )

    assert output.plan_id == "42"
    assert output.title == "Test Plan"
    assert output.state == "OPEN"
    assert output.url == "https://github.com/owner/repo/issues/42"
    assert output.labels == ("erk-plan", "bug")
    assert output.assignees == ("alice",)
    assert output.created_at == "2024-01-01T00:00:00Z"
    assert output.updated_at == "2024-01-02T00:00:00Z"
    assert output.body is None  # include_body=False
    assert output.header is None  # empty header_info


def test_build_plan_view_output_with_body() -> None:
    """Test that include_body=True includes the plan body."""
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Plan body content",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    output = build_plan_view_output(
        plan=plan,
        plan_id="42",
        header_info={},
        include_body=True,
    )

    assert output.body == "Plan body content"


def test_build_plan_view_output_with_header() -> None:
    """Test building PlanViewOutput with header metadata."""
    plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    header_info: dict[str, object] = {
        "created_by": "schrockn",
        "schema_version": "2",
        "worktree_name": "test-wt",
        "objective_issue": 100,
        "source_repo": "dagster-io/erk",
        "branch_name": "P42-test-plan",
        "learn_status": "pending",
        "learn_plan_issue": 456,
    }

    output = build_plan_view_output(
        plan=plan,
        plan_id="42",
        header_info=header_info,
        include_body=False,
    )

    assert output.header is not None
    assert output.header.created_by == "schrockn"
    assert output.header.schema_version == "2"
    assert output.header.worktree_name == "test-wt"
    assert output.header.objective_issue == 100
    assert output.header.source_repo == "dagster-io/erk"
    assert output.header.learn_status == "pending"
    assert output.header.learn_plan_issue == 456
    assert output.branch_name == "P42-test-plan"


def test_build_plan_view_output_datetime_formatting() -> None:
    """Test that datetime values in header_info are formatted as ISO 8601."""
    plan = Plan(
        plan_identifier="42",
        title="Test",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )

    header_info: dict[str, object] = {
        "created_by": "test",
        "last_local_impl_at": datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC),
    }

    output = build_plan_view_output(
        plan=plan,
        plan_id="42",
        header_info=header_info,
        include_body=False,
    )

    assert output.header is not None
    assert output.header.last_local_impl_at == "2024-06-15T10:30:00Z"
