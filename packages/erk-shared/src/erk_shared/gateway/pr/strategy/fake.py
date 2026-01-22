"""Fake submit strategy for testing.

Provides a configurable fake strategy that returns predetermined results,
enabling tests to verify strategy consumer behavior without real git/GitHub operations.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.types import (
    StrategyGenerator,
    StrategyOutcome,
)


@dataclass(frozen=True)
class FakeSubmitStrategy(SubmitStrategy):
    """Fake strategy that yields configured progress messages and result.

    Use this in tests to verify that strategy consumers correctly handle
    progress events and result/error types without real git/GitHub operations.

    Attributes:
        result: The result or error to return via CompletionEvent
        progress_messages: Progress messages to yield before the result
    """

    result: StrategyOutcome
    progress_messages: tuple[str, ...] = ()

    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute fake strategy, yielding configured progress and result."""
        # Yield configured progress messages
        for message in self.progress_messages:
            yield ProgressEvent(message=message, style="info")

        # Yield the configured result
        yield CompletionEvent(result=self.result)
