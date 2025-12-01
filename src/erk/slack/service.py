"""SlackBotService - orchestrates Slack bot components."""

from pathlib import Path

from erk_shared.integrations.time.abc import Time

from erk.slack.agent.abc import AgentSpawner
from erk.slack.listener.abc import SlackListener
from erk.slack.thread_store.abc import ThreadStore
from erk.slack.types import SlackEvent, ThreadRecord


class SlackBotService:
    """Orchestrates Slack bot: listen → spawn agent → track state.

    This service coordinates the listener, thread store, and agent spawner
    to provide a complete Slack bot experience.

    The service listens for Slack events, spawns Claude agents to handle
    messages, and tracks thread state for conversation continuity.
    """

    def __init__(
        self,
        listener: SlackListener,
        thread_store: ThreadStore,
        agent_spawner: AgentSpawner,
        time: Time,
        repo_path: Path,
    ) -> None:
        """Initialize the service with dependencies.

        Args:
            listener: SlackListener for receiving events
            thread_store: ThreadStore for persistence
            agent_spawner: AgentSpawner for Claude agent execution
            time: Time abstraction for timestamps
            repo_path: Path to repository for agent context
        """
        self._listener = listener
        self._thread_store = thread_store
        self._agent_spawner = agent_spawner
        self._time = time
        self._repo_path = repo_path

    def run(self) -> None:
        """Main event loop.

        Listens for Slack events and handles each one by spawning
        an agent and tracking thread state.
        """
        for event in self._listener.listen():
            self._handle_event(event)

    def _handle_event(self, event: SlackEvent) -> None:
        """Handle a single Slack event.

        For app_mention events, always spawn an agent (new thread).
        For message events, only handle if we're already tracking the thread.

        Args:
            event: The SlackEvent to handle
        """
        msg = event.message
        # Use thread_ts if in a thread, otherwise use message ts as thread root
        thread_ts = msg.thread_ts if msg.thread_ts is not None else msg.ts

        # Check if this is a thread we're tracking (or new mention)
        existing = self._thread_store.get_thread(msg.channel, thread_ts)

        # Ignore non-mention messages in threads we don't own
        if existing is None and event.event_type != "app_mention":
            return

        # Get session ID for conversation resume
        session_id = existing.session_id if existing is not None else None

        # Spawn agent to handle message
        result = self._agent_spawner.spawn(
            channel=msg.channel,
            thread_ts=thread_ts,
            message=msg.text,
            repo_path=self._repo_path,
            session_id=session_id,
        )

        # Update thread state
        now = self._time.now()
        created_at = existing.created_at if existing is not None else now
        record = ThreadRecord(
            channel=msg.channel,
            thread_ts=thread_ts,
            session_id=result.session_id,
            last_message_ts=msg.ts,
            created_at=created_at,
            updated_at=now,
        )
        self._thread_store.upsert_thread(record)

    def stop(self) -> None:
        """Stop the service.

        Signals the listener to stop processing events.
        """
        self._listener.stop()
