"""Submit issues for remote AI implementation via GitHub Actions."""

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.issues import IssueInfo
from erk_shared.github.metadata import create_submission_queued_block, render_erk_issue_event
from erk_shared.naming import derive_branch_name_with_date
from erk_shared.output.output import user_output
from erk_shared.worker_impl_folder import create_worker_impl_folder

from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PLAN_LABEL,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


@dataclass
class ValidatedIssue:
    """Issue that passed all validation checks."""

    number: int
    issue: IssueInfo
    branch_name: str
    branch_exists: bool
    pr_number: int | None


@dataclass
class SubmitResult:
    """Result of submitting a single issue."""

    issue_number: int
    issue_title: str
    issue_url: str
    pr_number: int | None
    pr_url: str | None
    workflow_run_id: str
    workflow_url: str


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


def _validate_issue_for_submit(
    ctx: ErkContext,
    repo: RepoContext,
    issue_number: int,
) -> ValidatedIssue:
    """Validate a single issue for submission.

    Raises SystemExit on validation failure.
    """
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

    # Derive branch name with date suffix
    branch_name = derive_branch_name_with_date(issue.title)

    # Check if branch already exists on remote
    branch_exists = ctx.git.branch_exists_on_remote(repo.root, "origin", branch_name)
    pr_number: int | None = None

    if branch_exists:
        # Check PR status for existing branch
        pr_status = ctx.github.get_pr_status(repo.root, branch_name, debug=False)
        if pr_status.pr_number is not None:
            pr_number = pr_status.pr_number

    return ValidatedIssue(
        number=issue_number,
        issue=issue,
        branch_name=branch_name,
        branch_exists=branch_exists,
        pr_number=pr_number,
    )


def _submit_single_issue(
    ctx: ErkContext,
    repo: RepoContext,
    validated: ValidatedIssue,
    submitted_by: str,
    original_branch: str,
    trunk_branch: str,
) -> SubmitResult:
    """Submit a single validated issue.

    Creates branch/PR if needed, triggers workflow, posts comment.
    """
    issue_number = validated.number
    issue = validated.issue
    branch_name = validated.branch_name
    pr_number = validated.pr_number

    # Display issue details
    user_output(f"Processing #{issue_number}: {click.style(issue.title, fg='yellow')}")

    if validated.branch_exists:
        if pr_number is not None:
            user_output(
                f"  PR #{pr_number} already exists for branch "
                f"'{branch_name}' - skipping branch/PR creation"
            )
        else:
            user_output(f"  Branch '{branch_name}' exists but no PR - skipping creation")
    else:
        # Create branch and initial commit
        user_output(f"  Creating branch from origin/{trunk_branch}...")

        # Fetch trunk branch
        ctx.git.fetch_branch(repo.root, "origin", trunk_branch)

        # Create and checkout new branch from trunk
        ctx.git.create_branch(repo.root, branch_name, f"origin/{trunk_branch}")
        ctx.git.checkout_branch(repo.root, branch_name)

        # Get plan content and create .worker-impl/ folder
        plan = ctx.plan_store.get_plan(repo.root, str(issue_number))
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
        user_output(click.style("  ✓", fg="green") + " Branch pushed to remote")

        # Create draft PR
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
        user_output(click.style("  ✓", fg="green") + f" Draft PR #{pr_number} created")

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
                click.style("  ✓", fg="green")
                + f" Closed {len(closed_prs)} orphaned draft PR(s): "
                + ", ".join(f"#{n}" for n in closed_prs)
            )

        # Restore local state
        ctx.git.checkout_branch(repo.root, original_branch)
        ctx.git.delete_branch(repo.root, branch_name, force=True)

        # Clean up .worker-impl/ folder from the working directory
        worker_impl_path = repo.root / ".worker-impl"
        if worker_impl_path.exists():
            shutil.rmtree(worker_impl_path)

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Trigger workflow via direct dispatch
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs={
            "issue_number": str(issue_number),
            "submitted_by": submitted_by,
            "issue_title": issue.title,
        },
    )
    user_output(click.style("  ✓", fg="green") + " Workflow triggered")

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

        ctx.issues.add_comment(repo.root, issue_number, comment_body)
    except Exception as e:
        # Log warning but don't block - workflow is already triggered
        user_output(click.style("  Warning: ", fg="yellow") + f"Failed to post queued comment: {e}")

    pr_url = _construct_pr_url(issue.url, pr_number) if pr_number is not None else None

    return SubmitResult(
        issue_number=issue_number,
        issue_title=issue.title,
        issue_url=issue.url,
        pr_number=pr_number,
        pr_url=pr_url,
        workflow_run_id=run_id,
        workflow_url=workflow_url,
    )


@click.command("submit")
@click.argument("issue_numbers", type=int, nargs=-1, required=True)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_numbers: tuple[int, ...]) -> None:
    """Submit issues for remote AI implementation via GitHub Actions.

    Creates branch and draft PR locally (for correct commit attribution),
    then triggers the dispatch-erk-queue.yml GitHub Actions workflow.

    Arguments:
        ISSUE_NUMBERS: One or more GitHub issue numbers to submit

    Example:
        erk submit 123
        erk submit 123 456 789

    Requires:
        - All issues must have erk-plan label
        - All issues must be OPEN
        - Working directory must be clean (no uncommitted changes)
    """
    # Validate GitHub CLI authentication upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Check for uncommitted changes and save current state
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

    # Get GitHub username from gh CLI (authentication already validated)
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Get trunk branch for PR creation
    trunk_branch = ctx.git.get_trunk_branch(repo.root)

    # Phase 1: Validate ALL issues upfront (atomic - fail fast before any side effects)
    user_output(f"Validating {len(issue_numbers)} issue(s)...")
    user_output("")
    validated: list[ValidatedIssue] = []
    for issue_number in issue_numbers:
        v = _validate_issue_for_submit(ctx, repo, issue_number)
        validated.append(v)
        user_output(click.style("✓", fg="green") + f" #{issue_number}: {v.issue.title}")
    user_output("")

    # Phase 2: Submit all validated issues
    user_output(f"Submitting {len(validated)} issue(s)...")
    user_output("")
    results: list[SubmitResult] = []
    for v in validated:
        result = _submit_single_issue(ctx, repo, v, submitted_by, original_branch, trunk_branch)
        results.append(result)
        user_output("")

    # Success output
    user_output(click.style("✓", fg="green") + f" {len(results)} issue(s) submitted successfully!")
    user_output("")
    user_output("Submitted issues:")
    for r in results:
        user_output(f"  • #{r.issue_number}: {r.issue_title}")
        user_output(f"    Issue: {r.issue_url}")
        if r.pr_url:
            user_output(f"    PR: {r.pr_url}")
        user_output(f"    Workflow: {r.workflow_url}")
    user_output("")
