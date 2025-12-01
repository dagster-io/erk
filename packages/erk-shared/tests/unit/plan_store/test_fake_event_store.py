"""Unit tests for FakePlanEventStore."""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.plan_store.event_store import PlanEvent, PlanEventType
from erk_shared.plan_store.fake_event_store import FakePlanEventStore


def test_append_event_creates_list_for_new_plan() -> None:
    """Test that appending creates a new list for unknown plan."""
    store = FakePlanEventStore()
    event = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={"creator": "test-user"},
    )

    store.append_event(Path("/fake"), "42", event)

    assert "42" in store.all_events
    assert len(store.all_events["42"]) == 1
    assert store.all_events["42"][0] == event


def test_append_event_adds_to_existing_list() -> None:
    """Test that appending adds to existing event list."""
    store = FakePlanEventStore()
    event1 = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={},
    )
    event2 = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        data={"workflow_name": "test"},
    )

    store.append_event(Path("/fake"), "42", event1)
    store.append_event(Path("/fake"), "42", event2)

    assert len(store.all_events["42"]) == 2


def test_get_events_empty_for_unknown_plan() -> None:
    """Test that getting events for unknown plan returns empty list."""
    store = FakePlanEventStore()

    events = store.get_events(Path("/fake"), "unknown")

    assert events == []


def test_get_events_returns_all_events_sorted() -> None:
    """Test that get_events returns all events sorted by timestamp."""
    store = FakePlanEventStore()

    # Add events out of order
    event_later = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        data={},
    )
    event_earlier = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={},
    )

    store.append_event(Path("/fake"), "42", event_later)
    store.append_event(Path("/fake"), "42", event_earlier)

    events = store.get_events(Path("/fake"), "42")

    assert len(events) == 2
    assert events[0] == event_earlier
    assert events[1] == event_later


def test_get_events_filters_by_type() -> None:
    """Test that get_events can filter by event type."""
    store = FakePlanEventStore()

    created_event = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={},
    )
    queued_event = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        data={},
    )
    progress_event = PlanEvent(
        event_type=PlanEventType.PROGRESS,
        timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        data={},
    )

    store.append_event(Path("/fake"), "42", created_event)
    store.append_event(Path("/fake"), "42", queued_event)
    store.append_event(Path("/fake"), "42", progress_event)

    # Filter for single type
    queued_events = store.get_events(Path("/fake"), "42", [PlanEventType.QUEUED])
    assert len(queued_events) == 1
    assert queued_events[0] == queued_event

    # Filter for multiple types
    filtered = store.get_events(
        Path("/fake"), "42", [PlanEventType.CREATED, PlanEventType.PROGRESS]
    )
    assert len(filtered) == 2
    assert created_event in filtered
    assert progress_event in filtered


def test_get_latest_event_returns_none_for_empty() -> None:
    """Test that get_latest_event returns None when no events."""
    store = FakePlanEventStore()

    result = store.get_latest_event(Path("/fake"), "unknown")

    assert result is None


def test_get_latest_event_returns_most_recent() -> None:
    """Test that get_latest_event returns the most recent event."""
    store = FakePlanEventStore()

    event1 = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={},
    )
    event2 = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        data={},
    )
    event3 = PlanEvent(
        event_type=PlanEventType.PROGRESS,
        timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        data={},
    )

    # Add out of order
    store.append_event(Path("/fake"), "42", event1)
    store.append_event(Path("/fake"), "42", event2)
    store.append_event(Path("/fake"), "42", event3)

    # Should return event2 (latest by timestamp)
    result = store.get_latest_event(Path("/fake"), "42")
    assert result == event2


def test_get_latest_event_with_type_filter() -> None:
    """Test that get_latest_event can filter by type."""
    store = FakePlanEventStore()

    progress1 = PlanEvent(
        event_type=PlanEventType.PROGRESS,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={"step": 1},
    )
    queued = PlanEvent(
        event_type=PlanEventType.QUEUED,
        timestamp=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        data={},
    )
    progress2 = PlanEvent(
        event_type=PlanEventType.PROGRESS,
        timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC),
        data={"step": 2},
    )

    store.append_event(Path("/fake"), "42", progress1)
    store.append_event(Path("/fake"), "42", queued)
    store.append_event(Path("/fake"), "42", progress2)

    # Get latest progress event
    result = store.get_latest_event(Path("/fake"), "42", PlanEventType.PROGRESS)
    assert result == progress2
    assert result.data.get("step") == 2

    # Get latest queued event
    result_queued = store.get_latest_event(Path("/fake"), "42", PlanEventType.QUEUED)
    assert result_queued == queued


def test_events_are_isolated_by_plan_identifier() -> None:
    """Test that events for different plans are kept separate."""
    store = FakePlanEventStore()

    event_plan1 = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={"plan": "1"},
    )
    event_plan2 = PlanEvent(
        event_type=PlanEventType.CREATED,
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        data={"plan": "2"},
    )

    store.append_event(Path("/fake"), "plan-1", event_plan1)
    store.append_event(Path("/fake"), "plan-2", event_plan2)

    events_1 = store.get_events(Path("/fake"), "plan-1")
    events_2 = store.get_events(Path("/fake"), "plan-2")

    assert len(events_1) == 1
    assert events_1[0].data.get("plan") == "1"

    assert len(events_2) == 1
    assert events_2[0].data.get("plan") == "2"
