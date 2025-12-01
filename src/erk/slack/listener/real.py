"""Real implementation of SlackListener using Slack Bolt Socket Mode."""

import threading
from collections.abc import Iterator
from queue import Empty, Queue

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from erk.slack.listener.abc import SlackListener
from erk.slack.types import SlackEvent, SlackMessage


class RealSlackListener(SlackListener):
    """Production implementation using Slack Bolt's Socket Mode.

    This implementation connects to Slack via Socket Mode and yields
    events as they are received.

    Attributes:
        bot_token: The Bot User OAuth Token (xoxb-...)
        app_token: The App-Level Token for Socket Mode (xapp-...)
    """

    def __init__(self, bot_token: str, app_token: str) -> None:
        """Initialize the listener with Slack credentials.

        Args:
            bot_token: Bot User OAuth Token (SLACK_BOT_TOKEN)
            app_token: App-Level Token for Socket Mode (SLACK_APP_TOKEN)
        """
        self._bot_token = bot_token
        self._app_token = app_token
        self._event_queue: Queue[SlackEvent | None] = Queue()
        self._stopped = False
        self._handler: SocketModeHandler | None = None

    def listen(self) -> Iterator[SlackEvent]:
        """Listen for events via Socket Mode.

        This method starts the Socket Mode handler in a background thread
        and yields events as they are received. Call stop() to terminate.

        Yields:
            SlackEvent objects as they are received from Slack
        """
        # Create Bolt app
        app = App(token=self._bot_token)

        # Register event handlers that push to our queue
        @app.event("app_mention")
        def handle_app_mention(event: dict, say: object) -> None:  # noqa: ARG001
            slack_event = self._convert_event("app_mention", event)
            self._event_queue.put(slack_event)

        @app.event("message")
        def handle_message(event: dict, say: object) -> None:  # noqa: ARG001
            # Only process thread replies (messages with thread_ts)
            if "thread_ts" in event:
                slack_event = self._convert_event("message", event)
                self._event_queue.put(slack_event)

        # Start Socket Mode handler in background thread
        self._handler = SocketModeHandler(app, self._app_token)

        def run_handler() -> None:
            if self._handler is not None:
                self._handler.start()

        handler_thread = threading.Thread(target=run_handler, daemon=True)
        handler_thread.start()

        # Yield events from queue
        while not self._stopped:
            event = None
            try:
                event = self._event_queue.get(timeout=1.0)
            except Empty:
                continue

            if event is None:
                break
            yield event

    def stop(self) -> None:
        """Stop the listener gracefully."""
        self._stopped = True
        # Signal the queue to unblock
        self._event_queue.put(None)
        # Stop the handler
        if self._handler is not None:
            self._handler.close()

    def _convert_event(self, event_type: str, event: dict) -> SlackEvent:
        """Convert a Slack event dict to a SlackEvent.

        Args:
            event_type: The type of event ("app_mention", "message")
            event: The raw event dict from Slack

        Returns:
            A SlackEvent with the extracted message data
        """
        message = SlackMessage(
            channel=event.get("channel", ""),
            ts=event.get("ts", ""),
            thread_ts=event.get("thread_ts"),
            user=event.get("user", ""),
            text=event.get("text", ""),
        )
        return SlackEvent(event_type=event_type, message=message)
