"""Tests for RealCodespaceRegistry TOML storage."""

from datetime import datetime

import pytest

from erk.core.codespace.registry_real import RealCodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace


class TestRealCodespaceRegistry:
    """Tests for RealCodespaceRegistry TOML operations."""

    def test_list_codespaces_empty(self, tmp_path):
        """list_codespaces returns empty list when config file doesn't exist."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)

        result = registry.list_codespaces()

        assert result == []

    def test_register_creates_file_and_stores_codespace(self, tmp_path):
        """register creates config file and stores codespace data."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )

        registry.register(codespace)

        # File should exist
        assert config_path.exists()
        # Codespace should be retrievable
        retrieved = registry.get("mybox")
        assert retrieved is not None
        assert retrieved.name == "mybox"
        assert retrieved.gh_name == "user-mybox-abc123"
        assert retrieved.created_at == datetime(2026, 1, 20, 8, 39, 0)

    def test_register_raises_if_name_exists(self, tmp_path):
        """register raises ValueError if codespace name already exists."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        registry.register(codespace)

        with pytest.raises(ValueError, match="already exists"):
            registry.register(codespace)

    def test_get_returns_none_for_nonexistent(self, tmp_path):
        """get returns None for non-existent codespace."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)

        result = registry.get("nonexistent")

        assert result is None

    def test_unregister_removes_codespace(self, tmp_path):
        """unregister removes codespace from registry."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        registry.register(codespace)

        registry.unregister("mybox")

        assert registry.get("mybox") is None
        assert registry.list_codespaces() == []

    def test_unregister_raises_if_not_exists(self, tmp_path):
        """unregister raises ValueError if codespace doesn't exist."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)

        with pytest.raises(ValueError, match="No codespace named"):
            registry.unregister("nonexistent")

    def test_set_default_and_get_default(self, tmp_path):
        """set_default and get_default work correctly."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        registry.register(codespace)

        registry.set_default("mybox")

        assert registry.get_default_name() == "mybox"
        default = registry.get_default()
        assert default is not None
        assert default.name == "mybox"

    def test_set_default_raises_if_not_exists(self, tmp_path):
        """set_default raises ValueError if codespace doesn't exist."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)

        with pytest.raises(ValueError, match="No codespace named"):
            registry.set_default("nonexistent")

    def test_unregister_clears_default_if_removing_default(self, tmp_path):
        """unregister clears default when removing the default codespace."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        registry.register(codespace)
        registry.set_default("mybox")

        registry.unregister("mybox")

        assert registry.get_default_name() is None
        assert registry.get_default() is None

    def test_list_codespaces_returns_all(self, tmp_path):
        """list_codespaces returns all registered codespaces."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        cs1 = RegisteredCodespace(
            name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        cs2 = RegisteredCodespace(
            name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
        )
        registry.register(cs1)
        registry.register(cs2)

        result = registry.list_codespaces()

        assert len(result) == 2
        names = {cs.name for cs in result}
        assert names == {"box1", "box2"}

    def test_toml_format_is_correct(self, tmp_path):
        """Verify TOML format matches expected schema."""
        config_path = tmp_path / "codespaces.toml"
        registry = RealCodespaceRegistry(config_path)
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2026, 1, 20, 8, 39, 0),
        )
        registry.register(codespace)
        registry.set_default("mybox")

        content = config_path.read_text(encoding="utf-8")

        assert "schema_version = 1" in content
        assert 'default_codespace = "mybox"' in content
        assert "[codespaces.mybox]" in content
        assert 'gh_name = "user-mybox-abc123"' in content
        assert 'created_at = "2026-01-20T08:39:00"' in content
