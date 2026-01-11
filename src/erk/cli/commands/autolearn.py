"""Autolearn helper for creating learn plan issues after landing PRs.

This module provides the logic to automatically create a learn plan issue
when landing a PR from a plan branch, if autolearn is enabled in config.
"""

from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_output
from erk_shared.sessions.discovery import find_sessions_for_plan


def _is_learn_plan(issue: IssueInfo) -> bool:
    """Check if an issue is already a learn plan by checking for erk-learn label.

    Args:
        issue: IssueInfo to check

    Returns:
        True if the issue has the erk-learn label, False otherwise
    """
    return "erk-learn" in issue.labels


def maybe_create_autolearn_issue(
    ctx: ErkContext,
    *,
    repo_root: Path,
    branch: str,
    pr_number: int,
) -> None:
    """Create a learn plan issue if autolearn is enabled and conditions are met.

    This function is fail-open: errors are reported as warnings but do not
    prevent the land operation from succeeding.

    Args:
        ctx: ErkContext with configuration and gateways
        repo_root: Repository root path
        branch: Branch name that was landed
        pr_number: PR number that was merged
    """
    # Check if autolearn is enabled
    if ctx.global_config is None or not ctx.global_config.autolearn:
        return

    # Extract plan issue number from branch name
    plan_issue_number = extract_leading_issue_number(branch)
    if plan_issue_number is None:
        # Branch doesn't have a plan prefix - nothing to do
        return

    # Fetch source plan issue to check if it's already a learn plan
    try:
        source_issue = ctx.github_issues.get_issue(repo_root, plan_issue_number)
    except RuntimeError as e:
        user_output(
            click.style("⚠ ", fg="yellow")
            + f"Autolearn: Could not fetch source issue #{plan_issue_number}: {e}"
        )
        return

    # Skip if source is already a learn plan (avoid recursive learn plans)
    if _is_learn_plan(source_issue):
        return

    # Discover sessions associated with the plan
    sessions = find_sessions_for_plan(ctx.github_issues, repo_root, plan_issue_number)
    all_session_ids = sessions.all_session_ids()
    if not all_session_ids:
        user_output(
            click.style("⚠ ", fg="yellow")
            + f"Autolearn: No sessions found for plan #{plan_issue_number}"
        )
        return

    # Create the learn plan title
    learn_title = f"Learn: {source_issue.title}"
    # Remove any existing suffix like [erk-plan]
    if learn_title.endswith("[erk-plan]"):
        learn_title = learn_title[: -len("[erk-plan]")].strip()

    # Create minimal plan content (learn plans don't need detailed content)
    plan_content = f"""# {learn_title}

Automatically created from landing PR #{pr_number}.

## Source

- Plan Issue: #{plan_issue_number}
- Merged PR: #{pr_number}
"""

    # Create the learn plan issue
    result = create_plan_issue(
        ctx.github_issues,
        repo_root,
        plan_content,
        title=learn_title,
        plan_type="learn",
        extra_labels=None,
        title_suffix="[erk-learn]",
        source_plan_issues=[plan_issue_number],
        extraction_session_ids=all_session_ids,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
    )

    if result.success:
        user_output(
            click.style("✓", fg="green")
            + f" Created learn plan #{result.issue_number}: {learn_title}"
        )
    else:
        user_output(
            click.style("⚠ ", fg="yellow")
            + f"Autolearn: Failed to create learn plan: {result.error}"
        )
