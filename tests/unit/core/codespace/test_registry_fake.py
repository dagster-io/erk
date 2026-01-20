"""Tests for FakeCodespaceRegistry mutation tracking."""

from datetime import datetime

import pytest

from erk.core.codespace.registry_fake import FakeCodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace


class TestFakeCodespaceRegistry:
    """Tests for FakeCodespaceRegistry mutation tracking."""

    def test_initialized_with_codespaces(self):
        """Fake registry can be initialized with codespaces."""
        cs = RegisteredCodespace(
            name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")

        assert registry.get("mybox") == cs
        assert registry.get_default() == cs
        assert registry.get_default_name() == "mybox"

    def test_tracks_registered_codespaces(self):
        """Fake registry tracks registered codespaces for assertions."""
        registry = FakeCodespaceRegistry()
        cs = RegisteredCodespace(
            name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )

        registry.register(cs)

        assert registry.registered_codespaces == [cs]

    def test_tracks_unregistered_names(self):
        """Fake registry tracks unregistered names for assertions."""
        cs = RegisteredCodespace(
            name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        registry = FakeCodespaceRegistry(codespaces=[cs])

        registry.unregister("mybox")

        assert registry.unregistered_names == ["mybox"]

    def test_tracks_set_default_history(self):
        """Fake registry tracks set_default calls for assertions."""
        cs = RegisteredCodespace(
            name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        registry = FakeCodespaceRegistry(codespaces=[cs])

        registry.set_default("mybox")

        assert registry.set_default_history == ["mybox"]

    def test_register_raises_if_name_exists(self):
        """register raises ValueError if codespace name already exists."""
        cs = RegisteredCodespace(
            name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        registry = FakeCodespaceRegistry(codespaces=[cs])

        with pytest.raises(ValueError, match="already exists"):
            registry.register(cs)

    def test_unregister_raises_if_not_exists(self):
        """unregister raises ValueError if codespace doesn't exist."""
        registry = FakeCodespaceRegistry()

        with pytest.raises(ValueError, match="No codespace named"):
            registry.unregister("nonexistent")

    def test_set_default_raises_if_not_exists(self):
        """set_default raises ValueError if codespace doesn't exist."""
        registry = FakeCodespaceRegistry()

        with pytest.raises(ValueError, match="No codespace named"):
            registry.set_default("nonexistent")

    def test_unregister_clears_default(self):
        """unregister clears default when removing default codespace."""
        cs = RegisteredCodespace(
            name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")

        registry.unregister("mybox")

        assert registry.get_default_name() is None
        assert registry.get_default() is None

    def test_list_codespaces(self):
        """list_codespaces returns all codespaces."""
        cs1 = RegisteredCodespace(
            name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
        )
        cs2 = RegisteredCodespace(
            name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
        )
        registry = FakeCodespaceRegistry(codespaces=[cs1, cs2])

        result = registry.list_codespaces()

        assert len(result) == 2
