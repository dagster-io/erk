"""Dataset monitoring handler for schema changes and documentation updates."""

import asyncio
import logging
from typing import TYPE_CHECKING

from ddtrace.trace import tracer

from csbot.agents.protocol import AsyncAgent
from csbot.contextengine.contextstore_protocol import ContextStoreProject, Dataset, TableFrontmatter
from csbot.csbot_client.csbot_profile import ProjectProfile
from csbot.ctx_admin.dataset_documentation import (
    TableSchemaAnalysis,
    analyze_table_schema,
)
from csbot.slackbot.storage.interface import SlackbotInstanceStorage
from csbot.utils.tracing import try_set_tag

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.handlers.github_pr_handler import GitHubPRHandler


class DatasetMonitor:
    """Handles dataset discovery, schema monitoring, and documentation updates."""

    def __init__(
        self,
        logger: logging.Logger | logging.LoggerAdapter,
        profile: ProjectProfile,
        kv_store: SlackbotInstanceStorage,
        github_pr_handler: "GitHubPRHandler",
        agent: AsyncAgent,
    ):
        self.logger = logger
        self.profile = profile
        self.kv_store = kv_store
        self.github_pr_handler = github_pr_handler
        self.agent = agent

    @tracer.wrap()
    async def check_and_update_dataset_if_changed(
        self, dataset: Dataset, frontmatter: TableFrontmatter | None, project: ContextStoreProject
    ) -> str | None:
        """Check if a dataset schema has changed and update it if so.

        Args:
            dataset: Dataset to check for changes
            frontmatter: Current frontmatter from the dataset documentation
            project: Project configuration

        Returns:
            The URL of the PR created to to modify the contextstore if created, otherwise None
            indicating there was no change
        """
        try_set_tag("connection", dataset.connection)
        try_set_tag("dataset", dataset.table_name)
        try:
            table_schema_analysis = await asyncio.to_thread(
                analyze_table_schema, self.logger, self.profile, dataset
            )

            # Check if schema has changed
            if frontmatter is None or frontmatter.schema_hash != table_schema_analysis.schema_hash:
                self.logger.info(f"Schema changed for {dataset.table_name}, creating PR")

                return await self._create_schema_update_pr(
                    dataset, table_schema_analysis, project, self.agent
                )

            else:
                self.logger.debug(f"No schema changes for {dataset.table_name}")
                return None

        except Exception as e:
            self.logger.warning(f"Error checking dataset {dataset.table_name}: {e}", exc_info=True)
            raise

    @tracer.wrap()
    async def _create_schema_update_pr(
        self,
        dataset: Dataset,
        table_schema_analysis: TableSchemaAnalysis,
        project: "ContextStoreProject",
        agent: "AsyncAgent",
    ) -> str | None:
        """Create a PR for a single dataset schema update.

        Args:
            dataset: Dataset that has schema changes
            table_schema_analysis: Analysis results for the dataset
            project: Project configuration
            agent: AI agent for generating documentation

        Returns:
            URL of PR created, if any
        """
        # Create a unique key for this PR to track duplicates
        pr_key = f"{dataset.connection}:{dataset.table_name}:{table_schema_analysis.schema_hash}"

        # Check if we've already sent a PR for this exact schema change
        existing_pr = await self.kv_store.get("schema_change_prs", pr_key)
        if existing_pr:
            self.logger.info(
                f"PR already sent for {dataset.table_name} with schema hash "
                f"{table_schema_analysis.schema_hash}, skipping"
            )
            return None

        # Create the PR
        pr_url = await self.github_pr_handler.create_dataset_schema_pr(
            dataset=dataset,
            table_schema_analysis=table_schema_analysis,
            profile=self.profile,
            agent=agent,
        )

        # Store that we've sent a PR for this schema change (expires in 30 days)
        if pr_url:
            await self.kv_store.set(
                "schema_change_prs", pr_key, pr_url, expiry_seconds=30 * 24 * 60 * 60
            )

        self.logger.info(f"Created PR for dataset {dataset.table_name}: {pr_url}")
        return pr_url
