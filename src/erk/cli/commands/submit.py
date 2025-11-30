"""Submit issue for remote AI implementation via GitHub Actions."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.issue_link_branches import DevelopmentBranch
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event
from erk_shared.naming import (
    derive_branch_name_from_title,
    format_branch_timestamp_suffix,
    sanitize_worktree_name,
)
from erk_shared.output.output import user_output
from erk_shared.worker_impl_folder import create_worker_impl_folder

from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PLAN_LABEL,
    USE_GITHUB_NATIVE_BRANCH_LINKING,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext

logger = logging.getLogger(__name__)


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


def _ensure_unique_branch_name(
    ctx: ErkContext,
    repo_root: Path,
    base_name: str,
) -> str:
    """Ensure branch name is unique by adding numeric suffix if needed.

    If the base_name already exists on the remote, appends -1, -2, etc.
    until a unique name is found. This prevents `gh issue develop` from
    failing when a branch with the same name already exists.

    Args:
        ctx: ErkContext with git operations
        repo_root: Repository root path
        base_name: Initial branch name to check

    Returns:
        Unique branch name (original if available, or with -1, -2, etc. suffix)
    """
    if not ctx.git.branch_exists_on_remote(repo_root, "origin", base_name):
        return base_name

    for i in range(1, 100):
        candidate = f"{base_name}-{i}"
        if not ctx.git.branch_exists_on_remote(repo_root, "origin", candidate):
            return candidate

    raise RuntimeError(f"Could not find unique branch name after 100 attempts: {base_name}")


def _close_orphaned_draft_prs(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
    keep_pr_number: int,
) -> list[int]:
    """Close old draft PRs linked to an issue, keeping the specified one.

    Returns list of PR numbers that were closed.
    """
    pr_linkages = ctx.github.get_prs_linked_to_issues(repo_root, [issue_number])
    linked_prs = pr_linkages.get(issue_number, [])

    closed_prs: list[int] = []
    for pr in linked_prs:
        # Close only: draft PRs with erk-plan label, that are OPEN, and not the one we just created
        is_erk_plan_pr = ERK_PLAN_LABEL in pr.labels
        if pr.is_draft and pr.state == "OPEN" and pr.number != keep_pr_number and is_erk_plan_pr:
            ctx.github.close_pr(repo_root, pr.number)
            closed_prs.append(pr.number)

    return closed_prs


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

    # Step 2: Create or derive branch name for the issue
    trunk_branch = ctx.git.get_trunk_branch(repo.root)
    logger.debug("trunk_branch=%s", trunk_branch)
    logger.debug("USE_GITHUB_NATIVE_BRANCH_LINKING=%s", USE_GITHUB_NATIVE_BRANCH_LINKING)
    if USE_GITHUB_NATIVE_BRANCH_LINKING:
        # Compute branch name: truncate to 31 chars, then append timestamp suffix
        base_branch_name = sanitize_worktree_name(f"{issue_number}-{issue.title}")
        logger.debug("base_branch_name=%s", base_branch_name)
        timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
        logger.debug("timestamp_suffix=%s", timestamp_suffix)
        desired_branch_name = base_branch_name + timestamp_suffix
        logger.debug("desired_branch_name (before unique check)=%s", desired_branch_name)

        # Ensure unique name to prevent gh issue develop failure
        desired_branch_name = _ensure_unique_branch_name(ctx, repo.root, desired_branch_name)
        logger.debug("desired_branch_name (after unique check)=%s", desired_branch_name)

        # Use GitHub's native branch linking via `gh issue develop`
        logger.debug(
            "Calling create_development_branch: repo_root=%s, issue_number=%d, "
            "branch_name=%s, base_branch=%s",
            repo.root,
            issue_number,
            desired_branch_name,
            trunk_branch,
        )
        dev_branch = ctx.issue_link_branches.create_development_branch(
            repo.root,
            issue_number,
            branch_name=desired_branch_name,
            base_branch=trunk_branch,
        )
        logger.debug(
            "create_development_branch returned: branch_name=%s, already_existed=%s",
            dev_branch.branch_name,
            dev_branch.already_existed,
        )
    else:
        # Traditional branch naming from issue title
        branch_name = derive_branch_name_from_title(issue.title)
        dev_branch = DevelopmentBranch(
            branch_name=branch_name,
            issue_number=issue_number,
            already_existed=False,
        )
    branch_name = dev_branch.branch_name

    if dev_branch.already_existed:
        user_output(f"Using existing linked branch: {click.style(branch_name, fg='cyan')}")
    else:
        user_output(f"Created linked branch: {click.style(branch_name, fg='cyan')}")

    # Step 3: Check if branch already exists on remote
    branch_exists = ctx.git.branch_exists_on_remote(repo.root, "origin", branch_name)
    logger.debug("branch_exists_on_remote(%s)=%s", branch_name, branch_exists)
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
            # Branch exists but no PR - need to add a commit for PR creation
            user_output(f"Branch '{branch_name}' exists but no PR. Adding placeholder commit...")

            # Fetch and checkout the remote branch locally
            ctx.git.fetch_branch(repo.root, "origin", branch_name)
            ctx.git.create_tracking_branch(repo.root, branch_name, f"origin/{branch_name}")
            ctx.git.checkout_branch(repo.root, branch_name)

            # Create empty commit as placeholder for PR creation
            ctx.git.commit(
                repo.root,
                f"[erk-plan] Initialize implementation for issue #{issue_number}",
            )
            ctx.git.push_to_remote(repo.root, "origin", branch_name)
            user_output(click.style("✓", fg="green") + " Placeholder commit pushed")

            # Now create the PR
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

            # Close any orphaned draft PRs
            closed_prs = _close_orphaned_draft_prs(ctx, repo.root, issue_number, pr_number)
            if closed_prs:
                user_output(
                    click.style("✓", fg="green")
                    + f" Closed {len(closed_prs)} orphaned draft PR(s): "
                    + ", ".join(f"#{n}" for n in closed_prs)
                )

            # Restore local state
            ctx.git.checkout_branch(repo.root, original_branch)
            ctx.git.delete_branch(repo.root, branch_name, force=True)
            user_output(click.style("✓", fg="green") + " Local branch cleaned up")
    else:
        # Step 4: Create branch and initial commit
        user_output(f"Creating branch from origin/{trunk_branch}...")

        # Fetch trunk branch
        ctx.git.fetch_branch(repo.root, "origin", trunk_branch)

        # Create and checkout new branch from trunk
        ctx.git.create_branch(repo.root, branch_name, f"origin/{trunk_branch}")
        ctx.git.checkout_branch(repo.root, branch_name)

        # Get plan content and create .worker-impl/ folder
        user_output("Fetching plan content...")
        plan = ctx.plan_store.get_plan(repo.root, str(issue_number))

        user_output("Creating .worker-impl/ folder...")
        create_worker_impl_folder(
            plan_content=plan.body,
            issue_number=issue_number,
            issue_url=issue.url,
            repo_root=repo.root,
        )

        # Stage, commit, and push
        ctx.git.stage_files(repo.root, [".worker-impl"])
        ctx.git.commit(repo.root, f"Add plan for issue #{issue_number}")
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

        # Close any orphaned draft PRs for this issue
        closed_prs = _close_orphaned_draft_prs(ctx, repo.root, issue_number, pr_number)
        if closed_prs:
            user_output(
                click.style("✓", fg="green")
                + f" Closed {len(closed_prs)} orphaned draft PR(s): "
                + ", ".join(f"#{n}" for n in closed_prs)
            )

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
