"""Shared helpers for objective tracking in land commands.

These helpers are used by `erk land` to check for linked objectives
and prompt users to update them after landing.
"""

import logging
from pathlib import Path

import click

from erk.cli.output import stream_command_with_feedback
from erk.core.context import ErkContext
from erk_shared.gateway.pr.submit import has_issue_closing_reference
from erk_shared.github.metadata.plan_header import extract_plan_header_objective_issue
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_confirm, user_output

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
    logger.debug(
        "Waiting for issue #%d to close (max %d retries, %.1fs delay)",
        issue_number,
        _AUTO_CLOSE_MAX_RETRIES,
        _AUTO_CLOSE_RETRY_DELAY,
    )
    for attempt in range(_AUTO_CLOSE_MAX_RETRIES):
        ctx.time.sleep(_AUTO_CLOSE_RETRY_DELAY)
        try:
            issue = ctx.issues.get_issue(repo_root, issue_number)
        except RuntimeError:
            logger.warning(
                "Issue #%d became inaccessible during retry %d", issue_number, attempt + 1
            )
            return False
        if issue.state == "CLOSED":
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
    plan_number = extract_leading_issue_number(branch)
    if plan_number is None:
        return None

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

    # GitHubIssues.get_issue raises RuntimeError for missing issues.
    # This is a fail-open feature (non-critical), so we catch and return None.
    try:
        issue = ctx.issues.get_issue(repo_root, plan_number)
    except RuntimeError:
        logger.debug("Plan issue #%d not found, skipping closure check", plan_number)
        return None

    if issue.state == "CLOSED":
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

    return plan_number


def get_objective_for_branch(ctx: ErkContext, repo_root: Path, branch: str) -> int | None:
    """Extract objective issue number from branch's linked plan issue.

    Returns objective issue number if:
    1. Branch has P<number>- prefix (plan issue link)
    2. Plan issue has objective_issue in its metadata

    Returns None otherwise (fail-open - never blocks landing).
    """
    plan_number = extract_leading_issue_number(branch)
    if plan_number is None:
        return None

    # GitHubIssues.get_issue raises RuntimeError for missing issues.
    # This is a fail-open feature (non-critical), so we catch and return None.
    try:
        issue = ctx.issues.get_issue(repo_root, plan_number)
    except RuntimeError:
        return None

    return extract_plan_header_objective_issue(issue.body)


def prompt_objective_update(
    ctx: ErkContext,
    *,
    repo_root: Path,
    objective_number: int,
    pr_number: int,
    branch: str,
    force: bool,
) -> None:
    """Prompt user to update objective after landing.

    Args:
        ctx: ErkContext with claude_executor
        repo_root: Repository root path for Claude execution
        objective_number: The linked objective issue number
        pr_number: The PR number that was just landed
        branch: The branch name that was landed
        force: If True, skip prompt (print command to run later)
    """
    user_output(f"   Linked to Objective #{objective_number}")

    # Build the command with all arguments for context-free execution
    # --auto-close enables automatic objective closing when all steps are complete
    cmd = (
        f"/erk:objective-update-with-landed-pr "
        f"--pr {pr_number} --objective {objective_number} --branch {branch} --auto-close"
    )

    if force:
        # --force skips all prompts, print command for later
        user_output(f"   Run '{cmd}' to update objective")
        return

    # Ask y/n prompt
    user_output("")
    if not user_confirm("Update objective now? (runs Claude agent)", default=True):
        user_output("")
        user_output("Skipped. To update later, run:")
        user_output(f"  {cmd}")
    else:
        # Add feedback BEFORE streaming starts (important for visibility)
        user_output("")
        user_output("Starting objective update...")

        result = stream_command_with_feedback(
            executor=ctx.claude_executor,
            command=cmd,
            worktree_path=repo_root,
            dangerous=True,
        )

        # Add feedback AFTER streaming completes
        if result.success:
            user_output("")
            user_output(click.style("✓", fg="green") + " Objective updated successfully")
        else:
            user_output("")
            user_output(
                click.style("⚠", fg="yellow") + f" Objective update failed: {result.error_message}"
            )
            user_output("  Run '/erk:objective-update-with-landed-pr' manually to retry")
