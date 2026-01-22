"""Core submit strategy implementation.

This strategy wraps execute_core_submit to provide a unified strategy interface
for standard git + GitHub CLI PR submission (non-Graphite path).
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import SubmitStrategy
from erk_shared.gateway.pr.strategy.types import (
    StrategyGenerator,
    SubmitStrategyError,
    SubmitStrategyResult,
)
from erk_shared.gateway.pr.submit import execute_core_submit
from erk_shared.gateway.pr.types import CoreSubmitError


@dataclass(frozen=True)
class CoreSubmitStrategy(SubmitStrategy):
    """Strategy that uses git + GitHub CLI for PR submission.

    This strategy wraps the existing execute_core_submit() function to provide
    a unified interface with GraphiteSubmitStrategy. It handles:
    1. GitHub authentication check
    2. Uncommitted changes (WIP commit)
    3. Branch push
    4. PR creation/update

    Use this strategy when Graphite is not available or the branch isn't tracked.
    """

    pr_title: str
    pr_body: str
    plans_repo: str | None

    def execute(
        self,
        ops: GtKit,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute core git+gh submit workflow.

        Yields events from execute_core_submit and converts final result
        to unified SubmitStrategyResult or SubmitStrategyError.
        """
        for event in execute_core_submit(
            ops,
            cwd,
            self.pr_title,
            self.pr_body,
            force=force,
            plans_repo=self.plans_repo,
        ):
            if isinstance(event, ProgressEvent):
                yield event
            elif isinstance(event, CompletionEvent):
                result = event.result

                if isinstance(result, CoreSubmitError):
                    yield CompletionEvent(
                        result=SubmitStrategyError(
                            error_type=result.error_type,
                            message=result.message,
                            details=result.details,
                        )
                    )
                else:
                    # CoreSubmitResult - success case
                    yield CompletionEvent(
                        result=SubmitStrategyResult(
                            pr_number=result.pr_number,
                            base_branch=result.base_branch,
                            graphite_url=None,  # Standard flow has no Graphite URL
                            pr_url=result.pr_url,
                            branch_name=result.branch_name,
                            was_created=result.was_created,
                        )
                    )
