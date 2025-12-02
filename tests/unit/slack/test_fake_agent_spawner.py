"""Tests for FakeAgentSpawner."""

from pathlib import Path

from erk.slack.agent.fake import FakeAgentSpawner


class TestFakeAgentSpawner:
    """Tests for FakeAgentSpawner."""

    def test_spawn_returns_success_by_default(self) -> None:
        """spawn returns successful result by default."""
        spawner = FakeAgentSpawner()

        result = spawner.spawn(
            channel="C12345",
            thread_ts="1234567890.123456",
            message="Hello",
            repo_path=Path("/tmp/repo"),
        )

        assert result.success is True
        assert result.error_message is None
        assert result.session_id is not None  # Generated UUID

    def test_spawn_records_call(self) -> None:
        """spawn records the call parameters."""
        spawner = FakeAgentSpawner()

        spawner.spawn(
            channel="C12345",
            thread_ts="1234567890.123456",
            message="Hello bot",
            repo_path=Path("/tmp/repo"),
            session_id="existing-session",
        )

        assert len(spawner.spawn_calls) == 1
        call = spawner.spawn_calls[0]
        assert call.channel == "C12345"
        assert call.thread_ts == "1234567890.123456"
        assert call.message == "Hello bot"
        assert call.repo_path == Path("/tmp/repo")
        assert call.session_id == "existing-session"

    def test_set_next_result_configures_success(self) -> None:
        """set_next_result configures success status."""
        spawner = FakeAgentSpawner()
        spawner.set_next_result(success=True)

        result = spawner.spawn(
            channel="C12345",
            thread_ts="1234567890.123456",
            message="Hello",
            repo_path=Path("/tmp/repo"),
        )

        assert result.success is True

    def test_set_next_result_configures_failure(self) -> None:
        """set_next_result configures failure with error message."""
        spawner = FakeAgentSpawner()
        spawner.set_next_result(success=False, error_message="Agent crashed")

        result = spawner.spawn(
            channel="C12345",
            thread_ts="1234567890.123456",
            message="Hello",
            repo_path=Path("/tmp/repo"),
        )

        assert result.success is False
        assert result.error_message == "Agent crashed"

    def test_set_next_result_configures_session_id(self) -> None:
        """set_next_result can specify exact session_id."""
        spawner = FakeAgentSpawner()
        spawner.set_next_result(session_id="specific-session-123")

        result = spawner.spawn(
            channel="C12345",
            thread_ts="1234567890.123456",
            message="Hello",
            repo_path=Path("/tmp/repo"),
        )

        assert result.session_id == "specific-session-123"

    def test_spawn_calls_returns_copy(self) -> None:
        """spawn_calls returns a copy of the internal list."""
        spawner = FakeAgentSpawner()

        spawner.spawn(
            channel="C12345",
            thread_ts="1234567890.123456",
            message="Hello",
            repo_path=Path("/tmp/repo"),
        )

        calls_copy = spawner.spawn_calls
        calls_copy.clear()

        assert len(spawner.spawn_calls) == 1

    def test_multiple_spawns_recorded_in_order(self) -> None:
        """Multiple spawns are recorded in order."""
        spawner = FakeAgentSpawner()

        spawner.spawn("C1", "ts1", "msg1", Path("/repo1"))
        spawner.spawn("C2", "ts2", "msg2", Path("/repo2"))
        spawner.spawn("C3", "ts3", "msg3", Path("/repo3"))

        assert len(spawner.spawn_calls) == 3
        assert spawner.spawn_calls[0].channel == "C1"
        assert spawner.spawn_calls[1].channel == "C2"
        assert spawner.spawn_calls[2].channel == "C3"
