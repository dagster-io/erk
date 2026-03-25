"""Unit tests for codespace resolution helper."""

from datetime import datetime

import pytest

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from tests.fakes.gateway.codespace_registry import FakeCodespaceRegistry


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

    result = resolve_codespace(registry, "mybox", config_codespace_name=None)

    assert result is cs


def test_resolve_by_name_exits_when_not_found() -> None:
    """resolve_codespace raises SystemExit when named codespace not found."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(SystemExit):
        resolve_codespace(registry, "nonexistent", config_codespace_name=None)


def test_resolve_default_returns_default_codespace() -> None:
    """resolve_codespace returns default codespace when name is None."""
    cs = _make_codespace("mybox")
    registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")

    result = resolve_codespace(registry, None, config_codespace_name=None)

    assert result is cs


def test_resolve_default_exits_when_no_default_set() -> None:
    """resolve_codespace raises SystemExit when no default is set."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(SystemExit):
        resolve_codespace(registry, None, config_codespace_name=None)


def test_resolve_default_exits_when_default_not_found() -> None:
    """resolve_codespace raises SystemExit when default codespace was removed."""
    cs = _make_codespace("mybox")
    registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    registry.unregister("mybox")
    # Re-set default to simulate stale state
    registry._default_codespace = "mybox"

    with pytest.raises(SystemExit):
        resolve_codespace(registry, None, config_codespace_name=None)


def test_resolve_config_name_returns_matching_codespace() -> None:
    """resolve_codespace uses config_codespace_name when no CLI name provided."""
    cs = _make_codespace("config-box")
    registry = FakeCodespaceRegistry(codespaces=[cs])

    result = resolve_codespace(registry, None, config_codespace_name="config-box")

    assert result is cs


def test_resolve_cli_name_overrides_config_name() -> None:
    """CLI name takes precedence over config_codespace_name."""
    cs_cli = _make_codespace("cli-box")
    cs_config = _make_codespace("config-box")
    registry = FakeCodespaceRegistry(codespaces=[cs_cli, cs_config])

    result = resolve_codespace(registry, "cli-box", config_codespace_name="config-box")

    assert result is cs_cli


def test_resolve_config_name_overrides_global_default() -> None:
    """Config name takes precedence over global default."""
    cs_config = _make_codespace("config-box")
    cs_default = _make_codespace("default-box")
    registry = FakeCodespaceRegistry(
        codespaces=[cs_config, cs_default],
        default_codespace="default-box",
    )

    result = resolve_codespace(registry, None, config_codespace_name="config-box")

    assert result is cs_config


def test_resolve_config_name_exits_when_not_registered() -> None:
    """resolve_codespace raises SystemExit when config name references unregistered codespace."""
    registry = FakeCodespaceRegistry()

    with pytest.raises(SystemExit):
        resolve_codespace(registry, None, config_codespace_name="nonexistent")
