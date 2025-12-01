"""Tests for SlackBotService."""

from datetime import datetime
from pathlib import Path

from erk_shared.integrations.time.fake import FakeTime

from erk.slack.agent.fake import FakeAgentSpawner
from erk.slack.listener.fake import FakeSlackListener
from erk.slack.service import SlackBotService
from erk.slack.thread_store.fake import FakeThreadStore
from erk.slack.types import SlackEvent, SlackMessage, ThreadRecord


class TestSlackBotService:
    """Tests for SlackBotService orchestrator."""

    def _create_service(
        self,
        listener: FakeSlackListener | None = None,
        thread_store: FakeThreadStore | None = None,
        agent_spawner: FakeAgentSpawner | None = None,
        time: FakeTime | None = None,
        repo_path: Path | None = None,
    ) -> tuple[SlackBotService, FakeSlackListener, FakeThreadStore, FakeAgentSpawner, FakeTime]:
        """Create a service with all fakes for testing.

        Returns tuple of (service, listener, thread_store, agent_spawner, time).
        """
        listener = listener or FakeSlackListener()
        thread_store = thread_store or FakeThreadStore()
        agent_spawner = agent_spawner or FakeAgentSpawner()
        time = time or FakeTime(datetime(2024, 1, 15, 10, 30, 0))
        repo_path = repo_path or Path("/tmp/repo")

        service = SlackBotService(
            listener=listener,
            thread_store=thread_store,
            agent_spawner=agent_spawner,
            time=time,
            repo_path=repo_path,
        )
        return service, listener, thread_store, agent_spawner, time

    def test_handles_app_mention_for_new_thread(self) -> None:
        """app_mention creates new thread record and spawns agent."""
        service, listener, thread_store, agent_spawner, time = self._create_service()

        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="@bot help me",
        )
        event = SlackEvent(event_type="app_mention", message=msg)
        listener.add_event(event)

        service.run()

        # Should spawn agent
        assert len(agent_spawner.spawn_calls) == 1
        call = agent_spawner.spawn_calls[0]
        assert call.channel == "C12345"
        assert call.thread_ts == "1234567890.123456"
        assert call.message == "@bot help me"
        assert call.session_id is None  # New thread

        # Should create thread record
        assert len(thread_store.records_upserted) == 1
        record = thread_store.records_upserted[0]
        assert record.channel == "C12345"
        assert record.thread_ts == "1234567890.123456"
        assert record.session_id is not None
        assert record.created_at == time.now()
        assert record.updated_at == time.now()

    def test_handles_message_in_tracked_thread(self) -> None:
        """message event in tracked thread spawns agent with session resume."""
        thread_store = FakeThreadStore()
        now = datetime(2024, 1, 15, 10, 0, 0)
        later = datetime(2024, 1, 15, 10, 30, 0)

        # Pre-populate a tracked thread
        existing_record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.000001",
            session_id="existing-session-123",
            last_message_ts="1234567890.000001",
            created_at=now,
            updated_at=now,
        )
        thread_store.upsert_thread(existing_record)

        time = FakeTime(later)
        service, listener, _, agent_spawner, _ = self._create_service(
            thread_store=thread_store, time=time
        )

        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.000002",
            thread_ts="1234567890.000001",  # Reply in tracked thread
            user="U12345",
            text="Follow up question",
        )
        event = SlackEvent(event_type="message", message=msg)
        listener.add_event(event)

        service.run()

        # Should spawn agent with existing session
        assert len(agent_spawner.spawn_calls) == 1
        call = agent_spawner.spawn_calls[0]
        assert call.session_id == "existing-session-123"

    def test_ignores_message_in_untracked_thread(self) -> None:
        """message event in untracked thread is ignored."""
        service, listener, thread_store, agent_spawner, _ = self._create_service()

        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.000002",
            thread_ts="1234567890.000001",  # Thread we're not tracking
            user="U12345",
            text="Some message",
        )
        event = SlackEvent(event_type="message", message=msg)
        listener.add_event(event)

        service.run()

        # Should NOT spawn agent
        assert len(agent_spawner.spawn_calls) == 0
        # Should NOT create thread record
        assert len(thread_store.records_upserted) == 0

    def test_preserves_created_at_on_thread_update(self) -> None:
        """Thread update preserves original created_at timestamp."""
        thread_store = FakeThreadStore()
        original_time = datetime(2024, 1, 15, 9, 0, 0)
        later = datetime(2024, 1, 15, 10, 0, 0)

        # Pre-populate a tracked thread
        existing_record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.000001",
            session_id="existing-session",
            last_message_ts="1234567890.000001",
            created_at=original_time,
            updated_at=original_time,
        )
        thread_store.upsert_thread(existing_record)

        time = FakeTime(later)
        service, listener, _, _, _ = self._create_service(thread_store=thread_store, time=time)

        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.000002",
            thread_ts="1234567890.000001",
            user="U12345",
            text="Another message",
        )
        event = SlackEvent(event_type="message", message=msg)
        listener.add_event(event)

        service.run()

        # Should have created new record but preserve created_at
        # records_upserted[0] is the initial setup, [1] is the update
        assert len(thread_store.records_upserted) == 2
        updated_record = thread_store.records_upserted[1]
        assert updated_record.created_at == original_time
        assert updated_record.updated_at == later

    def test_uses_repo_path_for_agent(self) -> None:
        """Agent is spawned with the configured repo_path."""
        service, listener, _, agent_spawner, _ = self._create_service(
            repo_path=Path("/my/special/repo")
        )

        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="@bot help",
        )
        event = SlackEvent(event_type="app_mention", message=msg)
        listener.add_event(event)

        service.run()

        assert agent_spawner.spawn_calls[0].repo_path == Path("/my/special/repo")

    def test_stop_stops_listener(self) -> None:
        """stop() calls stop on the listener."""
        service, listener, _, _, _ = self._create_service()

        # Add two events
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="@bot help",
        )
        event1 = SlackEvent(event_type="app_mention", message=msg)
        event2 = SlackEvent(event_type="app_mention", message=msg)
        listener.add_events([event1, event2])

        # Stop after first event
        def run_with_stop() -> int:
            count = 0
            for _event in listener.listen():
                count += 1
                if count == 1:
                    service.stop()
            return count

        count = run_with_stop()
        assert count == 1
