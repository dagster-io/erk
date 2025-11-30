"""Tests for FakePlannerRegistry test infrastructure.

These tests verify that FakePlannerRegistry correctly simulates planner operations,
providing reliable test doubles for CLI tests.
"""

from datetime import UTC, datetime

import pytest

from erk.core.planner.registry_fake import FakePlannerRegistry
from erk.core.planner.types import RegisteredPlanner


def _make_planner(
    name: str = "test-planner",
    gh_name: str = "test-gh-name",
    repository: str = "test-owner/test-repo",
    configured: bool = False,
) -> RegisteredPlanner:
    """Helper to create test planners."""
    return RegisteredPlanner(
        name=name,
        gh_name=gh_name,
        repository=repository,
        configured=configured,
        registered_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        last_connected_at=None,
    )


def test_fake_planner_registry_empty_initialization() -> None:
    """Test that FakePlannerRegistry initializes with empty state."""
    registry = FakePlannerRegistry()

    assert registry.list_planners() == []
    assert registry.get("any-name") is None
    assert registry.get_default() is None
    assert registry.get_default_name() is None


def test_fake_planner_registry_initialization_with_planners() -> None:
    """Test initialization with pre-configured planners."""
    planner1 = _make_planner(name="planner-1")
    planner2 = _make_planner(name="planner-2", gh_name="other-gh-name")

    registry = FakePlannerRegistry(planners=[planner1, planner2])

    planners = registry.list_planners()
    assert len(planners) == 2
    assert registry.get("planner-1") == planner1
    assert registry.get("planner-2") == planner2


def test_fake_planner_registry_initialization_with_default() -> None:
    """Test initialization with default planner."""
    planner = _make_planner(name="my-planner")

    registry = FakePlannerRegistry(planners=[planner], default_planner="my-planner")

    assert registry.get_default_name() == "my-planner"
    assert registry.get_default() == planner


def test_fake_planner_registry_register() -> None:
    """Test registering a new planner."""
    registry = FakePlannerRegistry()
    planner = _make_planner(name="new-planner")

    registry.register(planner)

    assert registry.get("new-planner") == planner
    assert len(registry.list_planners()) == 1
    # Verify mutation tracking
    assert registry.registered_planners == [planner]


def test_fake_planner_registry_register_duplicate_raises() -> None:
    """Test that registering duplicate name raises ValueError."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[planner])

    duplicate = _make_planner(name="my-planner", gh_name="different-gh")

    with pytest.raises(ValueError, match="already exists"):
        registry.register(duplicate)


def test_fake_planner_registry_unregister() -> None:
    """Test unregistering a planner."""
    planner = _make_planner(name="to-remove")
    registry = FakePlannerRegistry(planners=[planner])

    registry.unregister("to-remove")

    assert registry.get("to-remove") is None
    assert len(registry.list_planners()) == 0
    # Verify mutation tracking
    assert registry.unregistered_names == ["to-remove"]


def test_fake_planner_registry_unregister_nonexistent_raises() -> None:
    """Test that unregistering nonexistent planner raises ValueError."""
    registry = FakePlannerRegistry()

    with pytest.raises(ValueError, match="No planner named"):
        registry.unregister("nonexistent")


def test_fake_planner_registry_unregister_clears_default() -> None:
    """Test that unregistering the default planner clears the default."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[planner], default_planner="my-planner")

    registry.unregister("my-planner")

    assert registry.get_default_name() is None
    assert registry.get_default() is None


def test_fake_planner_registry_set_default() -> None:
    """Test setting the default planner."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[planner])

    registry.set_default("my-planner")

    assert registry.get_default_name() == "my-planner"
    assert registry.get_default() == planner
    # Verify mutation tracking
    assert registry.set_default_history == ["my-planner"]


def test_fake_planner_registry_set_default_nonexistent_raises() -> None:
    """Test that setting nonexistent planner as default raises ValueError."""
    registry = FakePlannerRegistry()

    with pytest.raises(ValueError, match="No planner named"):
        registry.set_default("nonexistent")


def test_fake_planner_registry_mark_configured() -> None:
    """Test marking a planner as configured."""
    planner = _make_planner(name="my-planner", configured=False)
    registry = FakePlannerRegistry(planners=[planner])

    registry.mark_configured("my-planner")

    updated = registry.get("my-planner")
    assert updated is not None
    assert updated.configured is True
    # Verify mutation tracking
    assert registry.marked_configured_names == ["my-planner"]


def test_fake_planner_registry_mark_configured_nonexistent_raises() -> None:
    """Test that marking nonexistent planner as configured raises ValueError."""
    registry = FakePlannerRegistry()

    with pytest.raises(ValueError, match="No planner named"):
        registry.mark_configured("nonexistent")


def test_fake_planner_registry_update_last_connected() -> None:
    """Test updating last_connected timestamp."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[planner])
    new_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)

    registry.update_last_connected("my-planner", new_time)

    updated = registry.get("my-planner")
    assert updated is not None
    assert updated.last_connected_at == new_time
    # Verify mutation tracking
    assert registry.updated_connections == [("my-planner", new_time)]


def test_fake_planner_registry_update_last_connected_nonexistent_raises() -> None:
    """Test that updating timestamp for nonexistent planner raises ValueError."""
    registry = FakePlannerRegistry()
    new_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="No planner named"):
        registry.update_last_connected("nonexistent", new_time)


def test_fake_planner_registry_mutation_tracking_returns_copies() -> None:
    """Test that mutation tracking properties return copies, not internal lists."""
    planner = _make_planner(name="my-planner")
    registry = FakePlannerRegistry()

    registry.register(planner)

    # Get the registered_planners list
    registered = registry.registered_planners

    # Try to modify it
    registered.append(_make_planner(name="fake-planner"))

    # Original should be unchanged
    assert len(registry.registered_planners) == 1


def test_fake_planner_registry_multiple_operations() -> None:
    """Test a sequence of multiple operations."""
    registry = FakePlannerRegistry()

    # Register two planners
    planner1 = _make_planner(name="planner-1")
    planner2 = _make_planner(name="planner-2", gh_name="other-gh")
    registry.register(planner1)
    registry.register(planner2)

    # Set default
    registry.set_default("planner-1")

    # Configure one
    registry.mark_configured("planner-2")

    # Update connection time
    connect_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=UTC)
    registry.update_last_connected("planner-1", connect_time)

    # Verify final state
    assert len(registry.list_planners()) == 2
    assert registry.get_default_name() == "planner-1"
    assert registry.get("planner-2").configured is True
    assert registry.get("planner-1").last_connected_at == connect_time

    # Verify all mutations tracked
    assert len(registry.registered_planners) == 2
    assert registry.set_default_history == ["planner-1"]
    assert registry.marked_configured_names == ["planner-2"]
    assert registry.updated_connections == [("planner-1", connect_time)]
