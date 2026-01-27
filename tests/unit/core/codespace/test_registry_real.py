"""Tests for RealCodespaceRegistry TOML storage."""

from datetime import datetime

import pytest

from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.real import (
    RealCodespaceRegistry,
    register_codespace,
    set_default_codespace,
    unregister_codespace,
)


class TestRealCodespaceRegistry:
    """Tests for RealCodespaceRegistry TOML operations."""

    def test_list_codespaces_empty(self, tmp_path):
        """list_codespaces returns empty list when config file doesn't exist."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry.from_config_path(config_path)

        result = registry.list_codespaces()

        assert result == []

    def test_from_config_path_creates_immutable_registry(self, tmp_path):
        """from_config_path creates a registry with loaded data."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        # Register using standalone function
        register_codespace(config_path, codespace)

        # Load using factory
        registry = RealCodespaceRegistry.from_config_path(config_path)

        assert registry.get("mybox") is not None
        assert registry.get("mybox").gh_name == "user-mybox-abc123"

    def test_get_returns_none_for_nonexistent(self, tmp_path):
        """get returns None for non-existent codespace."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry.from_config_path(config_path)

        result = registry.get("nonexistent")

        assert result is None

    def test_list_codespaces_returns_all(self, tmp_path):
        """list_codespaces returns all registered codespaces."""
        config_path = tmp_path / "codespaces.toml"
        cs1 = RegisteredCodespace(
            name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        cs2 = RegisteredCodespace(
            name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
        )
        register_codespace(config_path, cs1)
        register_codespace(config_path, cs2)

        registry = RealCodespaceRegistry.from_config_path(config_path)
        result = registry.list_codespaces()

        assert len(result) == 2
        names = {cs.name for cs in result}
        assert names == {"box1", "box2"}


class TestRegisterCodespace:
    """Tests for register_codespace standalone function."""

    def test_register_creates_file_and_stores_codespace(self, tmp_path):
        """register_codespace creates config file and stores codespace data."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )

        new_registry = register_codespace(config_path, codespace)

        # File should exist
        assert config_path.exists()
        # Codespace should be in returned registry
        retrieved = new_registry.get("mybox")
        assert retrieved is not None
        assert retrieved.name == "mybox"
        assert retrieved.gh_name == "user-mybox-abc123"
        assert retrieved.created_at == datetime(2026, 1, 20, 8, 39, 0)

    def test_register_raises_if_name_exists(self, tmp_path):
        """register_codespace raises ValueError if codespace name already exists."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        register_codespace(config_path, codespace)

        with pytest.raises(ValueError, match="already exists"):
            register_codespace(config_path, codespace)


class TestUnregisterCodespace:
    """Tests for unregister_codespace standalone function."""

    def test_unregister_removes_codespace(self, tmp_path):
        """unregister_codespace removes codespace from registry."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        register_codespace(config_path, codespace)

        new_registry = unregister_codespace(config_path, "mybox")

        assert new_registry.get("mybox") is None
        assert new_registry.list_codespaces() == []

    def test_unregister_raises_if_not_exists(self, tmp_path):
        """unregister_codespace raises ValueError if codespace doesn't exist."""
        config_path = tmp_path / "codespaces.toml"

        with pytest.raises(ValueError, match="No codespace named"):
            unregister_codespace(config_path, "nonexistent")

    def test_unregister_clears_default_if_removing_default(self, tmp_path):
        """unregister_codespace clears default when removing the default codespace."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        register_codespace(config_path, codespace)
        set_default_codespace(config_path, "mybox")

        new_registry = unregister_codespace(config_path, "mybox")

        assert new_registry.get_default_name() is None
        assert new_registry.get_default() is None


class TestSetDefaultCodespace:
    """Tests for set_default_codespace standalone function."""

    def test_set_default_and_get_default(self, tmp_path):
        """set_default_codespace and get_default work correctly."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        register_codespace(config_path, codespace)

        new_registry = set_default_codespace(config_path, "mybox")

        assert new_registry.get_default_name() == "mybox"
        default = new_registry.get_default()
        assert default is not None
        assert default.name == "mybox"

    def test_set_default_raises_if_not_exists(self, tmp_path):
        """set_default_codespace raises ValueError if codespace doesn't exist."""
        config_path = tmp_path / "codespaces.toml"

        with pytest.raises(ValueError, match="No codespace named"):
            set_default_codespace(config_path, "nonexistent")


class TestTomlFormat:
    """Tests for TOML format verification."""

    def test_toml_format_is_correct(self, tmp_path):
        """Verify TOML format matches expected schema."""
        config_path = tmp_path / "codespaces.toml"
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        register_codespace(config_path, codespace)
        set_default_codespace(config_path, "mybox")

        content = config_path.read_text(encoding="utf-8")

        assert "schema_version = 1" in content
        assert 'default_codespace = "mybox"' in content
        assert "[codespaces.mybox]" in content
        assert 'gh_name = "user-mybox-abc123"' in content
        assert 'created_at = "2026-01-20T08:39:00"' in content
