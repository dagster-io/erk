"""Background task manager for CompassChannelBotInstance."""

import logging
from collections.abc import Sequence

from .background_task import BackgroundTask


class BackgroundTaskManager:
    """Manages all background tasks for a CompassChannelBotInstance."""

    def __init__(self, tasks: Sequence[BackgroundTask], logger: logging.Logger):
        self.tasks = tasks
        self.logger = logger

    async def start_all(self):
        """Start all background tasks."""
        for task in self.tasks:
            await task.start()
        self.logger.info("Started all background tasks")

    async def stop_all(self):
        """Stop all background tasks."""
        # Stop tasks in reverse order to handle dependencies gracefully
        for task in reversed(self.tasks):
            try:
                await task.stop()
            except Exception as e:
                self.logger.error(f"Error stopping task {task.__class__.__name__}: {e}")
        self.logger.info("Stopped all background tasks")

    def get_task(self, task_type: type[BackgroundTask]) -> BackgroundTask | None:
        """Get a specific task instance by type."""
        for task in self.tasks:
            if isinstance(task, task_type):
                return task
        return None
