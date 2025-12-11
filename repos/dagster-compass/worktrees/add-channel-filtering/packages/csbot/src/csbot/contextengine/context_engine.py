import asyncio
import json
import re
from datetime import datetime
from sqlite3 import NotSupportedError
from typing import TYPE_CHECKING, Any

from csbot.agents.completion_utils import categorize_context, generate_context_summary
from csbot.agents.protocol import AsyncAgent
from csbot.contextengine.contextstore_protocol import (
    NO_CHANNEL_SENTINEL,
    AddContextResult,
    ContextIdentifier,
    ContextStore,
    DatasetSearchResult,
    NamedContext,
    ProvidedContext,
    SearchContextResult,
    UserCronJob,
)
from csbot.contextengine.dataset_documentation import DatasetSearcher
from csbot.contextengine.fts_index import FTSIndex
from csbot.contextengine.protocol import ContextStoreManager
from csbot.local_context_store.github.api import (
    create_data_request_issue,
)
from csbot.slackbot.usercron import (
    DeleteUserCronJobResult,
    UpdateUserCronJobResult,
    UserCronStorage,
)
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.local_context_store.github.config import GithubConfig


class ContextEngine:
    """Unified context engine for all context store operations.

    Implements ContextEngineProtocol to ensure type safety and prevent
    accidental mutations from leaking into read-only implementations.
    """

    def __init__(
        self,
        context_store_manager: ContextStoreManager,
        agent: "AsyncAgent",
        normalized_channel_name: str | None,
        available_connection_names: set[str],
        github_config: "GithubConfig | None",
    ) -> None:
        if (
            normalized_channel_name
            and normalize_channel_name(normalized_channel_name) != normalized_channel_name
        ):
            raise ValueError(f"Channel name was not normalized: {normalized_channel_name}")
        self._agent = agent
        self._context_store_manager = context_store_manager
        self._normalized_channel_name = normalized_channel_name
        self._available_connection_names = available_connection_names
        self._github_config = github_config

        # Initialize cron job management
        self._cron_manager = UserCronStorage(context_store_manager, normalized_channel_name)

    # Protocol-required attributes (as properties for consistency)

    @property
    def normalized_channel_name(self) -> str | None:
        """Access to normalized channel name."""
        return self._normalized_channel_name

    @property
    def available_connection_names(self) -> set[str]:
        """Access to available connection names."""
        return self._available_connection_names

    @property
    def agent(self) -> AsyncAgent:
        """Access to AI agent."""
        return self._agent

    def supports_add_context(self) -> bool:
        """Check if this context engine supports adding context.

        Returns True for standard context engines, False for read-only variants.
        """
        return True

    def supports_cron_jobs(self) -> bool:
        """Check if this context engine supports cron jobs.

        Returns True for standard context engines, False for read-only variants.
        """
        return True

    def _open_data_request_ticket_wrapper(
        self, title: str, body: str, attribution: str | None
    ) -> str:
        """Wrapper for opening data request tickets."""
        if self._github_config is None:
            raise NotSupportedError
        return create_data_request_issue(self._github_config, title, body, attribution)

    async def get_cron_jobs(self) -> dict[str, UserCronJob]:
        """Get all cron jobs."""
        return await self._cron_manager.get_cron_jobs()

    async def add_cron_job(
        self,
        cron_job_name: str,
        cron_string: str,
        question: str,
        thread: str,
        attribution: str | None,
    ) -> Any:
        """Add a cron job."""
        return await self._cron_manager.add_cron_job(
            cron_job_name=cron_job_name,
            cron_string=cron_string,
            question=question,
            thread=thread,
            attribution=attribution,
        )

    async def update_cron_job(
        self,
        cron_job_name: str,
        additional_context: str,
        attribution: str | None,
    ) -> UpdateUserCronJobResult:
        """Update a cron job by appending additional context to the question."""
        return await self._cron_manager.update_cron_job(
            cron_job_name=cron_job_name,
            additional_context=additional_context,
            attribution=attribution,
        )

    async def delete_cron_job(
        self, cron_job_name: str, attribution: str | None
    ) -> DeleteUserCronJobResult:
        """Delete a cron job."""
        return await self._cron_manager.delete_cron_job(
            cron_job_name=cron_job_name,
            attribution=attribution,
        )

    async def open_data_request_ticket(self, title: str, body: str, attribution: str | None) -> str:
        """Open a data request ticket in the GitHub repository. Returns the URL of the ticket."""
        return await asyncio.to_thread(
            lambda title, body, attribution: self._open_data_request_ticket_wrapper(
                title, body, attribution
            ),
            title,
            body,
            attribution,
        )

    async def add_context(
        self,
        topic: str,
        incorrect_understanding: str,
        correct_understanding: str,
        attribution: str | None,
    ) -> AddContextResult:
        """
        Add context with AI-generated summary and keywords.

        Args:
            topic: Topic or subject area
            incorrect_understanding: Description of incorrect understanding
            correct_understanding: Description of correct understanding
            attribution: Optional attribution text for PR description

        Returns:
            AddContextResult with file paths and review URL
        """
        # Load project configuration
        # Generate summary and keywords using agent
        summary, keywords = await generate_context_summary(
            self.agent,
            topic=topic,
            incorrect_understanding=incorrect_understanding,
            correct_understanding=correct_understanding,
        )

        # Create context object
        context = ProvidedContext(
            topic=topic,
            incorrect_understanding=incorrect_understanding,
            correct_understanding=correct_understanding,
            search_keywords=keywords,
        )

        # Generate filename with timestamp and summary
        timestamp = datetime.now().strftime("%Y%m%d")
        # Sanitize summary for filename
        safe_summary = re.sub(r"[^\w\s-]", "", summary)
        safe_summary = re.sub(r"[-\s]+", "-", safe_summary).strip("-")
        context_name = f"{timestamp}_{safe_summary}"

        summary_for_title = summary
        summary += f"\n\n```\n{json.dumps(context.model_dump(), indent=2)}\n```"

        # Build PR body with optional attribution
        body = summary
        if attribution:
            body = f"{attribution}\n\n{body}"

        context_store = await self._context_store_manager.get_context_store()

        category = "uncategorized"
        available_categories = [context.name for context in context_store.general_context]
        if "uncategorized" not in available_categories:
            available_categories.append("uncategorized")
        category = await categorize_context(
            self.agent,
            summary=summary,
            available_categories=available_categories,
        )
        updated = context_store.model_copy(
            update={
                "general_context": [
                    *context_store.general_context,
                    NamedContext(
                        group=category,
                        name=context_name,
                        context=context,
                    ),
                ]
            }
        )

        mutation_token = await self._context_store_manager.mutate(
            f"CONTEXT: {summary_for_title}",
            body,
            False,
            before=context_store,
            after=updated,
        )

        return AddContextResult(
            context_review_url=mutation_token,
            context_summary=summary,
        )

    async def search_context(self, query: str) -> list[SearchContextResult]:
        """Search for context in the project."""
        # Check if project exists first
        results = await self._search_context_internal(query)

        # Convert to SearchContextResult to exclude search_keywords
        search_results = [
            SearchContextResult(
                topic=context.topic,
                incorrect_understanding=context.incorrect_understanding,
                correct_understanding=context.correct_understanding,
            )
            for _, context in results
        ]
        return search_results

    async def _search_context_internal(
        self,
        query: str,
    ) -> list[tuple[str, ProvidedContext]]:
        """
        Internal search context method using ContextStore data.

        Args:
            query: Search query string

        Returns:
            List of tuples containing (file_path, ProvidedContext)
        """
        context_store = await self._context_store_manager.get_context_store()
        searcher = ContextSearcher(
            context_store=context_store, channel_name=self.normalized_channel_name
        )
        return await asyncio.to_thread(searcher.search, query)

    async def search_datasets(self, query: str, full: bool) -> list[DatasetSearchResult]:
        """
        Search dataset documentation using ContextStore data.

        Args:
            query: Search query string (use "*" to return all datasets when full=False)
            full: Whether to return full documentation or just table names

        Returns:
            List of DatasetSearchResult objects
        """
        if query == "*" and full:
            raise ValueError("Cannot search all datasets when full=True")

        context_store = await self._context_store_manager.get_context_store()
        searcher = DatasetSearcher(
            context_store=context_store,
            full=full,
            connections=list(self.available_connection_names),
        )

        if query == "*":
            # Return all datasets for wildcard query
            rv = []
            for dataset, _ in context_store.datasets:
                if dataset.connection not in self.available_connection_names:
                    continue
                object_id = None
                if context_store.project.version == 2:
                    object_id = f"{dataset.connection}/{dataset.table_name}"
                rv.append(
                    DatasetSearchResult(
                        connection=dataset.connection,
                        table=dataset.table_name,
                        docs_markdown=None,
                        object_id=object_id,
                    )
                )
            return rv

        return await asyncio.to_thread(searcher.search, query)

    async def get_system_prompt(self) -> str | None:
        """Get the system prompt for the project."""
        context_store = await self._context_store_manager.get_context_store()

        system_prompts = []
        if context_store.system_prompt:
            system_prompts.append(context_store.system_prompt)

        if self.normalized_channel_name and self.normalized_channel_name in context_store.channels:
            channel_context = context_store.channels[self.normalized_channel_name]
            if channel_context.system_prompt:
                system_prompts.append(channel_context.system_prompt)

        if system_prompts:
            return "\n\n".join(system_prompts)
        return None


class ContextSearcher:
    def __init__(
        self,
        context_store: ContextStore,
        channel_name: str | None,
    ) -> None:
        self.channel_name = channel_name
        self.context_store = context_store
        self.fts = None

    def build_index(self) -> FTSIndex:
        """Build the search index from context files."""
        if self.fts:
            return self.fts

        # Collect all documents from the context directory
        docs = []
        for named_context in self.context_store.general_context:
            context = named_context.context
            content = (
                f"{context.topic} {context.incorrect_understanding} "
                f"{context.correct_understanding} {context.search_keywords}"
            )
            docs.append(
                (f"{NO_CHANNEL_SENTINEL}/{named_context.group}/{named_context.name}", content)
            )

        for channel_name, channel_context in self.context_store.channels.items():
            for named_context in channel_context.context:
                context = named_context.context
                content = (
                    f"{context.topic} {context.incorrect_understanding} "
                    f"{context.correct_understanding} {context.search_keywords}"
                )
                docs.append((f"{channel_name}/{named_context.group}/{named_context.name}", content))

        # Create index with all documents at once
        self.fts = FTSIndex(docs)
        return self.fts

    def search(self, query: str) -> list[tuple[str, ProvidedContext]]:
        """
        Search the context index.

        Args:
            query: Search query string

        Returns:
            List of ProvidedContext objects
        """
        fts = self.build_index()

        # Perform search
        results = []
        for doc_id in fts.search(query, limit=10):
            context_id = ContextIdentifier.from_string(doc_id)
            results.append((doc_id, self.context_store.get_context(context_id)))

        return results
