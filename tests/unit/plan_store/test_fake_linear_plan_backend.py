"""Unit tests for FakeLinearPlanBackend.

These tests verify that the fake implementation correctly models Linear's
key differences from GitHub:

1. UUID-based IDs (not integers)
2. 5-state workflow mapped to OPEN/CLOSED
3. Single assignee (not list)
4. Comment IDs are UUIDs (not integers)
5. Mutation tracking for test assertions
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.plan_store.fake_linear import (
    FakeLinearPlanBackend,
    LinearIssue,
)
from erk_shared.plan_store.types import PlanQuery, PlanState


def _create_linear_issue(
    id: str,
    title: str,
    description: str = "Test description",
    state: str = "todo",
    labels: tuple[str, ...] = (),
    assignee: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    custom_fields: dict[str, object] | None = None,
) -> LinearIssue:
    """Helper to create LinearIssue for tests."""
    now = datetime.now(UTC)
    return LinearIssue(
        id=id,
        title=title,
        description=description,
        state=state,  # type: ignore[arg-type]
        url=f"https://linear.app/team/issue/{id}",
        labels=labels,
        assignee=assignee,
        created_at=created_at if created_at else now,
        updated_at=updated_at if updated_at else now,
        custom_fields=custom_fields if custom_fields else {},
    )


# =============================================================================
# get_plan tests
# =============================================================================


def test_get_plan_returns_plan_with_uuid_identifier() -> None:
    """Test that plan_identifier is UUID string (not integer)."""
    issue = _create_linear_issue(
        id="LIN-abc12345",
        title="Test Plan",
    )
    backend = FakeLinearPlanBackend(issues={"LIN-abc12345": issue})

    result = backend.get_plan(Path("/repo"), "LIN-abc12345")

    # UUID-style identifier, not integer
    assert result.plan_identifier == "LIN-abc12345"
    assert not result.plan_identifier.isdigit()


def test_get_plan_not_found_raises() -> None:
    """Test error when plan doesn't exist."""
    backend = FakeLinearPlanBackend()

    with pytest.raises(RuntimeError, match="Linear issue .* not found"):
        backend.get_plan(Path("/repo"), "nonexistent-id")


def test_get_plan_converts_all_fields() -> None:
    """Test that all LinearIssue fields are converted to Plan."""
    created = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
    updated = datetime(2024, 1, 16, 12, 0, 0, tzinfo=UTC)

    issue = _create_linear_issue(
        id="LIN-full-test",
        title="Full Test Plan",
        description="Complete plan content",
        state="in_progress",
        labels=("erk-plan", "feature"),
        assignee="alice",
        created_at=created,
        updated_at=updated,
        custom_fields={"worktree_name": "feature-wt"},
    )
    backend = FakeLinearPlanBackend(issues={"LIN-full-test": issue})

    result = backend.get_plan(Path("/repo"), "LIN-full-test")

    assert result.plan_identifier == "LIN-full-test"
    assert result.title == "Full Test Plan"
    assert result.body == "Complete plan content"
    assert result.state == PlanState.OPEN  # in_progress maps to OPEN
    assert result.url == "https://linear.app/team/issue/LIN-full-test"
    assert result.labels == ["erk-plan", "feature"]
    assert result.assignees == ["alice"]  # Single assignee becomes list
    assert result.created_at == created
    assert result.updated_at == updated
    assert result.metadata == {"worktree_name": "feature-wt"}


# =============================================================================
# State mapping tests (5 states -> 2 states)
# =============================================================================


def test_state_mapping_backlog_is_open() -> None:
    """Test 'backlog' state maps to OPEN."""
    issue = _create_linear_issue(id="id-1", title="Test", state="backlog")
    backend = FakeLinearPlanBackend(issues={"id-1": issue})

    result = backend.get_plan(Path("/repo"), "id-1")

    assert result.state == PlanState.OPEN


def test_state_mapping_todo_is_open() -> None:
    """Test 'todo' state maps to OPEN."""
    issue = _create_linear_issue(id="id-2", title="Test", state="todo")
    backend = FakeLinearPlanBackend(issues={"id-2": issue})

    result = backend.get_plan(Path("/repo"), "id-2")

    assert result.state == PlanState.OPEN


def test_state_mapping_in_progress_is_open() -> None:
    """Test 'in_progress' state maps to OPEN."""
    issue = _create_linear_issue(id="id-3", title="Test", state="in_progress")
    backend = FakeLinearPlanBackend(issues={"id-3": issue})

    result = backend.get_plan(Path("/repo"), "id-3")

    assert result.state == PlanState.OPEN


def test_state_mapping_done_is_closed() -> None:
    """Test 'done' state maps to CLOSED."""
    issue = _create_linear_issue(id="id-4", title="Test", state="done")
    backend = FakeLinearPlanBackend(issues={"id-4": issue})

    result = backend.get_plan(Path("/repo"), "id-4")

    assert result.state == PlanState.CLOSED


def test_state_mapping_canceled_is_closed() -> None:
    """Test 'canceled' state maps to CLOSED."""
    issue = _create_linear_issue(id="id-5", title="Test", state="canceled")
    backend = FakeLinearPlanBackend(issues={"id-5": issue})

    result = backend.get_plan(Path("/repo"), "id-5")

    assert result.state == PlanState.CLOSED


# =============================================================================
# Assignee handling tests (single -> list)
# =============================================================================


def test_single_assignee_becomes_list_with_one_item() -> None:
    """Test that single assignee is converted to list with one item."""
    issue = _create_linear_issue(id="id-1", title="Test", assignee="bob")
    backend = FakeLinearPlanBackend(issues={"id-1": issue})

    result = backend.get_plan(Path("/repo"), "id-1")

    assert result.assignees == ["bob"]


def test_no_assignee_becomes_empty_list() -> None:
    """Test that no assignee is converted to empty list."""
    issue = _create_linear_issue(id="id-2", title="Test", assignee=None)
    backend = FakeLinearPlanBackend(issues={"id-2": issue})

    result = backend.get_plan(Path("/repo"), "id-2")

    assert result.assignees == []


# =============================================================================
# list_plans tests
# =============================================================================


def test_list_plans_filters_by_state_open() -> None:
    """Test filtering by OPEN state includes backlog, todo, in_progress."""
    backend = FakeLinearPlanBackend(
        issues={
            "id-1": _create_linear_issue(id="id-1", title="Backlog", state="backlog"),
            "id-2": _create_linear_issue(id="id-2", title="Todo", state="todo"),
            "id-3": _create_linear_issue(id="id-3", title="In Progress", state="in_progress"),
            "id-4": _create_linear_issue(id="id-4", title="Done", state="done"),
            "id-5": _create_linear_issue(id="id-5", title="Canceled", state="canceled"),
        }
    )

    results = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.OPEN))

    assert len(results) == 3
    ids = {r.plan_identifier for r in results}
    assert ids == {"id-1", "id-2", "id-3"}


def test_list_plans_filters_by_state_closed() -> None:
    """Test filtering by CLOSED state includes done, canceled."""
    backend = FakeLinearPlanBackend(
        issues={
            "id-1": _create_linear_issue(id="id-1", title="Todo", state="todo"),
            "id-2": _create_linear_issue(id="id-2", title="Done", state="done"),
            "id-3": _create_linear_issue(id="id-3", title="Canceled", state="canceled"),
        }
    )

    results = backend.list_plans(Path("/repo"), PlanQuery(state=PlanState.CLOSED))

    assert len(results) == 2
    ids = {r.plan_identifier for r in results}
    assert ids == {"id-2", "id-3"}


def test_list_plans_filters_by_labels() -> None:
    """Test filtering by labels uses AND logic."""
    backend = FakeLinearPlanBackend(
        issues={
            "id-1": _create_linear_issue(id="id-1", title="Plan 1", labels=("erk-plan", "feature")),
            "id-2": _create_linear_issue(id="id-2", title="Plan 2", labels=("erk-plan",)),
            "id-3": _create_linear_issue(id="id-3", title="Bug", labels=("bug",)),
        }
    )

    # Both labels must match
    results = backend.list_plans(Path("/repo"), PlanQuery(labels=["erk-plan", "feature"]))

    assert len(results) == 1
    assert results[0].plan_identifier == "id-1"


def test_list_plans_applies_limit() -> None:
    """Test limit parameter restricts results."""
    backend = FakeLinearPlanBackend(
        issues={f"id-{i}": _create_linear_issue(id=f"id-{i}", title=f"Plan {i}") for i in range(10)}
    )

    results = backend.list_plans(Path("/repo"), PlanQuery(limit=3))

    assert len(results) == 3


def test_list_plans_no_filters_returns_all() -> None:
    """Test no filters returns all plans."""
    backend = FakeLinearPlanBackend(
        issues={
            "id-1": _create_linear_issue(id="id-1", title="Plan 1"),
            "id-2": _create_linear_issue(id="id-2", title="Plan 2", state="done"),
        }
    )

    results = backend.list_plans(Path("/repo"), PlanQuery())

    assert len(results) == 2


# =============================================================================
# create_plan tests
# =============================================================================


def test_create_plan_returns_uuid_id() -> None:
    """Test create_plan returns UUID-style plan_id."""
    backend = FakeLinearPlanBackend()

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="New Plan",
        content="Plan content",
        labels=("erk-plan",),
        metadata={},
    )

    # UUID-style ID with prefix
    assert result.plan_id.startswith("LIN-")
    assert not result.plan_id.replace("LIN-", "").isdigit()
    assert result.url.startswith("https://linear.app/")


def test_create_plan_tracks_mutation() -> None:
    """Test create_plan tracks mutation for assertions."""
    backend = FakeLinearPlanBackend()

    backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Title",
        content="Test Content",
        labels=("erk-plan", "feature"),
        metadata={"source": "test"},
    )

    assert len(backend.created_plans) == 1
    title, content, labels = backend.created_plans[0]
    assert title == "Test Title"
    assert content == "Test Content"
    assert labels == ("erk-plan", "feature")


def test_create_plan_stores_metadata_in_custom_fields() -> None:
    """Test metadata is stored in custom_fields."""
    backend = FakeLinearPlanBackend()

    result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Plan",
        content="Content",
        labels=(),
        metadata={"worktree_name": "feature-wt", "objective_issue": 100},
    )

    # Fetch the plan and check metadata
    plan = backend.get_plan(Path("/repo"), result.plan_id)
    assert plan.metadata == {"worktree_name": "feature-wt", "objective_issue": 100}


# =============================================================================
# add_comment tests
# =============================================================================


def test_add_comment_returns_uuid_string() -> None:
    """Test add_comment returns UUID string (not integer)."""
    issue = _create_linear_issue(id="plan-1", title="Test")
    backend = FakeLinearPlanBackend(issues={"plan-1": issue})

    comment_id = backend.add_comment(
        repo_root=Path("/repo"),
        plan_id="plan-1",
        body="Progress update",
    )

    # UUID-style comment ID
    assert comment_id.startswith("comment-")
    assert not comment_id.replace("comment-", "").isdigit()


def test_add_comment_tracks_mutation() -> None:
    """Test add_comment tracks mutation for assertions."""
    issue = _create_linear_issue(id="plan-1", title="Test")
    backend = FakeLinearPlanBackend(issues={"plan-1": issue})

    comment_id = backend.add_comment(
        repo_root=Path("/repo"),
        plan_id="plan-1",
        body="Phase 1 complete",
    )

    assert len(backend.added_comments) == 1
    plan_id, body, cid = backend.added_comments[0]
    assert plan_id == "plan-1"
    assert body == "Phase 1 complete"
    assert cid == comment_id


def test_add_comment_plan_not_found_raises() -> None:
    """Test error when plan doesn't exist."""
    backend = FakeLinearPlanBackend()

    with pytest.raises(RuntimeError, match="Linear issue .* not found"):
        backend.add_comment(Path("/repo"), "nonexistent", "comment")


# =============================================================================
# update_metadata tests
# =============================================================================


def test_update_metadata_merges_fields() -> None:
    """Test update_metadata merges into custom_fields."""
    issue = _create_linear_issue(
        id="plan-1",
        title="Test",
        custom_fields={"existing_key": "value"},
    )
    backend = FakeLinearPlanBackend(issues={"plan-1": issue})

    backend.update_metadata(
        repo_root=Path("/repo"),
        plan_id="plan-1",
        metadata={"worktree_name": "feature-wt"},
    )

    # Fetch and verify merge
    plan = backend.get_plan(Path("/repo"), "plan-1")
    assert plan.metadata["existing_key"] == "value"
    assert plan.metadata["worktree_name"] == "feature-wt"


def test_update_metadata_tracks_mutation() -> None:
    """Test update_metadata tracks mutation for assertions."""
    issue = _create_linear_issue(id="plan-1", title="Test")
    backend = FakeLinearPlanBackend(issues={"plan-1": issue})

    backend.update_metadata(
        repo_root=Path("/repo"),
        plan_id="plan-1",
        metadata={"last_impl_at": "2024-01-15"},
    )

    assert len(backend.updated_metadata) == 1
    plan_id, metadata = backend.updated_metadata[0]
    assert plan_id == "plan-1"
    assert metadata == {"last_impl_at": "2024-01-15"}


def test_update_metadata_plan_not_found_raises() -> None:
    """Test error when plan doesn't exist."""
    backend = FakeLinearPlanBackend()

    with pytest.raises(RuntimeError, match="Linear issue .* not found"):
        backend.update_metadata(Path("/repo"), "nonexistent", {})


# =============================================================================
# close_plan tests
# =============================================================================


def test_close_plan_sets_state_to_done() -> None:
    """Test close_plan sets state to 'done'."""
    issue = _create_linear_issue(id="plan-1", title="Test", state="in_progress")
    backend = FakeLinearPlanBackend(issues={"plan-1": issue})

    backend.close_plan(Path("/repo"), "plan-1")

    plan = backend.get_plan(Path("/repo"), "plan-1")
    assert plan.state == PlanState.CLOSED


def test_close_plan_tracks_mutation() -> None:
    """Test close_plan tracks mutation for assertions."""
    issue = _create_linear_issue(id="plan-1", title="Test")
    backend = FakeLinearPlanBackend(issues={"plan-1": issue})

    backend.close_plan(Path("/repo"), "plan-1")

    assert backend.closed_plans == ["plan-1"]


def test_close_plan_not_found_raises() -> None:
    """Test error when plan doesn't exist."""
    backend = FakeLinearPlanBackend()

    with pytest.raises(RuntimeError, match="Linear issue .* not found"):
        backend.close_plan(Path("/repo"), "nonexistent")


# =============================================================================
# Provider name tests
# =============================================================================


def test_get_provider_name() -> None:
    """Test provider name is 'linear'."""
    backend = FakeLinearPlanBackend()
    assert backend.get_provider_name() == "linear"
