"""Factory for building ContextStore instances in tests.

Provides a fluent builder interface for constructing ContextStore objects with
test data. The builder allows chaining methods to incrementally build up a
complete ContextStore with projects, datasets, contexts, cronjobs, and channels.

Example usage:
    store = (
        context_store_builder()
        .with_project("test/project")
        .with_system_prompt("Global system prompt")
        .add_dataset("postgres", "users")
        .with_markdown("# Users table\\nContains user data")
        .with_schema_hash("abc123")
        .add_general_context("onboarding", "user_flow")
        .with_topic("User onboarding process")
        .with_incorrect("Users go through checkout")
        .with_correct("Users go through registration flow")
        .with_keywords("registration signup onboarding")
        .add_general_cronjob("daily_report")
        .with_cron("0 9 * * *")
        .with_question("What were yesterday's signups?")
        .with_thread("daily-reports")
        .new_channel("sales")
        .with_channel_system_prompt("Focus on sales metrics")
        .add_channel_context("deals", "pipeline_stages")
        .with_topic("Sales pipeline stages")
        .with_incorrect("We have 3 stages")
        .with_correct("We have 5 stages: Lead, Qualified, Proposal, Negotiation, Closed")
        .with_keywords("sales pipeline stages deal")
        .add_channel_cronjob("weekly_deals")
        .with_cron("0 10 * * 1")
        .with_question("What deals closed last week?")
        .with_thread("weekly-sales")
        .build()
    )
"""

from typing import Self

from pydantic import ValidationError

from csbot.contextengine.contextstore_protocol import (
    ChannelContext,
    ContextStore,
    ContextStoreProject,
    Dataset,
    DatasetDocumentation,
    NamedContext,
    ProvidedContext,
    TableFrontmatter,
    UserCronJob,
)


class ContextStoreBuilder:
    """Fluent builder for constructing ContextStore instances in tests.

    The builder maintains state for the current item being built (dataset, context, cronjob)
    and allows chaining methods to configure that item before moving to the next.

    Usage pattern:
        1. Start with context_store_builder()
        2. Configure project: .with_project("name")
        3. Add datasets: .add_dataset(connection, table).with_markdown(...).with_schema_hash(...)
        4. Add contexts: .add_general_context(group, name).with_topic(...).with_correct(...)
        5. Add cronjobs: .add_general_cronjob(name).with_cron(...).with_question(...)
        6. Add channels: .new_channel(name).add_channel_context(...).add_channel_cronjob(...)
        7. Build: .build()
    """

    def __init__(self):
        self._project_name = "test/project"
        self._project_version = 1
        self._project_teams = {}
        self._datasets = []
        self._general_context = []
        self._general_cronjobs = {}
        self._channels = {}
        self._system_prompt = None

        # Current item being built
        self._current_dataset = None
        self._current_dataset_markdown = ""
        self._current_dataset_frontmatter = None

        self._current_context_group = None
        self._current_context_name = None
        self._current_context_topic = None
        self._current_context_incorrect = None
        self._current_context_correct = None
        self._current_context_keywords = None

        self._current_cronjob_name = None
        self._current_cronjob_cron = None
        self._current_cronjob_question = None
        self._current_cronjob_thread = None

        # Channel building state
        self._current_channel_name = None
        self._current_channel_contexts = []
        self._current_channel_cronjobs = {}
        self._current_channel_system_prompt = None

    # Project configuration

    def with_project(self, project_name: str, version: int = 1) -> Self:
        """Set the project name and version.

        Args:
            project_name: Project name in format "org/repo"
            version: Context store version (1=legacy, 2=manifest)

        Returns:
            Self for chaining
        """
        self._project_name = project_name
        self._project_version = version
        return self

    def with_project_teams(self, teams: dict[str, list[str]]) -> Self:
        """Set project teams configuration.

        Args:
            teams: Dictionary mapping team names to member lists

        Returns:
            Self for chaining
        """
        self._project_teams = teams
        return self

    def with_system_prompt(self, prompt: str) -> Self:
        """Set the general system prompt.

        Args:
            prompt: System prompt content

        Returns:
            Self for chaining
        """
        self._system_prompt = prompt
        return self

    # Dataset building

    def add_dataset(self, connection: str | Dataset, table_name: str | None = None) -> Self:
        self._flush_current_dataset()

        if isinstance(connection, Dataset):
            assert table_name is None
            table_name = connection.table_name
            connection = connection.connection
        else:
            assert table_name is not None
        self._current_dataset = Dataset(connection=connection, table_name=table_name)
        self._current_dataset_markdown = ""
        self._current_dataset_frontmatter = None
        return self

    def with_markdown(self, markdown: str) -> Self:
        """Set markdown content for the current dataset.

        Args:
            markdown: Full markdown documentation content (may include frontmatter)

        Returns:
            Self for chaining
        """
        if not self._current_dataset:
            raise ValueError("Call add_dataset() before with_markdown()")

        # Parse frontmatter if present
        from csbot.contextengine.loader import _parse_frontmatter_and_summary

        try:
            frontmatter, summary = _parse_frontmatter_and_summary(markdown)
        except ValidationError:
            summary = markdown
            frontmatter = None
        self._current_dataset_markdown = summary
        if frontmatter:
            self._current_dataset_frontmatter = frontmatter
        return self

    def with_schema_hash(self, schema_hash: str, columns: list[str] | None = None) -> Self:
        """Set schema hash and optional columns for the current dataset.

        Args:
            schema_hash: Schema hash string
            columns: Optional list of column names

        Returns:
            Self for chaining
        """
        if not self._current_dataset:
            raise ValueError("Call add_dataset() before with_schema_hash()")
        self._current_dataset_frontmatter = TableFrontmatter(
            schema_hash=schema_hash, columns=columns
        )
        return self

    def _flush_current_dataset(self) -> None:
        """Save the current dataset being built to the datasets list."""
        if self._current_dataset:
            documentation = DatasetDocumentation(
                frontmatter=self._current_dataset_frontmatter,
                summary=self._current_dataset_markdown,
            )
            self._datasets.append((self._current_dataset, documentation))
            self._current_dataset = None
            self._current_dataset_markdown = ""
            self._current_dataset_frontmatter = None

    # General context building

    def add_general_context(self, group: str, name: str) -> Self:
        """Start building a new general context entry.

        Args:
            group: Context group/category
            name: Context name

        Returns:
            Self for chaining (use with_topic/with_incorrect/with_correct/with_keywords)
        """
        self._flush_current_general_context()
        self._current_context_group = group
        self._current_context_name = name
        self._current_context_topic = None
        self._current_context_incorrect = None
        self._current_context_correct = None
        self._current_context_keywords = None
        return self

    def with_topic(self, topic: str) -> Self:
        """Set topic for current context.

        Args:
            topic: Context topic

        Returns:
            Self for chaining
        """
        if not self._current_context_group:
            raise ValueError(
                "Call add_general_context() or add_channel_context() before with_topic()"
            )
        self._current_context_topic = topic
        return self

    def with_incorrect(self, incorrect: str) -> Self:
        """Set incorrect understanding for current context.

        Args:
            incorrect: Incorrect understanding text

        Returns:
            Self for chaining
        """
        if not self._current_context_group:
            raise ValueError(
                "Call add_general_context() or add_channel_context() before with_incorrect()"
            )
        self._current_context_incorrect = incorrect
        return self

    def with_correct(self, correct: str) -> Self:
        """Set correct understanding for current context.

        Args:
            correct: Correct understanding text

        Returns:
            Self for chaining
        """
        if not self._current_context_group:
            raise ValueError(
                "Call add_general_context() or add_channel_context() before with_correct()"
            )
        self._current_context_correct = correct
        return self

    def with_keywords(self, keywords: str) -> Self:
        """Set search keywords for current context.

        Args:
            keywords: Space-separated search keywords

        Returns:
            Self for chaining
        """
        if not self._current_context_group:
            raise ValueError(
                "Call add_general_context() or add_channel_context() before with_keywords()"
            )
        self._current_context_keywords = keywords
        return self

    def _flush_current_general_context(self) -> None:
        """Save the current general context being built."""
        if self._current_context_group and not self._current_channel_name:
            if not all(
                [
                    self._current_context_topic,
                    self._current_context_incorrect,
                    self._current_context_correct,
                    self._current_context_keywords,
                ]
            ):
                raise ValueError(
                    "Context must have topic, incorrect, correct, and keywords. "
                    f"Missing for {self._current_context_group}/{self._current_context_name}"
                )

            assert self._current_context_topic is not None
            assert self._current_context_incorrect is not None
            assert self._current_context_correct is not None
            assert self._current_context_keywords is not None
            assert self._current_context_name is not None

            provided_context = ProvidedContext(
                topic=self._current_context_topic,
                incorrect_understanding=self._current_context_incorrect,
                correct_understanding=self._current_context_correct,
                search_keywords=self._current_context_keywords,
            )
            named_context = NamedContext(
                group=self._current_context_group,
                name=self._current_context_name,
                context=provided_context,
            )
            self._general_context.append(named_context)
            self._current_context_group = None
            self._current_context_name = None

    # General cronjob building

    def add_general_cronjob(
        self,
        name: str,
        cron: str | None = None,
        question: str | None = None,
        thread: str | None = None,
    ) -> Self:
        """Start building a new general cronjob.

        Args:
            name: Cronjob name

        Returns:
            Self for chaining (use with_cron/with_question/with_thread)
        """
        self._flush_current_general_cronjob()
        self._current_cronjob_name = name
        self._current_cronjob_cron = cron
        self._current_cronjob_question = question
        self._current_cronjob_thread = thread
        return self

    def with_cron(self, cron: str) -> Self:
        """Set cron schedule for current cronjob.

        Args:
            cron: Cron expression

        Returns:
            Self for chaining
        """
        if not self._current_cronjob_name:
            raise ValueError(
                "Call add_general_cronjob() or add_channel_cronjob() before with_cron()"
            )
        self._current_cronjob_cron = cron
        return self

    def with_question(self, question: str) -> Self:
        """Set question for current cronjob.

        Args:
            question: Question to run on schedule

        Returns:
            Self for chaining
        """
        if not self._current_cronjob_name:
            raise ValueError(
                "Call add_general_cronjob() or add_channel_cronjob() before with_question()"
            )
        self._current_cronjob_question = question
        return self

    def with_thread(self, thread: str) -> Self:
        """Set thread for current cronjob.

        Args:
            thread: Thread/channel for posting results

        Returns:
            Self for chaining
        """
        if not self._current_cronjob_name:
            raise ValueError(
                "Call add_general_cronjob() or add_channel_cronjob() before with_thread()"
            )
        self._current_cronjob_thread = thread
        return self

    def _flush_current_general_cronjob(self) -> None:
        """Save the current general cronjob being built."""
        if self._current_cronjob_name and not self._current_channel_name:
            if not all(
                [
                    self._current_cronjob_cron,
                    self._current_cronjob_question,
                    self._current_cronjob_thread,
                ]
            ):
                raise ValueError(
                    f"Cronjob must have cron, question, and thread. Missing for {self._current_cronjob_name}"
                )

            assert self._current_cronjob_cron is not None
            assert self._current_cronjob_question is not None
            assert self._current_cronjob_thread is not None

            cronjob = UserCronJob(
                cron=self._current_cronjob_cron,
                question=self._current_cronjob_question,
                thread=self._current_cronjob_thread,
            )
            self._general_cronjobs[self._current_cronjob_name] = cronjob
            self._current_cronjob_name = None

    # Channel building

    def new_channel(self, channel_name: str) -> Self:
        """Start building a new channel.

        This flushes any pending general items and starts a new channel context.
        Use add_channel_context() and add_channel_cronjob() to add items to this channel.

        Args:
            channel_name: Channel name

        Returns:
            Self for chaining
        """
        self._flush_all_general()
        self._flush_current_channel()
        self._current_channel_name = channel_name
        self._current_channel_contexts = []
        self._current_channel_cronjobs = {}
        self._current_channel_system_prompt = None
        return self

    def with_channel_system_prompt(self, prompt: str) -> Self:
        """Set system prompt for the current channel.

        Args:
            prompt: Channel-specific system prompt

        Returns:
            Self for chaining
        """
        if not self._current_channel_name:
            raise ValueError("Call new_channel() before with_channel_system_prompt()")
        self._current_channel_system_prompt = prompt
        return self

    def add_channel_context(self, group: str, name: str) -> Self:
        """Start building a new context entry for the current channel.

        Args:
            group: Context group/category
            name: Context name

        Returns:
            Self for chaining (use with_topic/with_incorrect/with_correct/with_keywords)
        """
        if not self._current_channel_name:
            raise ValueError("Call new_channel() before add_channel_context()")
        self._flush_current_channel_context()
        self._current_context_group = group
        self._current_context_name = name
        self._current_context_topic = None
        self._current_context_incorrect = None
        self._current_context_correct = None
        self._current_context_keywords = None
        return self

    def add_channel_cronjob(
        self,
        name: str,
        cron: str | None = None,
        question: str | None = None,
        thread: str | None = None,
    ) -> Self:
        """Start building a new cronjob for the current channel.

        Args:
            name: Cronjob name

        Returns:
            Self for chaining (use with_cron/with_question/with_thread)
        """
        if not self._current_channel_name:
            raise ValueError("Call new_channel() before add_channel_cronjob()")
        self._flush_current_channel_cronjob()
        self._current_cronjob_name = name
        self._current_cronjob_cron = cron
        self._current_cronjob_question = question
        self._current_cronjob_thread = thread
        return self

    def _flush_current_channel_context(self) -> None:
        """Save the current channel context being built."""
        if self._current_context_group and self._current_channel_name:
            if not all(
                [
                    self._current_context_topic,
                    self._current_context_incorrect,
                    self._current_context_correct,
                    self._current_context_keywords,
                ]
            ):
                raise ValueError(
                    "Context must have topic, incorrect, correct, and keywords. "
                    f"Missing for {self._current_context_group}/{self._current_context_name}"
                )

            assert self._current_context_topic is not None
            assert self._current_context_incorrect is not None
            assert self._current_context_correct is not None
            assert self._current_context_keywords is not None
            assert self._current_context_name is not None

            provided_context = ProvidedContext(
                topic=self._current_context_topic,
                incorrect_understanding=self._current_context_incorrect,
                correct_understanding=self._current_context_correct,
                search_keywords=self._current_context_keywords,
            )
            named_context = NamedContext(
                group=self._current_context_group,
                name=self._current_context_name,
                context=provided_context,
            )
            self._current_channel_contexts.append(named_context)
            self._current_context_group = None
            self._current_context_name = None

    def _flush_current_channel_cronjob(self) -> None:
        """Save the current channel cronjob being built."""
        if self._current_cronjob_name and self._current_channel_name:
            if not all(
                [
                    self._current_cronjob_cron,
                    self._current_cronjob_question,
                    self._current_cronjob_thread,
                ]
            ):
                raise ValueError(
                    f"Cronjob must have cron, question, and thread. Missing for {self._current_cronjob_name}"
                )

            assert self._current_cronjob_cron is not None
            assert self._current_cronjob_question is not None
            assert self._current_cronjob_thread is not None

            cronjob = UserCronJob(
                cron=self._current_cronjob_cron,
                question=self._current_cronjob_question,
                thread=self._current_cronjob_thread,
            )
            self._current_channel_cronjobs[self._current_cronjob_name] = cronjob
            self._current_cronjob_name = None

    def _flush_current_channel(self) -> None:
        """Save the current channel being built."""
        if self._current_channel_name:
            self._flush_current_channel_context()
            self._flush_current_channel_cronjob()

            channel_context = ChannelContext(
                cron_jobs=self._current_channel_cronjobs,
                context=self._current_channel_contexts,
                system_prompt=self._current_channel_system_prompt,
            )
            self._channels[self._current_channel_name] = channel_context
            self._current_channel_name = None
            self._current_channel_contexts = []
            self._current_channel_cronjobs = {}
            self._current_channel_system_prompt = None

    def _flush_all_general(self) -> None:
        """Flush all pending general items."""
        self._flush_current_dataset()
        self._flush_current_general_context()
        self._flush_current_general_cronjob()

    def build(self) -> ContextStore:
        """Build the final ContextStore instance.

        Returns:
            Immutable ContextStore with all configured data
        """
        # Flush any pending items
        self._flush_all_general()
        self._flush_current_channel()

        project = ContextStoreProject(
            project_name=self._project_name,
            version=self._project_version,
            teams=self._project_teams,
        )

        return ContextStore(
            project=project,
            datasets=self._datasets,
            general_context=self._general_context,
            general_cronjobs=self._general_cronjobs,
            channels=self._channels,
            system_prompt=self._system_prompt,
        )


def context_store_builder() -> ContextStoreBuilder:
    """Create a new ContextStoreBuilder instance.

    Returns:
        Fresh ContextStoreBuilder ready for configuration

    Example:
        store = (
            context_store_builder()
            .with_project("my-org/my-project")
            .add_dataset("postgres", "users")
            .with_markdown("# Users\\nUser data")
            .with_schema_hash("abc123")
            .build()
        )
    """
    return ContextStoreBuilder()
