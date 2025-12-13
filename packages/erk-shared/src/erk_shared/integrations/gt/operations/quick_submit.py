"""Quick commit and submit operation for rapid iteration.

This operation stages all changes, commits with "update" message if there are changes,
then submits via Graphite. Returns the PR URL for easy access.
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.github.types import PRNotFound
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import QuickSubmitError, QuickSubmitSuccess


def execute_quick_submit(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[QuickSubmitSuccess | QuickSubmitError]]:
    """Execute the quick-submit workflow.

    Stages all changes, commits with "update" message if there are changes,
    then runs gt submit. Returns the PR URL after successful submit.

    Args:
        ops: GtKit operations interface.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with QuickSubmitSuccess or QuickSubmitError
    """
    # Step 1: Stage all changes
    yield ProgressEvent("Staging all changes...")
    try:
        ops.git.add_all(cwd)
    except Exception as e:
        yield CompletionEvent(
            QuickSubmitError(
                success=False,
                error_type="stage_failed",
                message=f"Failed to stage changes: {e}",
            )
        )
        return

    # Step 2: Check if there are staged changes
    yield ProgressEvent("Checking for staged changes...")
    has_changes = ops.git.has_staged_changes(cwd)
    committed = False

    # Step 3: Commit if there are staged changes
    if has_changes:
        yield ProgressEvent("Committing changes...")
        try:
            ops.git.commit(cwd, "update")
            committed = True
        except Exception as e:
            yield CompletionEvent(
                QuickSubmitError(
                    success=False,
                    error_type="commit_failed",
                    message=f"Failed to commit changes: {e}",
                )
            )
            return

    # Step 4: Run gt submit
    yield ProgressEvent("Submitting to Graphite...")
    repo_root = ops.git.get_repository_root(cwd)
    try:
        ops.graphite.submit_stack(repo_root, quiet=True, force=True)
    except Exception as e:
        yield CompletionEvent(
            QuickSubmitError(
                success=False,
                error_type="submit_failed",
                message=f"Failed to submit: {e}",
            )
        )
        return

    # Step 5: Get PR URL after successful submit
    yield ProgressEvent("Getting PR URL...")
    pr_url: str | None = None
    current_branch = ops.git.get_current_branch(cwd)
    if current_branch:
        pr_details = ops.github.get_pr_for_branch(repo_root, current_branch)
        if not isinstance(pr_details, PRNotFound):
            pr_url = pr_details.url

    # Success
    msg = (
        "Changes submitted successfully"
        if committed
        else "No new changes, submitted existing commits"
    )
    yield CompletionEvent(
        QuickSubmitSuccess(
            success=True,
            staged_changes=has_changes,
            committed=committed,
            message=msg,
            pr_url=pr_url,
        )
    )
