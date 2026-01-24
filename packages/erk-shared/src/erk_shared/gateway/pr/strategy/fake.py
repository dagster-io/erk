"""Fake implementation of SubmitStrategy for testing.

FakeSubmitStrategy allows tests to control the outcome of PR submission
without invoking real git/GitHub/Graphite operations. Configure it with
the desired result and progress messages at construction time.
"""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult


@dataclass(frozen=True)
class FakeSubmitStrategy(SubmitStrategy):
    """Fake strategy for testing.

    Constructor injection controls the behavior:
    - result: The SubmitStrategyResult or SubmitStrategyError to return
    - progress_messages: Optional sequence of progress messages to emit

    Attributes:
        result: The result to return from execute()
        progress_messages: Progress messages to emit before completion
    """

    result: SubmitStrategyResult | SubmitStrategyError
    progress_messages: tuple[str, ...] = ()

    def execute(
        self,
        ctx: ErkContext,
        cwd: Path,
        *,
        force: bool,
    ) -> Generator[
        ProgressEvent | CompletionEvent[SubmitStrategyResult | SubmitStrategyError], None, None
    ]:
        """Execute the fake strategy, yielding configured events."""
        for message in self.progress_messages:
            yield ProgressEvent(message)
        yield CompletionEvent(self.result)
