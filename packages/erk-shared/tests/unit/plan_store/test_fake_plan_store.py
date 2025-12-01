"""Unit tests for FakePlanStore."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from erk_shared.plan_store.fake import FakePlanStore
from erk_shared.plan_store.types import Plan, PlanMetadataUpdate, PlanQuery, PlanState


def test_get_plan_success() -> None:
    """Test fetching a plan issue that exists."""
    plan_issue = Plan(
        plan_identifier="42",
        title="Test Issue",
        body="Test body",
        state=PlanState.OPEN,
        url="https://example.com/issues/42",
        labels=["erk-plan"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        metadata={"number": 42},
    )

    store = FakePlanStore(plans={"42": plan_issue})
    result = store.get_plan(Path("/fake/repo"), "42")

    assert result == plan_issue


def test_get_plan_not_found() -> None:
    """Test fetching a plan issue that doesn't exist raises RuntimeError."""
    store = FakePlanStore(plans={})

    with pytest.raises(RuntimeError, match="Plan '999' not found"):
        store.get_plan(Path("/fake/repo"), "999")


def test_list_plans_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    issue1 = Plan(
        plan_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue2 = Plan(
        plan_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.CLOSED,
        url="https://example.com/issues/2",
        labels=["bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(plans={"1": issue1, "2": issue2})
    query = PlanQuery()
    results = store.list_plans(Path("/fake/repo"), query)

    assert len(results) == 2
    assert issue1 in results
    assert issue2 in results


def test_list_plans_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    open_issue = Plan(
        plan_identifier="1",
        title="Open Issue",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_issue = Plan(
        plan_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanState.CLOSED,
        url="https://example.com/issues/2",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(plans={"1": open_issue, "2": closed_issue})

    # Filter for open issues
    query_open = PlanQuery(state=PlanState.OPEN)
    results_open = store.list_plans(Path("/fake/repo"), query_open)
    assert len(results_open) == 1
    assert results_open[0] == open_issue

    # Filter for closed issues
    query_closed = PlanQuery(state=PlanState.CLOSED)
    results_closed = store.list_plans(Path("/fake/repo"), query_closed)
    assert len(results_closed) == 1
    assert results_closed[0] == closed_issue


def test_list_plans_filter_by_labels_and_logic() -> None:
    """Test filtering plan issues by labels with AND logic."""
    issue_with_both = Plan(
        plan_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_with_one = Plan(
        plan_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(plans={"1": issue_with_both, "2": issue_with_one})

    # Query for both labels (AND logic)
    query = PlanQuery(labels=["erk-plan", "erk-queue"])
    results = store.list_plans(Path("/fake/repo"), query)

    # Only issue 1 has both labels
    assert len(results) == 1
    assert results[0] == issue_with_both


def test_list_plans_filter_by_limit() -> None:
    """Test limiting the number of returned plan issues."""
    issue1 = Plan(
        plan_identifier="1",
        title="Issue 1",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue2 = Plan(
        plan_identifier="2",
        title="Issue 2",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/2",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    issue3 = Plan(
        plan_identifier="3",
        title="Issue 3",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/3",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(plans={"1": issue1, "2": issue2, "3": issue3})
    query = PlanQuery(limit=2)
    results = store.list_plans(Path("/fake/repo"), query)

    assert len(results) == 2


def test_list_plans_combined_filters() -> None:
    """Test combining multiple filters."""
    matching_issue = Plan(
        plan_identifier="1",
        title="Matching Issue",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    wrong_state = Plan(
        plan_identifier="2",
        title="Wrong State",
        body="",
        state=PlanState.CLOSED,
        url="https://example.com/issues/2",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    wrong_labels = Plan(
        plan_identifier="3",
        title="Wrong Labels",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/3",
        labels=["erk-plan"],  # Missing "bug"
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(plans={"1": matching_issue, "2": wrong_state, "3": wrong_labels})
    query = PlanQuery(
        state=PlanState.OPEN,
        labels=["erk-plan", "bug"],
    )
    results = store.list_plans(Path("/fake/repo"), query)

    # Only issue 1 matches all criteria
    assert len(results) == 1
    assert results[0] == matching_issue


def test_list_plans_empty_results() -> None:
    """Test querying with filters that match no issues."""
    issue = Plan(
        plan_identifier="1",
        title="Issue",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(plans={"1": issue})
    query = PlanQuery(state=PlanState.CLOSED)
    results = store.list_plans(Path("/fake/repo"), query)

    assert len(results) == 0


def test_get_provider_name() -> None:
    """Test getting the provider name."""
    store = FakePlanStore()
    assert store.get_provider_name() == "fake"


def test_string_identifier_flexibility() -> None:
    """Test that identifiers work as strings (not just integers)."""
    # Test with various string formats
    issue_github = Plan(
        plan_identifier="42",
        title="GitHub Issue",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/42",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_jira = Plan(
        plan_identifier="PROJ-123",
        title="Jira Issue",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/PROJ-123",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_linear = Plan(
        plan_identifier="550e8400-e29b-41d4-a716-446655440000",
        title="Linear Issue",
        body="",
        state=PlanState.OPEN,
        url="https://example.com/issues/550e8400",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanStore(
        plans={
            "42": issue_github,
            "PROJ-123": issue_jira,
            "550e8400-e29b-41d4-a716-446655440000": issue_linear,
        }
    )

    # All identifier formats should work
    assert store.get_plan(Path("/fake"), "42") == issue_github
    assert store.get_plan(Path("/fake"), "PROJ-123") == issue_jira
    assert store.get_plan(Path("/fake"), "550e8400-e29b-41d4-a716-446655440000") == issue_linear


# === WRITE OPERATIONS TESTS ===


def test_create_plan_basic() -> None:
    """Test creating a plan stores it and returns result."""
    store = FakePlanStore()

    result = store.create_plan(
        repo_root=Path("/fake/repo"),
        title="Test Plan",
        body="Plan content here",
        labels=["bug"],
    )

    # Check result
    assert result.plan_identifier == "1"
    assert result.url.startswith("https://github.com/")

    # Check plan was stored
    plan = store.get_plan(Path("/fake"), "1")
    assert plan.title == "Test Plan [erk-plan]"
    assert plan.body == "Plan content here"
    assert plan.state == PlanState.OPEN
    assert "erk-plan" in plan.labels
    assert "bug" in plan.labels

    # Check created_plans tracking
    assert len(store.created_plans) == 1
    assert store.created_plans[0] == result


def test_create_plan_auto_increments_id() -> None:
    """Test that plan IDs auto-increment."""
    store = FakePlanStore()

    result1 = store.create_plan(Path("/fake"), "Plan 1", "Body 1", [])
    result2 = store.create_plan(Path("/fake"), "Plan 2", "Body 2", [])

    assert result1.plan_identifier == "1"
    assert result2.plan_identifier == "2"


def test_create_plan_deduplicates_erk_plan_label() -> None:
    """Test that erk-plan label is not duplicated if already provided."""
    store = FakePlanStore()

    result = store.create_plan(
        repo_root=Path("/fake"),
        title="Test",
        body="Body",
        labels=["erk-plan", "other"],
    )

    plan = store.get_plan(Path("/fake"), result.plan_identifier)
    # erk-plan should appear exactly once
    assert plan.labels.count("erk-plan") == 1
    assert "other" in plan.labels


def test_update_plan_metadata_worktree_name() -> None:
    """Test updating worktree_name in plan metadata."""
    # Create initial plan
    initial_plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Body",
        state=PlanState.OPEN,
        url="https://example.com/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 42},
    )
    store = FakePlanStore(plans={"42": initial_plan})

    # Update metadata
    updates = PlanMetadataUpdate(worktree_name="feature-branch")
    store.update_plan_metadata(Path("/fake"), "42", updates)

    # Verify update
    updated_plan = store.get_plan(Path("/fake"), "42")
    assert updated_plan.metadata.get("worktree_name") == "feature-branch"


def test_update_plan_metadata_multiple_fields() -> None:
    """Test updating multiple metadata fields at once."""
    initial_plan = Plan(
        plan_identifier="42",
        title="Test Plan",
        body="Body",
        state=PlanState.OPEN,
        url="https://example.com/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={"number": 42},
    )
    store = FakePlanStore(plans={"42": initial_plan})

    updates = PlanMetadataUpdate(
        worktree_name="feature-branch",
        last_dispatched_run_id="run-123",
        last_dispatched_at="2024-06-01T12:00:00Z",
        last_local_impl_at="2024-06-02T10:00:00Z",
    )
    store.update_plan_metadata(Path("/fake"), "42", updates)

    updated_plan = store.get_plan(Path("/fake"), "42")
    assert updated_plan.metadata.get("worktree_name") == "feature-branch"
    assert updated_plan.metadata.get("last_dispatched_run_id") == "run-123"
    assert updated_plan.metadata.get("last_dispatched_at") == "2024-06-01T12:00:00Z"
    assert updated_plan.metadata.get("last_local_impl_at") == "2024-06-02T10:00:00Z"


def test_update_plan_metadata_not_found() -> None:
    """Test updating metadata for non-existent plan raises error."""
    store = FakePlanStore()

    with pytest.raises(RuntimeError, match="Plan '999' not found"):
        store.update_plan_metadata(Path("/fake"), "999", PlanMetadataUpdate())


def test_ensure_label_tracks_labels() -> None:
    """Test that ensure_label tracks labels in memory."""
    store = FakePlanStore()

    store.ensure_label(
        repo_root=Path("/fake"),
        label="erk-plan",
        description="Implementation plan",
        color="0E8A16",
    )

    assert "erk-plan" in store.labels
    assert store.labels["erk-plan"] == ("Implementation plan", "0E8A16")


def test_get_current_user_default() -> None:
    """Test default current user is 'test-user'."""
    store = FakePlanStore()
    assert store.get_current_user() == "test-user"


def test_get_current_user_configurable() -> None:
    """Test current user can be configured."""
    store = FakePlanStore()

    store.set_current_user("custom-user")
    assert store.get_current_user() == "custom-user"

    store.set_current_user(None)
    assert store.get_current_user() is None
