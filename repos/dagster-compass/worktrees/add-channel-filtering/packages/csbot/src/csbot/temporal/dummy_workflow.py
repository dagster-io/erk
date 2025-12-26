"""Dummy workflow for temporal worker initialization.

This module is intentionally minimal to avoid sandbox import issues.
It provides a basic workflow that allows the Temporal worker to start.
"""

from temporalio import workflow


@workflow.defn
class DummyWorkflow:
    """Dummy workflow to satisfy Temporal worker requirements.

    This allows the worker to start without errors. Real workflows
    should be added to the worker as they are developed.
    """

    @workflow.run
    async def run(self) -> str:
        """Execute dummy workflow."""
        return "dummy workflow completed"
