"""Shared helper for cleaning up review PRs when plans are closed or landed."""

from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.metadata.plan_header import clear_plan_header_review_pr
from erk_shared.gateway.github.metadata_blocks import find_metadata_block
from erk_shared.gateway.github.types import BodyText
from erk_shared.output.output import user_output


def cleanup_review_pr(
    ctx: ErkContext,
    *,
    repo_root: Path,
    issue_number: int,
    reason: str,
) -> int | None:
    """Close a plan's review PR and clear its metadata.

    This function is fail-open: if any step fails, the main operation
    (plan close or land) still succeeds. Warnings are logged but exceptions
    are not propagated.

    The function is idempotent: if the review PR is already closed or
    metadata is already cleared, it returns without error.

    Args:
        ctx: Erk context with gateway dependencies
        repo_root: Repository root path
        issue_number: Plan issue number
        reason: Human-readable reason for closing (used in PR comment)

    Returns:
        The review PR number if closed, None otherwise
    """
    # LBYL: Check issue exists
    if not ctx.issues.issue_exists(repo_root, issue_number):
        return None

    # LBYL: Get issue and check for plan-header block
    issue = ctx.issues.get_issue(repo_root, issue_number)
    block = find_metadata_block(issue.body, "plan-header")
    if block is None:
        return None

    # LBYL: Check review_pr is not None
    review_pr = block.data.get("review_pr")
    if review_pr is None:
        return None

    # Step 1: Add comment to review PR explaining why it was closed
    comment_body = f"This review PR was automatically closed because {reason}."
    try:
        ctx.issues.add_comment(repo_root, review_pr, comment_body)
    except RuntimeError:
        user_output(f"Warning: Could not add comment to review PR #{review_pr}")

    # Step 2: Close the review PR
    try:
        ctx.github.close_pr(repo_root, review_pr)
    except RuntimeError:
        user_output(f"Warning: Could not close review PR #{review_pr}")
        # If close fails, do NOT clear metadata (preserves consistency)
        return None

    # Step 3: Clear review_pr metadata (archives to last_review_pr)
    try:
        updated_body = clear_plan_header_review_pr(issue.body)
        ctx.issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
    except (ValueError, RuntimeError):
        user_output(f"Warning: Could not clear review PR metadata for issue #{issue_number}")

    user_output(f"Closed review PR #{review_pr}")
    return review_pr
