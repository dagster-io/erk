"""Fake parallel task runner for testing.

FakeParallelTaskRunner is an in-memory implementation that returns pre-configured results
instantly without any threading or wall-clock delays. Construct instances directly
with keyword arguments specifying expected results.
"""

from collections.abc import Callable

from erk_shared.gateway.parallel.abc import ParallelTaskRunner


class FakeParallelTaskRunner(ParallelTaskRunner):
    """In-memory fake implementation of parallel task runner.

    Returns pre-configured results instantly without executing tasks.
    Tracks requested tasks for test assertions.

    Constructor Injection:
    ---------------------
    All results are provided via constructor (results parameter).
    Tasks are NOT actually executed - the fake returns configured results immediately.

    Mutation Tracking:
    -----------------
    This fake tracks requested tasks via read-only property:
    - requested_tasks: List of task names passed to run_parallel()

    Examples:
    ---------
        # Configure results for specific tasks
        runner = FakeParallelTaskRunner(results={
            "task1": "result1",
            "task2": None,  # Simulate timeout
            "task3": {"data": "value"}
        })

        # Tasks are not executed, pre-configured results returned
        results = runner.run_parallel(
            tasks={
                "task1": lambda: expensive_operation(),  # NOT called
                "task2": lambda: slow_operation(),       # NOT called
                "task3": lambda: compute_something(),    # NOT called
            },
            timeout_per_task=2.0
        )

        # Verify results
        assert results == {"task1": "result1", "task2": None, "task3": {"data": "value"}}

        # Verify which tasks were requested
        assert runner.requested_tasks == ["task1", "task2", "task3"]
    """

    def __init__(self, *, results: dict[str, object | None] | None = None) -> None:
        """Create FakeParallelTaskRunner with pre-configured results.

        Args:
            results: Mapping of task name -> result (None for timeouts)
                    If a task is not in results, it returns None by default.
        """
        self._results = results or {}
        self._requested_tasks: list[str] = []

    @property
    def requested_tasks(self) -> list[str]:
        """Get list of task names that were requested via run_parallel.

        Returns:
            List of task names in order they were requested
        """
        return list(self._requested_tasks)

    def run_parallel(
        self, tasks: dict[str, Callable[[], object]], timeout_per_task: float
    ) -> dict[str, object | None]:
        """Return pre-configured results instantly without executing tasks.

        Tasks are NOT executed. The callables are ignored and pre-configured
        results are returned immediately.

        Args:
            tasks: Dictionary mapping task names to callables (NOT executed)
            timeout_per_task: Timeout value (ignored in fake)

        Returns:
            Pre-configured results dictionary (or None for missing tasks)
        """
        # Track which tasks were requested
        self._requested_tasks.extend(tasks.keys())

        # Return pre-configured results (None for any task not configured)
        return {task_name: self._results.get(task_name) for task_name in tasks}
