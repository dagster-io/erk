"""Test-only utilities for background task testing.

This module provides utilities for deterministic background task testing without
polluting production code with test instrumentation.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

from csbot.slackbot.tasks.background_task import BackgroundTask


@dataclass
class ExecutionTracker:
    """Tracks background task executions for test synchronization.

    Test-only utility. Do not use in production code.

    Attributes:
        count: Number of times execute_tick() has been called
        executions: Timestamps of each execution (for debugging)
    """

    count: int = 0
    executions: list[float] = field(default_factory=list)


def wrap_task_with_tracker(task: BackgroundTask, tracker: ExecutionTracker) -> None:
    """Wrap a BackgroundTask's execute_tick() to track executions.

    This dynamically wraps the task's execute_tick() method to increment
    the tracker's count after each successful execution.

    Test-only utility. Do not use in production code.

    Args:
        task: The BackgroundTask instance to wrap
        tracker: The ExecutionTracker to update on each execution

    Example:
        tracker = ExecutionTracker()
        task = ConcreteBackgroundTask(bot, async_sleep=fake_time.async_sleep)
        wrap_task_with_tracker(task, tracker)

        await task.start()
        await wait_for_execution_count(tracker, target=3, timeout=2.0)
        await task.stop()

        assert tracker.count == 3
    """
    original_execute_tick = task.execute_tick

    async def tracked_execute_tick():
        await original_execute_tick()
        tracker.count += 1

    # Replace the method on the instance
    task.execute_tick = tracked_execute_tick  # type: ignore[method-assign]


async def wait_for_execution_count(
    tracker: ExecutionTracker,
    target: int,
    timeout: float = 2.0,
) -> None:
    """Wait for background task to complete exactly N executions.

    Polls the tracker's count until it reaches the target value, yielding
    control to the event loop on each check to allow background tasks to execute.

    Test-only utility. Do not use in production code.

    Args:
        tracker: The ExecutionTracker to monitor
        target: Number of executions to wait for
        timeout: Maximum time to wait in seconds (default: 2.0)

    Raises:
        asyncio.TimeoutError: If target not reached within timeout

    Example:
        tracker = ExecutionTracker()
        wrap_task_with_tracker(task, tracker)

        await task.start()
        await wait_for_execution_count(tracker, target=3, timeout=2.0)
        await task.stop()

        assert tracker.count == 3
    """
    async with asyncio.timeout(timeout):
        while tracker.count < target:
            await asyncio.sleep(0)  # Yield to event loop


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 2.0,
) -> None:
    """Wait for arbitrary condition to become true.

    Polls the condition function until it returns True, yielding control
    to the event loop on each check.

    Test-only utility. Do not use in production code.

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds (default: 2.0)

    Raises:
        asyncio.TimeoutError: If condition not met within timeout

    Example:
        await task.start()
        await wait_for_condition(lambda: task.some_state == "ready", timeout=2.0)
        await task.stop()
    """
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0)  # Yield to event loop
