"""Fake submit strategy for testing.

Provides a configurable fake that yields pre-configured progress messages
and returns a pre-configured result (success or error).
"""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult


@dataclass(frozen=True)
class FakeSubmitStrategy(SubmitStrategy):
    """Fake strategy for testing that yields configured progress and result.

    Attributes:
        result: The result to return (success or error)
        progress_messages: Progress messages to yield before result
    """

    result: SubmitStrategyResult | SubmitStrategyError
    progress_messages: tuple[str, ...] = ()

    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> Generator[
        ProgressEvent | CompletionEvent[SubmitStrategyResult | SubmitStrategyError], None, None
    ]:
        """Execute fake submit by yielding configured progress and result."""
        # Yield configured progress messages
        for message in self.progress_messages:
            yield ProgressEvent(message=message, style="info")

        # Yield completion with configured result
        yield CompletionEvent(result=self.result)
