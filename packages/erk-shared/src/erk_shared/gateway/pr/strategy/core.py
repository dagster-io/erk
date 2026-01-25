"""Core PR submission strategy using git + gh.

This strategy uses standard git push + gh pr create for PR submission.
It works without Graphite and can be optionally enhanced with Graphite
stack metadata afterward via the graphite_enhance module.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.abc import StrategyGenerator, SubmitStrategy
from erk_shared.gateway.pr.strategy.types import SubmitStrategyError, SubmitStrategyResult
from erk_shared.gateway.pr.submit import execute_core_submit
from erk_shared.gateway.pr.types import CoreSubmitError, CoreSubmitResult


@dataclass(frozen=True)
class CoreSubmitStrategy(SubmitStrategy):
    """Strategy using git + gh for PR submission (no Graphite).

    This strategy wraps execute_core_submit() and converts its results
    to the unified strategy types. Use this when:
    - Graphite is not available or not authenticated
    - The branch is not tracked by Graphite
    - User explicitly requested --no-graphite

    The strategy handles the complete flow:
    1. Check GitHub authentication
    2. Handle uncommitted changes (WIP commit)
    3. Push branch to remote
    4. Create or update PR via gh

    Note: WIP commit handling is currently inside execute_core_submit().
    The plan is to move it pre-strategy in submit_cmd.py for consolidation.

    Attributes:
        plans_repo: Target repo in "owner/repo" format for cross-repo plans,
            or None for same-repo issue linking
    """

    plans_repo: str | None

    def execute(
        self,
        ctx: ErkContext,
        cwd: Path,
        *,
        force: bool,
    ) -> StrategyGenerator:
        """Execute core PR submission via git + gh.

        Args:
            ctx: ErkContext providing git and github operations
            cwd: Working directory
            force: If True, force push

        Yields:
            ProgressEvent for status updates
            CompletionEvent with SubmitStrategyResult or SubmitStrategyError
        """
        for event in execute_core_submit(
            ctx,
            cwd,
            pr_title="WIP",
            pr_body="",
            force=force,
            plans_repo=self.plans_repo,
        ):
            if isinstance(event, ProgressEvent):
                yield event
            elif isinstance(event, CompletionEvent):
                result = event.result
                if isinstance(result, CoreSubmitError):
                    yield CompletionEvent(
                        SubmitStrategyError(
                            error_type=result.error_type,
                            message=result.message,
                            details=result.details,
                        )
                    )
                elif isinstance(result, CoreSubmitResult):
                    yield CompletionEvent(
                        SubmitStrategyResult(
                            pr_number=result.pr_number,
                            base_branch=result.base_branch,
                            graphite_url=None,  # Core never has Graphite URL
                            pr_url=result.pr_url,
                            branch_name=result.branch_name,
                            was_created=result.was_created,
                        )
                    )
