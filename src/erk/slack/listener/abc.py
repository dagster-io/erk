"""Abstract interface for receiving Slack events."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from erk.slack.types import SlackEvent


class SlackListener(ABC):
    """Abstract interface for receiving Slack events via Socket Mode.

    Implementations should handle the connection to Slack's Socket Mode API
    and yield SlackEvent objects as they are received.
    """

    @abstractmethod
    def listen(self) -> Iterator[SlackEvent]:
        """Listen for events via Socket Mode.

        This method blocks until stop() is called, yielding SlackEvent
        objects as they are received from Slack.

        Yields:
            SlackEvent objects as they are received
        """
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the listener gracefully.

        This method signals the listener to stop processing events
        and return from the listen() iterator.
        """
        ...
