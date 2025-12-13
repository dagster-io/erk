"""Protocol definition for context engine implementations.

This protocol defines the interface that all context engine implementations must follow.
Using a protocol ensures that read-only and standard context engines explicitly implement
all methods, preventing accidental mutations from leaking into read-only implementations.

Note: This protocol uses TYPE_CHECKING to avoid runtime protocol checking issues with
decorators like @sync_to_async and @cached_property. The protocol serves as documentation
and static type checking only.
"""

from typing import TYPE_CHECKING, Any, Protocol

from csbot.contextengine.contextstore_protocol import ContextStore


class ContextStoreManager(Protocol):
    """Protocol for managing context store read and write operations.

    Combines both provider (read) and mutator (write) capabilities.
    """

    async def get_context_store(self) -> ContextStore:
        """Get the current ContextStore state."""
        ...

    async def mutate(
        self, title: str, body: str, commit: bool, before: ContextStore, after: ContextStore
    ) -> str:
        """Mutate the context store.

        Returns:
            PR URL or commit URL
        """
        ...


class ReadOnlyContextStoreManager:
    """Context store manager that provides read-only access.

    Used for read-only context engines that should not support mutations.
    Provides read access but blocks write operations.
    """

    def __init__(self, provider):
        self._provider = provider

    async def get_context_store(self) -> ContextStore:
        """Get the current ContextStore state (delegated to provider)."""
        return await self._provider.get_context_store()

    async def mutate(
        self, title: str, body: str, commit: bool, before: ContextStore, after: ContextStore
    ) -> str:
        raise RuntimeError(
            "Attempted to mutate a read-only context store. This operation is not permitted."
        )


if TYPE_CHECKING:
    # Legacy alias for backward compatibility in type stubs
    UnsupportedContextStoreManager = ReadOnlyContextStoreManager

    class ContextEngineProtocol(Protocol):
        """Protocol defining the interface for context engine implementations.

        Implementations include:
        - ContextEngine: Full-featured engine with read-write access
        - ProspectorReadOnlyContextEngine: Read-only engine for prospector instances

        This protocol is used for type hints only - at runtime, duck typing is used
        to allow both implementations without protocol checking complications.
        """

        @property
        def normalized_channel_name(self) -> str | None:
            """Access to normalized channel name."""
            ...

        @property
        def available_connection_names(self) -> set[str]:
            """Access to available connection names."""
            ...

        def supports_add_context(self) -> bool:
            """Check if this context engine supports adding context."""
            ...

        def add_context(
            self,
            topic: str,
            incorrect_understanding: str,
            correct_understanding: str,
            attribution: str | None,
        ) -> Any:
            """Add context to the context store with AI-generated summary and keywords."""
            ...

        def supports_cron_jobs(self) -> bool:
            """Check if this context engine supports cron jobs."""
            ...

        def get_cron_jobs(self) -> Any:
            """Get all cron jobs for the current channel."""
            ...

        def add_cron_job(
            self,
            cron_job_name: str,
            cron_string: str,
            question: str,
            thread: str,
            attribution: str | None,
        ) -> Any:
            """Add a new cron job."""
            ...

        def update_cron_job(
            self,
            cron_job_name: str,
            additional_context: str,
            attribution: str | None,
        ) -> Any:
            """Update a cron job by appending additional context."""
            ...

        def delete_cron_job(self, cron_job_name: str, attribution: str | None) -> Any:
            """Delete a cron job."""
            ...

        def open_data_request_ticket(self, title: str, body: str, attribution: str | None) -> Any:
            """Open a data request ticket in the GitHub repository."""
            ...

        def search_context(self, query: str) -> Any:
            """Search for context entries matching the query."""
            ...

        def search_datasets(self, query: str, full: bool) -> Any:
            """Search for dataset documentation matching the query."""
            ...

        def get_system_prompt(self) -> Any:
            """Get the system prompt for the current context."""
            ...

else:
    # At runtime, ContextEngineProtocol is just a type alias
    # This allows duck typing without protocol checking complications
    ContextEngineProtocol = Any
