"""Tests for session source abstraction.

Layer 3 (Pure Unit Tests): Tests for session source implementations
with zero dependencies.
"""

from erk_shared.learn.extraction.session_source import (
    LocalSessionSource,
    RemoteSessionSource,
    SessionSource,
)


class TestLocalSessionSource:
    """Test LocalSessionSource implementation."""

    def test_source_type_is_local(self) -> None:
        """source_type returns 'local'."""
        source = LocalSessionSource(_session_id="test-session-123")
        assert source.source_type == "local"

    def test_session_id_returns_provided_value(self) -> None:
        """session_id returns the provided session ID."""
        source = LocalSessionSource(_session_id="abc-def-ghi-123")
        assert source.session_id == "abc-def-ghi-123"

    def test_run_id_is_none(self) -> None:
        """run_id returns None for local sessions."""
        source = LocalSessionSource(_session_id="test-session")
        assert source.run_id is None

    def test_path_returns_none_by_default(self) -> None:
        """path returns None when not provided."""
        source = LocalSessionSource(_session_id="test-session")
        assert source.path is None

    def test_path_returns_provided_value(self) -> None:
        """path returns the provided path."""
        source = LocalSessionSource(
            _session_id="test-session",
            _path="/Users/test/.claude/sessions/test-session.jsonl",
        )
        assert source.path == "/Users/test/.claude/sessions/test-session.jsonl"

    def test_is_session_source_subclass(self) -> None:
        """LocalSessionSource is a SessionSource."""
        source = LocalSessionSource(_session_id="test")
        assert isinstance(source, SessionSource)

    def test_is_frozen_dataclass(self) -> None:
        """LocalSessionSource is immutable."""
        source = LocalSessionSource(_session_id="test")
        # Attempting to modify should raise FrozenInstanceError
        try:
            source._session_id = "modified"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected behavior

    def test_to_dict_serializes_all_fields(self) -> None:
        """to_dict() serializes all fields to a dictionary."""
        source = LocalSessionSource(
            _session_id="abc-123",
            _path="/path/to/session.jsonl",
        )
        result = source.to_dict()
        assert result == {
            "source_type": "local",
            "session_id": "abc-123",
            "run_id": None,
            "path": "/path/to/session.jsonl",
        }

    def test_to_dict_with_none_path(self) -> None:
        """to_dict() works when path is None."""
        source = LocalSessionSource(_session_id="abc-123")
        result = source.to_dict()
        assert result == {
            "source_type": "local",
            "session_id": "abc-123",
            "run_id": None,
            "path": None,
        }


class TestRemoteSessionSource:
    """Test RemoteSessionSource implementation."""

    def test_source_type_is_remote(self) -> None:
        """source_type returns 'remote'."""
        source = RemoteSessionSource(_session_id="test-session", _run_id="12345")
        assert source.source_type == "remote"

    def test_session_id_returns_provided_value(self) -> None:
        """session_id returns the provided session ID."""
        source = RemoteSessionSource(_session_id="abc-def-ghi", _run_id="12345")
        assert source.session_id == "abc-def-ghi"

    def test_run_id_returns_provided_value(self) -> None:
        """run_id returns the provided run ID."""
        source = RemoteSessionSource(_session_id="test", _run_id="run-98765")
        assert source.run_id == "run-98765"

    def test_path_is_none(self) -> None:
        """path returns None for remote sessions (until downloaded)."""
        source = RemoteSessionSource(_session_id="test", _run_id="123")
        assert source.path is None

    def test_is_session_source_subclass(self) -> None:
        """RemoteSessionSource is a SessionSource."""
        source = RemoteSessionSource(_session_id="test", _run_id="123")
        assert isinstance(source, SessionSource)

    def test_is_frozen_dataclass(self) -> None:
        """RemoteSessionSource is immutable."""
        source = RemoteSessionSource(_session_id="test", _run_id="123")
        # Attempting to modify should raise FrozenInstanceError
        try:
            source._session_id = "modified"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected behavior

    def test_to_dict_serializes_all_fields(self) -> None:
        """to_dict() serializes all fields to a dictionary."""
        source = RemoteSessionSource(_session_id="abc-123", _run_id="run-456")
        result = source.to_dict()
        assert result == {
            "source_type": "remote",
            "session_id": "abc-123",
            "run_id": "run-456",
            "path": None,
        }


class TestSessionSourcePolymorphism:
    """Test that both implementations work polymorphically."""

    def test_local_and_remote_share_interface(self) -> None:
        """Both sources share the same interface."""
        local: SessionSource = LocalSessionSource(_session_id="local-123")
        remote: SessionSource = RemoteSessionSource(_session_id="remote-456", _run_id="run-789")

        # Both have source_type
        assert local.source_type == "local"
        assert remote.source_type == "remote"

        # Both have session_id
        assert local.session_id == "local-123"
        assert remote.session_id == "remote-456"

        # Both have run_id (None for local)
        assert local.run_id is None
        assert remote.run_id == "run-789"

    def test_can_use_in_list(self) -> None:
        """Can collect mixed sources in a list."""
        sources: list[SessionSource] = [
            LocalSessionSource(_session_id="local-1"),
            RemoteSessionSource(_session_id="remote-1", _run_id="run-1"),
            LocalSessionSource(_session_id="local-2"),
        ]

        assert len(sources) == 3
        assert sources[0].source_type == "local"
        assert sources[1].source_type == "remote"
        assert sources[2].source_type == "local"
