"""Abstract base class for PR submit strategies.

The strategy pattern allows different PR submission flows (Graphite-first,
core flow) to be implemented as interchangeable strategies with a common
interface.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult


class SubmitStrategy(ABC):
    """Abstract base class for PR submit strategies.

    Strategies yield progress events during execution and complete with
    either a SubmitStrategyResult (success) or SubmitStrategyError (failure).

    The generator pattern enables:
    1. Progress reporting without CLI dependencies
    2. Testable progress assertions
    3. Flexible rendering (CLI, JSON, silent)
    """

    @abstractmethod
    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> Generator[
        ProgressEvent | CompletionEvent[SubmitStrategyResult | SubmitStrategyError], None, None
    ]:
        """Execute the submit strategy.

        Args:
            ops: GtKit providing git, github, graphite, and branch_manager operations
            cwd: Working directory (typically repository root or worktree)
            force: Force push flag (use when branch has diverged from remote)

        Yields:
            ProgressEvent: Progress notifications during execution
            CompletionEvent: Final result (exactly one, always last)

        The final event is always a CompletionEvent containing either:
        - SubmitStrategyResult: Successful submission
        - SubmitStrategyError: Failed submission
        """
        ...
