"""Abstraction for parallel task execution with timeout handling.

This module provides an interface for executing tasks in parallel with timeout support,
enabling graceful degradation when tasks exceed their time limits. The abstraction allows
for both production execution using real threads and instant test execution using
pre-configured results.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable


class ParallelTaskRunner(ABC):
    """Abstract interface for parallel task execution with timeouts.

    Implementations must handle task execution with timeout semantics:
    - Tasks that complete successfully return their result
    - Tasks that timeout return None (graceful degradation)
    - Tasks that raise exceptions return None (error boundary)
    """

    @abstractmethod
    def run_parallel(
        self, tasks: dict[str, Callable[[], object]], timeout_per_task: float
    ) -> dict[str, object | None]:
        """Execute tasks in parallel with timeout handling.

        Args:
            tasks: Dictionary mapping task names to zero-argument callables
            timeout_per_task: Maximum time (seconds) to wait for each task

        Returns:
            Dictionary mapping task names to results (None for timeouts/failures)
        """
