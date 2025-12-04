"""Unified PR submission operation.

This module provides execute_submit_pr which orchestrates the full PR submission
workflow in Python:

1. Preflight: auth checks, squash commits, submit to Graphite, extract diff
2. AI Generation: generate commit message via ClaudeCLIExecutor
3. Finalize: update PR metadata with AI-generated content

Key principle: Operations orchestrate. Claude generates content.
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.operations.finalize import execute_finalize
from erk_shared.integrations.gt.operations.preflight import execute_preflight
from erk_shared.integrations.gt.types import (
    PostAnalysisError,
    PreAnalysisError,
    PreflightResult,
    SubmitPRError,
    SubmitPRResult,
)


def execute_submit_pr(
    ops: GtKit,
    cwd: Path,
    session_id: str,
    *,
    force: bool = False,
    publish: bool = True,
) -> Generator[ProgressEvent | CompletionEvent[SubmitPRResult | SubmitPRError]]:
    """Execute full PR submission workflow.

    This operation orchestrates the complete PR submission:
    1. Run preflight (auth, squash, submit to Graphite, extract diff)
    2. Generate commit message via AI
    3. Finalize PR with generated message

    Args:
        ops: GtKit for dependency injection (includes ai executor)
        cwd: Working directory (repository path)
        session_id: Claude session ID for scratch file isolation
        force: If True, force push even if remote has diverged
        publish: If True, mark PR as ready for review (not draft)

    Yields:
        ProgressEvent for status updates
        CompletionEvent with SubmitPRResult on success, or SubmitPRError on failure
    """
    # Step 1: Preflight
    yield ProgressEvent("Running preflight checks...")
    preflight_result: PreflightResult | None = None
    for event in execute_preflight(ops, cwd, session_id, force=force):
        if isinstance(event, CompletionEvent):
            if isinstance(event.result, (PreAnalysisError, PostAnalysisError)):
                yield CompletionEvent(SubmitPRError.from_preflight(event.result))
                return
            preflight_result = event.result
        else:
            yield event

    if preflight_result is None:
        yield CompletionEvent(SubmitPRError.from_ai("Preflight returned no result"))
        return

    yield ProgressEvent("Preflight complete", style="success")

    # Step 2: Generate commit message via AI
    yield ProgressEvent("Generating commit message via AI...")
    try:
        diff_path = Path(preflight_result.diff_file)
        repo_root = Path(preflight_result.repo_root)
        ai_result = ops.ai.generate_commit_message(
            diff_file=diff_path,
            repo_root=repo_root,
            current_branch=preflight_result.current_branch,
            parent_branch=preflight_result.parent_branch,
        )
        title = ai_result.title
        body = ai_result.body
        yield ProgressEvent("Commit message generated", style="success")
    except Exception as e:
        yield CompletionEvent(
            SubmitPRError.from_ai(
                f"AI generation failed: {e}",
                details={"exception": str(e)},
            )
        )
        return

    # Step 3: Finalize
    yield ProgressEvent("Updating PR metadata...")
    for event in execute_finalize(
        ops,
        cwd,
        preflight_result.pr_number,
        title,
        pr_body=body,
        diff_file=preflight_result.diff_file,
    ):
        if isinstance(event, CompletionEvent):
            if isinstance(event.result, PostAnalysisError):
                yield CompletionEvent(SubmitPRError.from_finalize(event.result))
                return
        else:
            yield event

    yield ProgressEvent("PR metadata updated", style="success")

    yield CompletionEvent(
        SubmitPRResult(
            success=True,
            pr_number=preflight_result.pr_number,
            pr_url=preflight_result.pr_url,
            pr_title=title,
            graphite_url=preflight_result.graphite_url,
            branch_name=preflight_result.branch_name,
            issue_number=preflight_result.issue_number,
            message=(
                f"PR #{preflight_result.pr_number} submitted successfully: "
                f"{preflight_result.pr_url}"
            ),
        )
    )
