"""Unit tests for codespace resolution helper."""

from datetime import datetime

import pytest

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry


def _make_codespace(name: str) -> RegisteredCodespace:
    return RegisteredCodespace(
        name=name,
        gh_name=f"user-{name}-abc",
        created_at=datetime(2026, 1, 20, 8, 0, 0),
    )


def test_resolve_by_name_returns_matching_codespace() -> None:
    """resolve_codespace returns the codespace when name matches."""
    cs = _make_codespace("mybox")
    registry = FakeCodespaceRegistry(codespaces=[cs])

    result = resolve_codespace(registry, "mybox")

    assert result is cs


def test_resolve_by_name_exits_when_not_found() -> None:
    """resolve_codespace raises SystemExit when named codespace not found."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(SystemExit):
        resolve_codespace(registry, "nonexistent")


def test_resolve_default_returns_default_codespace() -> None:
    """resolve_codespace returns default codespace when name is None."""
    cs = _make_codespace("mybox")
    registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")

    result = resolve_codespace(registry, None)

    assert result is cs


def test_resolve_default_exits_when_no_default_set() -> None:
    """resolve_codespace raises SystemExit when no default is set."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(SystemExit):
        resolve_codespace(registry, None)


def test_resolve_default_exits_when_default_not_found() -> None:
    """resolve_codespace raises SystemExit when default codespace was removed."""
    cs = _make_codespace("mybox")
    registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    registry.unregister("mybox")
    # Re-set default to simulate stale state
    registry._default_codespace = "mybox"

    with pytest.raises(SystemExit):
        resolve_codespace(registry, None)
