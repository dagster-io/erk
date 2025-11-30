"""Tests for FakeCodespaceRegistry test infrastructure.

These tests verify that FakeCodespaceRegistry correctly simulates registry operations,
providing reliable test doubles for codespace command tests.
"""

from datetime import datetime
from pathlib import Path

import pytest

from erk.core.codespace.registry_fake import FakeCodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace


def _make_codespace(
    friendly_name: str = "test-space",
    gh_name: str = "schrockn-abc123",
    configured: bool = False,
    last_connected_at: datetime | None = None,
) -> RegisteredCodespace:
    """Helper to create test codespaces."""
    return RegisteredCodespace(
        friendly_name=friendly_name,
        gh_name=gh_name,
        repository="schrockn/erk",
        branch="main",
        machine_type="standardLinux32gb",
        configured=configured,
        registered_at=datetime(2025, 1, 1, 12, 0, 0),
        last_connected_at=last_connected_at,
        notes=None,
    )


def test_fake_registry_initializes_empty() -> None:
    """Test that FakeCodespaceRegistry initializes with empty state."""
    registry = FakeCodespaceRegistry()

    assert not registry.exists()
    assert registry.list_codespaces() == []
    assert registry.get("any-name") is None


def test_fake_registry_initializes_with_codespaces() -> None:
    """Test initialization with pre-configured codespaces."""
    cs = _make_codespace("my-space")
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    assert registry.exists()
    assert len(registry.list_codespaces()) == 1
    assert registry.get("my-space") == cs


def test_fake_registry_register_creates_entry() -> None:
    """Test that register adds a codespace to the registry."""
    registry = FakeCodespaceRegistry()
    cs = _make_codespace("new-space")

    registry.register(cs)

    assert registry.exists()
    assert registry.get("new-space") == cs


def test_fake_registry_register_duplicate_raises() -> None:
    """Test that registering duplicate name raises ValueError."""
    cs = _make_codespace("my-space")
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    with pytest.raises(ValueError, match="already exists"):
        registry.register(cs)


def test_fake_registry_unregister_removes_entry() -> None:
    """Test that unregister removes a codespace."""
    cs = _make_codespace("my-space")
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    registry.unregister("my-space")

    assert registry.get("my-space") is None


def test_fake_registry_unregister_missing_raises() -> None:
    """Test that unregistering non-existent codespace raises KeyError."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(KeyError, match="not found"):
        registry.unregister("nonexistent")


def test_fake_registry_update_modifies_entry() -> None:
    """Test that update replaces a codespace entry."""
    cs = _make_codespace("my-space", configured=False)
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    updated = _make_codespace("my-space", configured=True)
    registry.update(updated)

    result = registry.get("my-space")
    assert result is not None
    assert result.configured is True


def test_fake_registry_update_missing_raises() -> None:
    """Test that updating non-existent codespace raises KeyError."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(KeyError, match="not found"):
        registry.update(_make_codespace("nonexistent"))


def test_fake_registry_update_last_connected() -> None:
    """Test that update_last_connected updates timestamp."""
    cs = _make_codespace("my-space", last_connected_at=None)
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    new_time = datetime(2025, 6, 15, 10, 30, 0)
    registry.update_last_connected("my-space", new_time)

    result = registry.get("my-space")
    assert result is not None
    assert result.last_connected_at == new_time


def test_fake_registry_update_last_connected_missing_raises() -> None:
    """Test that updating last_connected for missing codespace raises KeyError."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(KeyError, match="not found"):
        registry.update_last_connected("nonexistent", datetime.now())


def test_fake_registry_mark_configured() -> None:
    """Test that mark_configured sets configured=True."""
    cs = _make_codespace("my-space", configured=False)
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    registry.mark_configured("my-space")

    result = registry.get("my-space")
    assert result is not None
    assert result.configured is True


def test_fake_registry_mark_configured_missing_raises() -> None:
    """Test that mark_configured for missing codespace raises KeyError."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(KeyError, match="not found"):
        registry.mark_configured("nonexistent")


def test_fake_registry_list_sorts_by_last_connected() -> None:
    """Test that list_codespaces sorts by last_connected_at descending."""
    cs1 = _make_codespace("space-1", last_connected_at=datetime(2025, 1, 1))
    cs2 = _make_codespace("space-2", last_connected_at=datetime(2025, 6, 1))
    cs3 = _make_codespace("space-3", last_connected_at=None)

    registry = FakeCodespaceRegistry(codespaces={"space-1": cs1, "space-2": cs2, "space-3": cs3})

    result = registry.list_codespaces()

    # Most recently connected first, never-connected last
    assert result[0].friendly_name == "space-2"
    assert result[1].friendly_name == "space-1"
    assert result[2].friendly_name == "space-3"


def test_fake_registry_path_returns_fake_path() -> None:
    """Test that path returns a fake path for error messages."""
    registry = FakeCodespaceRegistry()

    path = registry.path()

    assert path == Path("/fake/erk/codespaces.toml")


def test_fake_registry_codespaces_property_returns_copy() -> None:
    """Test that codespaces property returns a copy, not internal state."""
    cs = _make_codespace("my-space")
    registry = FakeCodespaceRegistry(codespaces={"my-space": cs})

    # Get the codespaces dict
    codespaces = registry.codespaces

    # Modify the returned dict
    codespaces["fake"] = _make_codespace("fake")

    # Original should be unchanged
    assert "fake" not in registry.codespaces
    assert len(registry.codespaces) == 1
