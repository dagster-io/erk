"""Abstract base class for PR submission strategies.

The strategy pattern allows different PR submission mechanisms (Graphite-first,
core git+gh) to share a common interface. Callers select a strategy based on
context and invoke it uniformly.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult

# Type alias for the generator yielded by strategy execution
StrategyGenerator = Generator[
    ProgressEvent | CompletionEvent[SubmitStrategyResult | SubmitStrategyError], None, None
]


class SubmitStrategy(ABC):
    """Abstract base class for PR submission strategies.

    Strategies encapsulate different approaches to submitting a PR:
    - GraphiteSubmitStrategy: Uses gt submit for push + PR creation
    - CoreSubmitStrategy: Uses git push + gh pr create

    The execute() method returns a generator that yields progress events
    and a final completion event with the result or error.
    """

    @abstractmethod
    def execute(
        self,
        ctx: ErkContext,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute the submission strategy.

        Args:
            ctx: ErkContext providing git, github, and graphite operations
            cwd: Working directory (must be in a git repository)
            force: If True, force push (use when branch has diverged)

        Yields:
            ProgressEvent for status updates
            CompletionEvent with SubmitStrategyResult on success,
                SubmitStrategyError on failure
        """
