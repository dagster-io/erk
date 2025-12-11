"""Base class for background tasks."""

import asyncio
import logging
import random
from abc import ABC, abstractmethod

from ddtrace.trace import Span, tracer

from csbot.utils.time import AsyncSleep, system_async_sleep


class BackgroundTask(ABC):
    """Base class for background tasks with centralized loop management."""

    def __init__(self, execute_on_init: bool = False, async_sleep: AsyncSleep = system_async_sleep):
        self._task: asyncio.Task | None = None
        self._execute_on_init = execute_on_init
        self.async_sleep = async_sleep

    def _jitter_seconds(self, sleep_seconds: float, jitter_seconds: int) -> float:
        return sleep_seconds + random.randint(0, jitter_seconds)

    @property
    def logger(self) -> logging.Logger:
        raise NotImplementedError("logger is not implemented")

    @abstractmethod
    async def execute_tick(self) -> None:
        """Execute one iteration of the task."""
        ...

    @abstractmethod
    def get_sleep_seconds(self) -> float:
        """Return seconds to sleep after successful execution."""
        ...

    def get_error_sleep_seconds(self) -> float:
        """Return seconds to sleep after an error. Override to customize."""
        return 60

    async def on_error(self, error: Exception) -> None:
        """Hook called when an error occurs. Override to customize."""
        self.logger.error(f"Error in {self.__class__.__name__}: {error}", exc_info=True)

    async def start(self) -> None:
        """Start the background task."""
        if self._task and not self._task.done():
            self.logger.warning(f"{self.__class__.__name__} already running")
            return

        self._task = asyncio.create_task(self._run_loop())
        self.logger.info(f"Started {self.__class__.__name__}")

    async def stop(self) -> None:
        """Stop the background task."""
        if not self._task:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self.logger.info(f"Stopped {self.__class__.__name__}")

    def _set_bot_instance_tags(self, span: Span):
        # prevent circular import
        from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask

        if not isinstance(self, BotInstanceBackgroundTask):
            return

        config = self.bot.bot_config
        span.set_tags(
            {
                "channel": config.channel_name,
                "team_id": config.team_id,
                "organization": config.organization_name,
            }
        )

    async def _run_loop(self) -> None:
        """Centralized loop management."""
        while True:
            try:
                if self._execute_on_init:
                    with tracer.trace(f"{self.__class__.__name__}.tick") as span:
                        self._set_bot_instance_tags(span)
                        span.set_tag("init", True)
                        await self.execute_tick()
                    self._execute_on_init = False
                sleep_seconds = self.get_sleep_seconds()
                await self.async_sleep(sleep_seconds)
                with tracer.trace(f"{self.__class__.__name__}.tick") as span:
                    self._set_bot_instance_tags(span)
                    await self.execute_tick()
            except Exception as e:
                await self.on_error(e)
                error_sleep = self.get_error_sleep_seconds()
                await self.async_sleep(error_sleep)
