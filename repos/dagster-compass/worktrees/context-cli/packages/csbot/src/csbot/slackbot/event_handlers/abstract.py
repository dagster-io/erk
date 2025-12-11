"""
Abstract base class for Slack event handlers.

Defines the common interface for HTTP and WebSocket transport implementations.
"""

from abc import ABC, abstractmethod


class AbstractSlackEventHandler(ABC):
    """Base class for Slack event handlers.

    Implementations provide either HTTP webhooks (production) or WebSocket
    connections (development) for receiving Slack events. Each handler is
    responsible for transport details, authentication, and routing events
    to appropriate bot instances.
    """

    @abstractmethod
    async def start(self) -> None:
        """Initialize transport and begin listening for Slack events."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport and clean up resources."""
        pass
