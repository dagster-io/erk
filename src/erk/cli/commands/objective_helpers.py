"""Shared helpers for objective tracking in land commands.

These helpers are used by `erk land` to check for linked objectives
and prompt users to update them after landing.
"""

import logging
from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.gateway.pr.submit import has_issue_closing_reference
from erk_shared.naming import extract_objective_number
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound, PlanState

logger = logging.getLogger(__name__)

# Number of retry attempts for auto-close detection
_AUTO_CLOSE_MAX_RETRIES = 3
# Seconds to wait between retry attempts
_AUTO_CLOSE_RETRY_DELAY = 1.0


def _wait_for_issue_closure(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
) -> bool:
    """Wait for GitHub to auto-close an issue after PR merge.

    GitHub's auto-close is asynchronous - there's a delay between PR merge
    and linked issue closure. This function retries up to _AUTO_CLOSE_MAX_RETRIES
    times with _AUTO_CLOSE_RETRY_DELAY between attempts.

    Returns True if issue closed within retry window, False otherwise.
    Returns False if issue becomes inaccessible (fail-open).
    """
    plan_id = str(issue_number)
    logger.debug(
        "Waiting for issue #%d to close (max %d retries, %.1fs delay)",
        issue_number,
        _AUTO_CLOSE_MAX_RETRIES,
        _AUTO_CLOSE_RETRY_DELAY,
    )
    for attempt in range(_AUTO_CLOSE_MAX_RETRIES):
        ctx.time.sleep(_AUTO_CLOSE_RETRY_DELAY)
        result = ctx.plan_store.get_plan(repo_root, plan_id)
        if isinstance(result, PlanNotFound):
            logger.warning(
                "Issue #%d became inaccessible during retry %d", issue_number, attempt + 1
            )
            return False
        if result.state == PlanState.CLOSED:
            logger.debug("Issue #%d closed after %d retries", issue_number, attempt + 1)
            return True
        logger.debug(
            "Issue #%d still open after retry %d/%d",
            issue_number,
            attempt + 1,
            _AUTO_CLOSE_MAX_RETRIES,
        )
    logger.debug("Issue #%d did not close after %d retries", issue_number, _AUTO_CLOSE_MAX_RETRIES)
    return False


def check_and_display_plan_issue_closure(
    ctx: ErkContext,
    repo_root: Path,
    branch: str,
    *,
    pr_body: str,
) -> int | None:
    """Check and display plan issue closure status after landing.

    Differentiates between:
    - PR has "Closes #N" but issue still open: retry (async auto-close expected)
    - PR missing "Closes #N" and issue open: warn about missing reference
    - Issue already closed: success regardless

    Returns the plan issue number if found, None otherwise.
    This is fail-open: returns None silently if the issue doesn't exist.
    """
    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo_root, branch)
    if plan_id is None:
        return None

    plan_number = int(plan_id)

    has_closing_ref = has_issue_closing_reference(
        pr_body,
        plan_number,
        ctx.local_config.plans_repo if ctx.local_config else None,
    )
    logger.debug(
        "Plan issue #%d: has_closing_ref=%s, branch=%s",
        plan_number,
        has_closing_ref,
        branch,
    )

    result = ctx.plan_store.get_plan(repo_root, plan_id)
    if isinstance(result, PlanNotFound):
        logger.debug("Plan issue #%d not found, skipping closure check", plan_number)
        return None

    if result.state == PlanState.CLOSED:
        user_output(click.style("✓", fg="green") + f" Closed plan issue #{plan_number}")
        return plan_number

    # Issue is OPEN - behavior depends on whether PR has closing reference
    if has_closing_ref:
        # PR has "Closes #N" - GitHub should auto-close, but it's async.
        if _wait_for_issue_closure(ctx, repo_root, plan_number):
            user_output(click.style("✓", fg="green") + f" Closed plan issue #{plan_number}")
        else:
            # Still open after retries - unexpected, but not critical
            user_output(
                click.style("⚠ ", fg="yellow")
                + f"Plan issue #{plan_number} still open (expected auto-close)"
            )
    else:
        # PR missing "Closes #N" - this is the bug case we want to detect.
        # The user added the closing reference after PR creation, which doesn't work.
        user_output(
            click.style("⚠ ", fg="yellow")
            + f"PR missing closing reference - plan issue #{plan_number} won't auto-close"
        )
        # Offer to close the issue manually
        if ctx.console.confirm(f"Close issue #{plan_number} now?", default=True):
            ctx.plan_store.close_plan(repo_root, plan_id)
            user_output(click.style("✓", fg="green") + f" Closed plan issue #{plan_number}")

    return plan_number


def get_objective_for_branch(ctx: ErkContext, repo_root: Path, branch: str) -> int | None:
    """Extract objective issue number from branch's linked plan issue.

    Returns objective issue number if:
    1. Branch is associated with a plan with objective_id in metadata, OR
    2. Branch name encodes the objective number (fallback)

    Returns None otherwise (fail-open - never blocks landing).
    """
    try:
        result = ctx.plan_backend.get_plan_for_branch(repo_root, branch)
    except RuntimeError:
        return extract_objective_number(branch)
    if isinstance(result, PlanNotFound):
        return extract_objective_number(branch)
    if result.objective_id is not None:
        return result.objective_id
    return extract_objective_number(branch)
