"""Submit issue for remote AI implementation via GitHub Actions."""

from datetime import UTC, datetime

import click
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event
from erk_shared.naming import derive_branch_name_with_date
from erk_shared.output.output import user_output

from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PLAN_LABEL,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


def _construct_workflow_run_url(issue_url: str, run_id: str) -> str:
    """Construct GitHub Actions workflow run URL from issue URL and run ID.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        run_id: Workflow run ID

    Returns:
        Workflow run URL (e.g., https://github.com/owner/repo/actions/runs/1234567890)
    """
    # Extract owner/repo from issue URL
    # Pattern: https://github.com/owner/repo/issues/123
    parts = issue_url.split("/")
    if len(parts) >= 5:
        owner = parts[-4]
        repo = parts[-3]
        return f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"
    return f"https://github.com/actions/runs/{run_id}"


def _strip_plan_markers(title: str) -> str:
    """Strip 'Plan:' prefix and '[erk-plan]' suffix from issue title for use as PR title."""
    result = title
    # Strip "Plan: " prefix if present
    if result.startswith("Plan: "):
        result = result[6:]
    # Strip " [erk-plan]" suffix if present
    if result.endswith(" [erk-plan]"):
        result = result[:-11]
    return result


def _construct_pr_url(issue_url: str, pr_number: int) -> str:
    """Construct GitHub PR URL from issue URL and PR number.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        pr_number: PR number

    Returns:
        PR URL (e.g., https://github.com/owner/repo/pull/456)
    """
    # Extract owner/repo from issue URL
    # Pattern: https://github.com/owner/repo/issues/123
    parts = issue_url.split("/")
    if len(parts) >= 5:
        owner = parts[-4]
        repo = parts[-3]
        return f"https://github.com/{owner}/{repo}/pull/{pr_number}"
    return f"https://github.com/pull/{pr_number}"


@click.command("submit")
@click.argument("issue_number", type=int)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_number: int) -> None:
    """Submit issue for remote AI implementation via GitHub Actions.

    Creates branch and draft PR locally (for correct commit attribution),
    then triggers the dispatch-erk-queue.yml GitHub Actions workflow.

    The workflow will:
    - Pick up the existing branch and PR
    - Run the implementation

    Arguments:
        ISSUE_NUMBER: GitHub issue number to submit for implementation

    Requires:
        - Issue must have erk-plan label
        - Issue must be OPEN
        - Working directory must be clean (no uncommitted changes)
    """
    # Validate GitHub CLI authentication upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Step 1: Save current state and check for uncommitted changes
    original_branch = ctx.git.get_current_branch(repo.root)
    if original_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Not on a branch (detached HEAD state). Cannot submit from here."
        )
        raise SystemExit(1)

    if ctx.git.has_uncommitted_changes(repo.root):
        user_output(
            click.style("Error: ", fg="red")
            + "You have uncommitted changes. Please commit or stash them first."
        )
        raise SystemExit(1)

    # Fetch issue from GitHub
    try:
        issue = ctx.issues.get_issue(repo.root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    # Validate: must have erk-plan label
    if ERK_PLAN_LABEL not in issue.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have {ERK_PLAN_LABEL} label\n\n"
            "Cannot submit non-plan issues for automated implementation.\n"
            "To create a plan, use: /erk:craft-plan"
        )
        raise SystemExit(1)

    # Validate: must be OPEN
    if issue.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"Issue #{issue_number} is {issue.state}\n\n"
            "Cannot submit closed issues for automated implementation."
        )
        raise SystemExit(1)

    # Display issue details
    user_output("Submitting issue for automated implementation:")
    user_output(f"  Number: {click.style(f'#{issue_number}', fg='cyan')}")
    user_output(f"  Title:  {click.style(issue.title, fg='yellow')}")
    user_output(f"  State:  {click.style(issue.state, fg='green')}")
    user_output("")

    # Get GitHub username from gh CLI (authentication already validated)
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Step 2: Derive branch name with date suffix
    branch_name = derive_branch_name_with_date(issue.title)
    user_output(f"Branch name: {click.style(branch_name, fg='cyan')}")

    # Step 3: Check if branch already exists on remote
    trunk_branch = ctx.git.get_trunk_branch(repo.root)
    branch_exists = ctx.git.branch_exists_on_remote(repo.root, "origin", branch_name)
    pr_number: int | None = None

    if branch_exists:
        # Check PR status for existing branch
        pr_status = ctx.github.get_pr_status(repo.root, branch_name, debug=False)
        if pr_status.pr_number is not None:
            pr_number = pr_status.pr_number
            user_output(
                f"PR #{pr_number} already exists for branch "
                f"'{branch_name}' (state: {pr_status.state})"
            )
            user_output("Skipping branch/PR creation, triggering workflow...")
        else:
            user_output(f"Branch '{branch_name}' exists but no PR. Skipping creation...")
    else:
        # Step 4: Create branch and initial commit
        user_output(f"Creating branch from origin/{trunk_branch}...")

        # Fetch trunk branch
        ctx.git.fetch_branch(repo.root, "origin", trunk_branch)

        # Create and checkout new branch from trunk
        ctx.git.create_branch(repo.root, branch_name, f"origin/{trunk_branch}")
        ctx.git.checkout_branch(repo.root, branch_name)

        # Create empty commit to establish branch for PR
        # The workflow will reconstruct .impl/ from the GitHub issue
        ctx.git.commit(
            repo.root,
            f"Initialize implementation for issue #{issue_number}",
            allow_empty=True,
        )
        ctx.git.push_to_remote(repo.root, "origin", branch_name, set_upstream=True)
        user_output(click.style("✓", fg="green") + " Branch pushed to remote")

        # Step 5: Create draft PR
        user_output("Creating draft PR...")
        pr_body = (
            f"**Author:** @{submitted_by}\n"
            f"**Plan:** #{issue_number}\n\n"
            f"**Status:** Queued for implementation\n\n"
            f"This PR will be marked ready for review after implementation completes.\n\n"
            f"---\n\n"
            f"Closes #{issue_number}"
        )
        pr_title = _strip_plan_markers(issue.title)
        pr_number = ctx.github.create_pr(
            repo_root=repo.root,
            branch=branch_name,
            title=pr_title,
            body=pr_body,
            base=trunk_branch,
            draft=True,
        )
        user_output(click.style("✓", fg="green") + f" Draft PR #{pr_number} created")

        # Update PR body with checkout command footer
        footer_body = (
            f"{pr_body}\n\n"
            f"---\n\n"
            f"To checkout this PR locally:\n\n"
            f"```\n"
            f"erk pr checkout {pr_number}\n"
            f"```"
        )
        ctx.github.update_pr_body(repo.root, pr_number, footer_body)

        # Step 6: Restore local state
        user_output("Restoring local state...")
        ctx.git.checkout_branch(repo.root, original_branch)
        ctx.git.delete_branch(repo.root, branch_name, force=True)
        user_output(click.style("✓", fg="green") + " Local branch cleaned up")

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Step 7: Trigger workflow via direct dispatch
    user_output("")
    user_output(f"Triggering workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")
    user_output(f"  Display name: {DISPATCH_WORKFLOW_METADATA_NAME}")
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs={
            "issue_number": str(issue_number),
            "submitted_by": submitted_by,
            "issue_title": issue.title,
        },
    )
    user_output(click.style("✓", fg="green") + " Workflow triggered.")

    validation_results = {
        "issue_is_open": True,
        "has_erk_plan_label": True,
    }

    # Create and post queued event comment
    workflow_url = _construct_workflow_run_url(issue.url, run_id)
    try:
        metadata_block = create_submission_queued_block(
            queued_at=queued_at,
            submitted_by=submitted_by,
            issue_number=issue_number,
            validation_results=validation_results,
            expected_workflow=DISPATCH_WORKFLOW_METADATA_NAME,
        )

        comment_body = render_erk_issue_event(
            title="🔄 Issue Queued for Implementation",
            metadata=metadata_block,
            description=(
                f"Issue submitted by **{submitted_by}** at {queued_at}.\n\n"
                f"The `{DISPATCH_WORKFLOW_METADATA_NAME}` workflow has been "
                f"triggered via direct dispatch.\n\n"
                f"**Workflow run:** {workflow_url}\n\n"
                f"Branch and draft PR were created locally for correct commit attribution."
            ),
        )

        user_output("Posting queued event comment...")
        ctx.issues.add_comment(repo.root, issue_number, comment_body)
        user_output(click.style("✓", fg="green") + " Queued event comment posted")
    except Exception as e:
        # Log warning but don't block - workflow is already triggered
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Failed to post queued comment: {e}\n"
            + "Workflow is already running."
        )

    # Success output
    user_output("")
    user_output(click.style("✓", fg="green") + " Issue submitted successfully!")
    user_output("")
    user_output("Next steps:")
    user_output(f"  • View issue: {issue.url}")
    if pr_number is not None:
        pr_url = _construct_pr_url(issue.url, pr_number)
        user_output(f"  • View PR: {pr_url}")
    user_output(f"  • View workflow run: {workflow_url}")
    user_output("")
