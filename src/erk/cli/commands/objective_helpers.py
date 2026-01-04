"""Shared helpers for objective tracking in land commands.

These helpers are used by `erk land` to check for linked objectives
and prompt users to update them after landing.
"""

from pathlib import Path

import click

from erk.cli.output import stream_command_with_feedback
from erk.core.context import ErkContext
from erk_shared.github.metadata import extract_plan_header_objective_issue
from erk_shared.naming import extract_leading_issue_number
from erk_shared.output.output import user_confirm, user_output


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

    issue = ctx.issues.get_issue(repo_root, plan_number)
    if issue is None:
        return None

    return extract_plan_header_objective_issue(issue.body)


def prompt_objective_update(
    ctx: ErkContext,
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
