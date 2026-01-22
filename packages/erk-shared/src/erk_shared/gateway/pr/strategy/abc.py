"""Abstract base class for PR submit strategies.

The strategy pattern enables different PR submission flows (Graphite, standard)
to share a common interface while encapsulating their specific logic.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.pr.strategy.types import StrategyGenerator


class SubmitStrategy(ABC):
    """Abstract base class for PR submit strategies.

    Each strategy encapsulates a complete PR submission flow, yielding
    progress events during execution and returning a result or error
    via a completion event.

    Strategies are stateless - all required state is passed through
    the execute method parameters.
    """

    @abstractmethod
    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute the PR submission strategy.

        Args:
            ops: Operations interface providing git, github, graphite, etc.
            cwd: Current working directory (within the repository)
            force: Force push (use when branch has diverged from remote)

        Yields:
            ProgressEvent: Progress notifications during execution
            CompletionEvent: Final result (SubmitStrategyResult or SubmitStrategyError)
        """
        ...
