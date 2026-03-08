"""Tests for PlanRowData serialization to JSON-compatible dicts."""

from datetime import UTC, datetime

from erk.tui.data.serialization import serialize_plan_row
from erk_shared.gateway.plan_data_provider.fake import make_plan_row


def test_datetime_serialization() -> None:
    """Datetime fields are converted to ISO 8601 strings."""
    created = datetime(2025, 3, 15, 10, 30, 0, tzinfo=UTC)
    updated = datetime(2025, 3, 16, 12, 0, 0, tzinfo=UTC)
    row = make_plan_row(42, "Test Plan", created_at=created, updated_at=updated)

    data = serialize_plan_row(row)

    assert data["created_at"] == "2025-03-15T10:30:00+00:00"
    assert data["updated_at"] == "2025-03-16T12:00:00+00:00"
    # None datetimes stay as None
    assert data["last_local_impl_at"] is None
    assert data["last_remote_impl_at"] is None


def test_tuple_to_list_log_entries() -> None:
    """Tuple fields (log_entries) are converted to lists of lists."""
    row = make_plan_row(42, "Test Plan")

    data = serialize_plan_row(row)

    assert isinstance(data["log_entries"], list)


def test_tuple_to_list_objective_deps_plans() -> None:
    """Tuple fields (objective_deps_plans) are converted to lists of lists."""
    row = make_plan_row(
        42,
        "Test Plan",
        objective_deps_plans=(("#100", "https://github.com/test/repo/issues/100"),),
    )

    data = serialize_plan_row(row)

    assert isinstance(data["objective_deps_plans"], list)
    assert data["objective_deps_plans"] == [["#100", "https://github.com/test/repo/issues/100"]]


def test_basic_fields_preserved() -> None:
    """Basic scalar fields are preserved in serialization."""
    row = make_plan_row(
        42,
        "My Test Plan",
        author="alice",
        pr_number=99,
        objective_issue=200,
    )

    data = serialize_plan_row(row)

    assert data["plan_id"] == 42
    assert data["full_title"] == "My Test Plan"
    assert data["author"] == "alice"
    assert data["pr_number"] == 99
    assert data["objective_issue"] == 200


def test_none_fields_preserved() -> None:
    """None values are preserved, not converted to strings."""
    row = make_plan_row(42, "Test Plan")

    data = serialize_plan_row(row)

    assert data["pr_number"] is None
    assert data["run_id"] is None
    assert data["objective_issue"] is None
