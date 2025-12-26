"""Read-only context engine for prospector bot instances."""

from textwrap import dedent
from typing import TYPE_CHECKING, Any

from .context_engine import ContextEngine
from .contextstore_protocol import (
    AddContextResult,
    DatasetSearchResult,
    SearchContextResult,
)
from .protocol import ReadOnlyContextStoreManager

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent
    from csbot.contextengine.contextstore_protocol import (
        UserCronJob,
    )
    from csbot.slackbot.usercron import (
        DeleteUserCronJobResult,
        UpdateUserCronJobResult,
    )


class ProspectorReadOnlyContextEngine:
    """Context engine that blocks write operations for prospector bot instances.

    Delegates read operations to an internal ContextEngine instance, but blocks
    all operations that would create PRs or modify the context store repository.

    For prospector instances, extends system prompts with ICP (Ideal Candidate Profile) information.

    Uses composition rather than inheritance to ensure type safety - mutation methods
    must be explicitly implemented (as errors) rather than accidentally inherited.
    """

    def __init__(
        self,
        provider,
        agent: "AsyncAgent",
        normalized_channel_name: str | None,
        available_connection_names: set[str],
        icp: str,
        data_types: list[str] | None = None,
    ) -> None:
        read_only_manager = ReadOnlyContextStoreManager(provider)
        self._base_engine = ContextEngine(
            read_only_manager,
            agent,
            normalized_channel_name,
            available_connection_names,
            None,
        )
        self.icp = icp
        self.data_types = data_types or []

    # Protocol-required attributes (delegate to base engine)

    @property
    def normalized_channel_name(self):
        """Access to normalized channel name. Delegates to base engine."""
        return self._base_engine.normalized_channel_name

    @property
    def available_connection_names(self):
        """Access to available connection names. Delegates to base engine."""
        return self._base_engine.available_connection_names

    @property
    def agent(self):
        """Access to AI agent. Delegates to base engine."""
        return self._base_engine.agent

    # Feature flag methods (return False to indicate read-only)

    def supports_add_context(self) -> bool:
        """Read-only context stores do not support adding context."""
        return False

    def supports_cron_jobs(self) -> bool:
        """Read-only context stores do not support cron jobs."""
        return False

    # Read operations (delegate to base engine)

    async def search_context(self, query: str) -> list[SearchContextResult]:
        """Search context. Delegates to base engine."""
        return await self._base_engine.search_context(query)

    async def search_datasets(self, query: str, full: bool) -> list[DatasetSearchResult]:
        """Search datasets. Delegates to base engine."""
        return await self._base_engine.search_datasets(query, full)

    async def get_cron_jobs(self) -> dict[str, "UserCronJob"]:
        """Get cron jobs (returns empty dict for read-only). Delegates to base engine."""
        return await self._base_engine.get_cron_jobs()

    async def open_data_request_ticket(self, title: str, body: str, attribution: str | None) -> str:
        """Open data request ticket. Delegates to base engine."""
        return await self._base_engine.open_data_request_ticket(title, body, attribution)

    # System prompt with ICP injection (overrides base implementation)

    async def get_system_prompt(self) -> str | None:
        """Get the system prompt with ICP or data type context for prospector bot instances."""
        # Get base system prompt from context store
        context_store = await self._base_engine._context_store_manager.get_context_store()

        system_prompts = []
        if context_store.system_prompt:
            system_prompts.append(context_store.system_prompt)

        if self.normalized_channel_name and self.normalized_channel_name in context_store.channels:
            channel_context = context_store.channels[self.normalized_channel_name]
            if channel_context.system_prompt:
                system_prompts.append(channel_context.system_prompt)

        base_prompt = "\n\n".join(system_prompts) if system_prompts else None

        # Add ICP or data type context
        if self.icp:
            # Use ICP if provided
            context_prompt = dedent(f"""
                CANDIDATE PROFILE INFORMATION:
                You are helping find and analyze candidates who match this ideal candidate profile:

                {self.icp}

                Use this profile to guide your questions, analysis, and recommendations. When analyzing
                candidate data, always consider how well candidates align with these criteria.
            """).strip()
        elif self.data_types:
            # Use data types if ICP is empty
            data_type_list = ", ".join(self.data_types)
            context_prompt = dedent(f"""
                DATA TYPE FOCUS:
                You are helping with data analysis for: {data_type_list}

                Focus your questions and analysis on data relevant to these areas.
            """).strip()
        else:
            # No ICP or data types
            context_prompt = ""

        if context_prompt:
            if base_prompt:
                return f"{base_prompt}\n\n{context_prompt}"
            return context_prompt
        return base_prompt

    # Mutation methods (explicitly blocked with clear error messages)

    async def add_context(
        self,
        topic: str,
        incorrect_understanding: str,
        correct_understanding: str,
        attribution: str | None,
    ) -> AddContextResult:
        """Blocked for read-only context stores."""
        raise RuntimeError(
            "Attempted to add context to a prospector bot instance. "
            "This operation is not permitted for read-only context stores."
        )

    async def add_cron_job(
        self,
        cron_job_name: str,
        cron_string: str,
        question: str,
        thread: str,
        attribution: str | None,
    ) -> Any:
        """Blocked for read-only context stores."""
        raise RuntimeError(
            "Attempted to add cron job to a prospector bot instance. "
            "This operation is not permitted for read-only context stores."
        )

    async def update_cron_job(
        self,
        cron_job_name: str,
        additional_context: str,
        attribution: str | None,
    ) -> "UpdateUserCronJobResult":
        """Blocked for read-only context stores."""
        raise RuntimeError(
            "Attempted to update cron job in a prospector bot instance. "
            "This operation is not permitted for read-only context stores."
        )

    async def delete_cron_job(
        self, cron_job_name: str, attribution: str | None
    ) -> "DeleteUserCronJobResult":
        """Blocked for read-only context stores."""
        raise RuntimeError(
            "Attempted to delete cron job from a prospector bot instance. "
            "This operation is not permitted for read-only context stores."
        )
