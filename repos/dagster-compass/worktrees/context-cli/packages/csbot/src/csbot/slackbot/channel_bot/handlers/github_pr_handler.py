"""GitHub pull request handler for dataset updates and monitoring."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import structlog

from csbot.contextengine.contextstore_protocol import ContextStore
from csbot.contextengine.protocol import ContextStoreManager
from csbot.ctx_admin.dataset_documentation import update_dataset

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent
    from csbot.contextengine.contextstore_protocol import Dataset
    from csbot.csbot_client.csbot_profile import ProjectProfile
    from csbot.ctx_admin.dataset_documentation import TableSchemaAnalysis


class GitHubPRHandler:
    """Handles GitHub pull request operations for dataset updates."""

    def __init__(self, context_store_manager: ContextStoreManager):
        self._context_store_manager = context_store_manager

    async def create_dataset_schema_pr(
        self,
        dataset: "Dataset",
        table_schema_analysis: "TableSchemaAnalysis",
        profile: "ProjectProfile",
        agent: "AsyncAgent",
    ) -> str:
        """Create a pull request for a single dataset schema update.

        Args:
            dataset: Dataset to update
            table_schema_analysis: Schema analysis results
            profile: Bot profile with connection details
            agent: AI agent for generating documentation
            logger: Logger instance

        Returns:
            URL of the created pull request
        """

        before = await self._context_store_manager.get_context_store()

        def run_sync_operations():
            child_logger = structlog.get_logger()
            with ThreadPoolExecutor(max_workers=4) as executor:
                return update_dataset(
                    logger=child_logger,
                    context_store=before,
                    profile=profile,
                    dataset=dataset,
                    table_schema_analysis=table_schema_analysis,
                    agent=agent,
                    column_analysis_threadpool=executor,
                )

        after = await asyncio.to_thread(run_sync_operations)

        mutation_token = await self._context_store_manager.mutate(
            f"DATASET MONITORING: Update {dataset.table_name} schema",
            (
                f"Automated schema update for dataset `{dataset.table_name}` from "
                f"connection `{dataset.connection}` detected by dataset monitoring "
                f"system.\n\n"
                f"Schema hash changed to: `{table_schema_analysis.schema_hash}`"
            ),
            False,
            before=before,
            after=after,
        )

        return mutation_token

    async def create_weekly_refresh_pr(
        self,
        datasets: list["Dataset"],
        profile: "ProjectProfile",
        agent: "AsyncAgent",
        logger: logging.Logger,
    ) -> str:
        """Create a pull request for weekly refresh of all datasets.

        Args:
            datasets: List of datasets to refresh
            profile: Bot profile with connection details
            agent: AI agent for generating documentation
            logger: Logger instance

        Returns:
            URL of the created pull request
        """

        before = await self._context_store_manager.get_context_store()

        def run_sync_operations(context_store: ContextStore):
            for dataset in datasets:
                try:
                    child_logger = structlog.get_logger()
                    child_logger.info(f"Refreshing {dataset.table_name}")

                    # Analyze schema
                    from csbot.ctx_admin.dataset_documentation import analyze_table_schema

                    table_schema_analysis = analyze_table_schema(child_logger, profile, dataset)

                    # Update dataset
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        context_store = update_dataset(
                            logger=child_logger,
                            context_store=context_store,
                            profile=profile,
                            dataset=dataset,
                            table_schema_analysis=table_schema_analysis,
                            agent=agent,
                            column_analysis_threadpool=executor,
                        )

                except Exception as e:
                    logger.error(
                        f"Error refreshing dataset {dataset.table_name}: {e}", exc_info=True
                    )
                    # Continue with other datasets
                    continue

            return context_store

        after = await asyncio.to_thread(run_sync_operations, before)

        mutation_token = await self._context_store_manager.mutate(
            "DATASET MONITORING: Weekly refresh of all datasets",
            (
                f"Weekly automated refresh of all {len(datasets)} datasets.\n\n"
                "This ensures dataset documentation stays current and includes any "
                "data quality changes even when schemas haven't changed."
            ),
            False,
            before=before,
            after=after,
        )

        logger.info(f"Created weekly refresh PR: {mutation_token}")
        return mutation_token
