"""Submit issue for remote AI implementation via GitHub Actions."""

import logging
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import click

from erk.cli.constants import (
    DISPATCH_WORKFLOW_METADATA_NAME,
    DISPATCH_WORKFLOW_NAME,
    ERK_PLAN_LABEL,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.gt.operations.finalize import ERK_SKIP_EXTRACTION_LABEL
from erk_shared.github.issues import IssueInfo
from erk_shared.github.metadata import (
    create_submission_queued_block,
    find_metadata_block,
    render_erk_issue_event,
    update_plan_header_dispatch,
)
from erk_shared.github.parsing import (
    construct_pr_url,
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import PRNotFound
from erk_shared.naming import (
    format_branch_timestamp_suffix,
    sanitize_worktree_name,
)
from erk_shared.output.output import user_output
from erk_shared.worker_impl_folder import create_worker_impl_folder

logger = logging.getLogger(__name__)


def _format_issue_ref(issue_number: int, plans_repo: str | None) -> str:
    """Format issue reference for PR body.

    Args:
        issue_number: The issue number
        plans_repo: Target repo in "owner/repo" format, or None for same repo

    Returns:
        "#N" for same-repo, "owner/repo#N" for cross-repo
    """
    if plans_repo is None:
        return f"#{issue_number}"
    return f"{plans_repo}#{issue_number}"


@contextmanager
def branch_rollback(ctx: "ErkContext", repo_root: Path, original_branch: str) -> Iterator[None]:
    """Context manager that restores original branch on exception.

    On success, does nothing (caller handles cleanup).
    On exception, checks out original_branch and re-raises.
    """
    try:
        yield
    except Exception:
        user_output(
            click.style("Error: ", fg="red") + "Operation failed, restoring original branch..."
        )
        ctx.git.checkout_branch(repo_root, original_branch)
        raise


def is_issue_extraction_plan(issue_body: str) -> bool:
    """Check if an issue is an extraction plan by examining its plan-header metadata.

    Args:
        issue_body: The full issue body text

    Returns:
        True if the issue has plan_type: "extraction" in its plan-header block,
        False otherwise (including if no plan-header block exists)
    """
    block = find_metadata_block(issue_body, "plan-header")

    if block is None:
        return False

    plan_type = block.data.get("plan_type")
    return plan_type == "extraction"


def load_workflow_config(repo_root: Path, workflow_name: str) -> dict[str, str]:
    """Load workflow config from .erk/config.toml [workflows.<name>] section.

    Args:
        repo_root: Repository root path
        workflow_name: Workflow filename (with or without .yml/.yaml extension).
            Only the basename is used for config lookup.

    Returns:
        Dict of string key-value pairs for workflow inputs.
        Returns empty dict if config file or section doesn't exist.

    Example:
        For workflow_name="erk-impl.yml", reads from:
        .erk/config.toml -> [workflows.erk-impl] section
    """
    config_path = repo_root / ".erk" / "config.toml"

    if not config_path.exists():
        return {}

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Extract basename and strip .yml/.yaml extension
    basename = Path(workflow_name).name
    config_name = basename.removesuffix(".yml").removesuffix(".yaml")

    # Get [workflows.<name>] section
    workflows_section = data.get("workflows", {})
    workflow_config = workflows_section.get(config_name, {})

    # Convert all values to strings (workflow inputs are always strings)
    return {k: str(v) for k, v in workflow_config.items()}


@dataclass(frozen=True)
class ValidatedIssue:
    """Issue that passed all validation checks."""

    number: int
    issue: IssueInfo
    branch_name: str
    branch_exists: bool
    pr_number: int | None
    is_extraction_origin: bool


@dataclass(frozen=True)
class SubmitResult:
    """Result of submitting a single issue."""

    issue_number: int
    issue_title: str
    issue_url: str
    pr_number: int | None
    pr_url: str | None
    workflow_run_id: str
    workflow_url: str


def _build_workflow_run_url(issue_url: str, run_id: str) -> str:
    """Construct GitHub Actions workflow run URL from issue URL and run ID.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        run_id: Workflow run ID

    Returns:
        Workflow run URL (e.g., https://github.com/owner/repo/actions/runs/1234567890)
    """
    owner_repo = extract_owner_repo_from_github_url(issue_url)
    if owner_repo is not None:
        owner, repo = owner_repo
        return construct_workflow_run_url(owner, repo, run_id)
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


def _build_pr_url(issue_url: str, pr_number: int) -> str:
    """Construct GitHub PR URL from issue URL and PR number.

    Args:
        issue_url: GitHub issue URL (e.g., https://github.com/owner/repo/issues/123)
        pr_number: PR number

    Returns:
        PR URL (e.g., https://github.com/owner/repo/pull/456)
    """
    owner_repo = extract_owner_repo_from_github_url(issue_url)
    if owner_repo is not None:
        owner, repo = owner_repo
        return construct_pr_url(owner, repo, pr_number)
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
    linked_prs = ctx.issues.get_prs_referencing_issue(repo_root, issue_number)

    closed_prs: list[int] = []
    for pr in linked_prs:
        # Close orphaned drafts: draft PRs that are OPEN and not the one we just created
        # Any draft PR linked to an erk-plan issue is fair game to close
        if pr.is_draft and pr.state == "OPEN" and pr.number != keep_pr_number:
            ctx.github.close_pr(repo_root, pr.number)
            closed_prs.append(pr.number)

    return closed_prs


def _validate_issue_for_submit(
    ctx: ErkContext,
    repo: RepoContext,
    issue_number: int,
    base_branch: str,
) -> ValidatedIssue:
    """Validate a single issue for submission.

    Fetches the issue, validates constraints, derives branch name, and checks
    if branch/PR already exist.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        issue_number: GitHub issue number to validate
        base_branch: Base branch for PR (trunk or custom feature branch)

    Raises:
        SystemExit: If issue doesn't exist, missing label, or closed.
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
            "To create a plan, use Plan Mode then /erk:plan-save"
        )
        raise SystemExit(1)

    # Validate: must be OPEN
    if issue.state != "OPEN":
        user_output(
            click.style("Error: ", fg="red") + f"Issue #{issue_number} is {issue.state}\n\n"
            "Cannot submit closed issues for automated implementation."
        )
        raise SystemExit(1)

    # Use provided base_branch instead of detecting trunk
    logger.debug("base_branch=%s", base_branch)

    # Compute branch name: P prefix + issue number + sanitized title + timestamp
    # Apply P prefix AFTER sanitization since sanitize_worktree_name lowercases input
    # Truncate total to 31 chars before adding timestamp suffix
    prefix = f"P{issue_number}-"
    sanitized_title = sanitize_worktree_name(issue.title)
    base_branch_name = (prefix + sanitized_title)[:31].rstrip("-")
    logger.debug("base_branch_name=%s", base_branch_name)
    timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
    logger.debug("timestamp_suffix=%s", timestamp_suffix)
    branch_name = base_branch_name + timestamp_suffix
    logger.debug("branch_name=%s", branch_name)
    user_output(f"Computed branch: {click.style(branch_name, fg='cyan')}")

    # Check if branch already exists on remote and has a PR
    branch_exists = ctx.git.branch_exists_on_remote(repo.root, "origin", branch_name)
    logger.debug("branch_exists_on_remote(%s)=%s", branch_name, branch_exists)

    pr_number: int | None = None
    if branch_exists:
        pr_details = ctx.github.get_pr_for_branch(repo.root, branch_name)
        if not isinstance(pr_details, PRNotFound):
            pr_number = pr_details.number

    # Check if this issue is an extraction plan
    is_extraction_origin = is_issue_extraction_plan(issue.body)

    return ValidatedIssue(
        number=issue_number,
        issue=issue,
        branch_name=branch_name,
        branch_exists=branch_exists,
        pr_number=pr_number,
        is_extraction_origin=is_extraction_origin,
    )


def _create_branch_and_pr(
    ctx: ErkContext,
    repo: RepoContext,
    validated: ValidatedIssue,
    branch_name: str,
    base_branch: str,
    submitted_by: str,
    original_branch: str,
) -> int:
    """Create branch, commit, push, and create draft PR.

    This function is called within the branch_rollback context manager.
    On any exception, the context manager will restore the original branch.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        validated: Validated issue information
        branch_name: Name of branch to create
        base_branch: Base branch for PR
        submitted_by: GitHub username of submitter
        original_branch: Original branch name (for cleanup on success)

    Returns:
        PR number of the created draft PR.
    """
    issue = validated.issue
    issue_number = validated.number

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
        prompt_executor=ctx.prompt_executor,
    )

    # Stage, commit, and push
    ctx.git.stage_files(repo.root, [".worker-impl"])
    ctx.git.commit(repo.root, f"Add plan for issue #{issue_number}")
    ctx.git.push_to_remote(repo.root, "origin", branch_name, set_upstream=True)
    user_output(click.style("✓", fg="green") + " Branch pushed to remote")

    # Create draft PR
    # IMPORTANT: "Closes owner/repo#N" (cross-repo) or "Closes #N" (same-repo)
    # MUST be in the initial body passed to create_pr(), NOT added via update.
    # GitHub's willCloseTarget API field is set at PR creation time and is NOT
    # updated when the body is edited afterward.
    user_output("Creating draft PR...")
    plans_repo = ctx.local_config.plans_repo if ctx.local_config else None
    issue_ref = _format_issue_ref(issue_number, plans_repo)
    pr_body = (
        f"**Author:** @{submitted_by}\n"
        f"**Plan:** {issue_ref}\n\n"
        f"**Status:** Queued for implementation\n\n"
        f"This PR will be marked ready for review after implementation completes.\n\n"
        f"---\n\n"
        f"Closes {issue_ref}"
    )
    pr_title = _strip_plan_markers(issue.title)
    pr_number = ctx.github.create_pr(
        repo_root=repo.root,
        branch=branch_name,
        title=pr_title,
        body=pr_body,
        base=base_branch,
        draft=True,
    )
    user_output(click.style("✓", fg="green") + f" Draft PR #{pr_number} created")

    # Update PR body with checkout command footer
    footer = build_pr_body_footer(
        pr_number=pr_number, issue_number=issue_number, plans_repo=plans_repo
    )
    ctx.github.update_pr_body(repo.root, pr_number, pr_body + footer)

    # Add extraction skip label if this is an extraction plan
    if validated.is_extraction_origin:
        ctx.github.add_label_to_pr(repo.root, pr_number, ERK_SKIP_EXTRACTION_LABEL)

    # Close any orphaned draft PRs for this issue
    closed_prs = _close_orphaned_draft_prs(ctx, repo.root, issue_number, pr_number)
    if closed_prs:
        user_output(
            click.style("✓", fg="green")
            + f" Closed {len(closed_prs)} orphaned draft PR(s): "
            + ", ".join(f"#{n}" for n in closed_prs)
        )

    # Restore local state
    user_output("Restoring local state...")
    ctx.git.checkout_branch(repo.root, original_branch)
    ctx.git.delete_branch(repo.root, branch_name, force=True)
    user_output(click.style("✓", fg="green") + " Local branch cleaned up")

    return pr_number


def _submit_single_issue(
    ctx: ErkContext,
    repo: RepoContext,
    validated: ValidatedIssue,
    submitted_by: str,
    original_branch: str,
    base_branch: str,
) -> SubmitResult:
    """Submit a single validated issue for implementation.

    Creates branch/PR if needed and triggers workflow.

    Args:
        ctx: ErkContext with git operations
        repo: Repository context
        validated: Validated issue information
        submitted_by: GitHub username of submitter
        original_branch: Original branch name (to restore after)
        base_branch: Base branch for PR (trunk or custom feature branch)

    Returns:
        SubmitResult with URLs and identifiers.
    """
    issue = validated.issue
    issue_number = validated.number
    branch_name = validated.branch_name
    branch_exists = validated.branch_exists
    pr_number = validated.pr_number

    if branch_exists:
        if pr_number is not None:
            user_output(
                f"PR #{pr_number} already exists for branch '{branch_name}' (state: existing)"
            )
            user_output("Skipping branch/PR creation, triggering workflow...")
        else:
            # Branch exists but no PR - need to add a commit for PR creation
            user_output(f"Branch '{branch_name}' exists but no PR. Adding placeholder commit...")

            # Fetch and checkout the remote branch locally
            ctx.git.fetch_branch(repo.root, "origin", branch_name)

            # Only create tracking branch if it doesn't exist locally (LBYL)
            local_branches = ctx.git.list_local_branches(repo.root)
            if branch_name not in local_branches:
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
            # IMPORTANT: "Closes owner/repo#N" (cross-repo) or "Closes #N" (same-repo)
            # MUST be in the initial body passed to create_pr(), NOT added via update.
            # GitHub's willCloseTarget API field is set at PR creation time and is NOT
            # updated when the body is edited afterward.
            plans_repo = ctx.local_config.plans_repo if ctx.local_config else None
            issue_ref = _format_issue_ref(issue_number, plans_repo)
            pr_body = (
                f"**Author:** @{submitted_by}\n"
                f"**Plan:** {issue_ref}\n\n"
                f"**Status:** Queued for implementation\n\n"
                f"This PR will be marked ready for review after implementation completes.\n\n"
                f"---\n\n"
                f"Closes {issue_ref}"
            )
            pr_title = _strip_plan_markers(issue.title)
            pr_number = ctx.github.create_pr(
                repo_root=repo.root,
                branch=branch_name,
                title=pr_title,
                body=pr_body,
                base=base_branch,
                draft=True,
            )
            user_output(click.style("✓", fg="green") + f" Draft PR #{pr_number} created")

            # Update PR body with checkout command footer
            footer = build_pr_body_footer(
                pr_number=pr_number, issue_number=issue_number, plans_repo=plans_repo
            )
            ctx.github.update_pr_body(repo.root, pr_number, pr_body + footer)

            # Add extraction skip label if this is an extraction plan
            if validated.is_extraction_origin:
                ctx.github.add_label_to_pr(repo.root, pr_number, ERK_SKIP_EXTRACTION_LABEL)

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
        # Create branch and initial commit
        user_output(f"Creating branch from origin/{base_branch}...")

        # Fetch base branch
        ctx.git.fetch_branch(repo.root, "origin", base_branch)

        # Create and checkout new branch from base
        ctx.git.create_branch(repo.root, branch_name, f"origin/{base_branch}")
        user_output(f"Created branch: {click.style(branch_name, fg='cyan')}")

        # Use context manager to restore original branch on failure
        with branch_rollback(ctx, repo.root, original_branch):
            pr_number = _create_branch_and_pr(
                ctx=ctx,
                repo=repo,
                validated=validated,
                branch_name=branch_name,
                base_branch=base_branch,
                submitted_by=submitted_by,
                original_branch=original_branch,
            )

    # Gather submission metadata
    queued_at = datetime.now(UTC).isoformat()

    # Validate pr_number is set before workflow dispatch
    if pr_number is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Failed to create or find PR. Cannot trigger workflow."
        )
        raise SystemExit(1)

    # Load workflow-specific config
    workflow_config = load_workflow_config(repo.root, DISPATCH_WORKFLOW_NAME)

    # Trigger workflow via direct dispatch
    user_output("")
    user_output(f"Triggering workflow: {click.style(DISPATCH_WORKFLOW_NAME, fg='cyan')}")
    user_output(f"  Display name: {DISPATCH_WORKFLOW_METADATA_NAME}")

    # Build inputs dict, merging workflow config
    inputs = {
        # Required inputs (always passed)
        "issue_number": str(issue_number),
        "submitted_by": submitted_by,
        "issue_title": issue.title,
        "branch_name": branch_name,
        "pr_number": str(pr_number),
        # Config-based inputs (from .erk/workflows/)
        **workflow_config,
    }

    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow=DISPATCH_WORKFLOW_NAME,
        inputs=inputs,
    )
    user_output(click.style("✓", fg="green") + " Workflow triggered.")

    # Write dispatch metadata synchronously to fix race condition with erk dash
    # This ensures the issue body has the run info before we return to the user
    node_id = ctx.github.get_workflow_run_node_id(repo.root, run_id)
    if node_id is not None:
        try:
            # Fetch fresh issue body and update dispatch metadata
            fresh_issue = ctx.issues.get_issue(repo.root, issue_number)
            updated_body = update_plan_header_dispatch(
                issue_body=fresh_issue.body,
                run_id=run_id,
                node_id=node_id,
                dispatched_at=queued_at,
            )
            ctx.issues.update_issue_body(repo.root, issue_number, updated_body)
            user_output(click.style("✓", fg="green") + " Dispatch metadata written to issue")
        except Exception as e:
            # Log warning but don't block - workflow is already triggered
            user_output(
                click.style("Warning: ", fg="yellow") + f"Failed to update dispatch metadata: {e}"
            )
    else:
        user_output(click.style("Warning: ", fg="yellow") + "Could not fetch workflow run node_id")

    validation_results = {
        "issue_is_open": True,
        "has_erk_plan_label": True,
    }

    # Create and post queued event comment
    workflow_url = _build_workflow_run_url(issue.url, run_id)
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

    pr_url = _build_pr_url(issue.url, pr_number) if pr_number else None

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
@click.option(
    "--base",
    type=str,
    default=None,
    help="Base branch for PR (defaults to current branch).",
)
@click.pass_obj
def submit_cmd(ctx: ErkContext, issue_numbers: tuple[int, ...], base: str | None) -> None:
    """Submit issues for remote AI implementation via GitHub Actions.

    Creates branch and draft PR locally (for correct commit attribution),
    then triggers the dispatch-erk-queue.yml GitHub Actions workflow.

    Arguments:
        ISSUE_NUMBERS: One or more GitHub issue numbers to submit

    Example:
        erk submit 123
        erk submit 123 456 789
        erk submit 123 --base master

    Requires:
        - All issues must have erk-plan label
        - All issues must be OPEN
        - Working directory must be clean (no uncommitted changes)
    """
    # Validate GitHub CLI prerequisites upfront (LBYL)
    Ensure.gh_authenticated(ctx)

    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Save current state (needed for both default base and restoration)
    original_branch = ctx.git.get_current_branch(repo.root)
    if original_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Not on a branch (detached HEAD state). Cannot submit from here."
        )
        raise SystemExit(1)

    # Validate base branch if provided, otherwise default to current branch (LBYL)
    if base is not None:
        if not ctx.git.branch_exists_on_remote(repo.root, "origin", base):
            user_output(
                click.style("Error: ", fg="red") + f"Base branch '{base}' does not exist on remote"
            )
            raise SystemExit(1)
        target_branch = base
    else:
        target_branch = original_branch

    # Get GitHub username (authentication already validated)
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Phase 1: Validate ALL issues upfront (atomic - fail fast before any side effects)
    user_output(f"Validating {len(issue_numbers)} issue(s)...")
    user_output("")

    validated: list[ValidatedIssue] = []
    for issue_number in issue_numbers:
        user_output(f"Validating issue #{issue_number}...")
        validated_issue = _validate_issue_for_submit(ctx, repo, issue_number, target_branch)
        validated.append(validated_issue)

    user_output("")
    user_output(click.style("✓", fg="green") + f" All {len(validated)} issue(s) validated")
    user_output("")

    # Display validated issues
    for v in validated:
        user_output(f"  #{v.number}: {click.style(v.issue.title, fg='yellow')}")
    user_output("")

    # Phase 2: Submit all validated issues
    results: list[SubmitResult] = []
    for i, v in enumerate(validated):
        if len(validated) > 1:
            user_output(f"--- Submitting issue {i + 1}/{len(validated)}: #{v.number} ---")
        else:
            user_output(f"Submitting issue #{v.number}...")
        user_output("")
        result = _submit_single_issue(ctx, repo, v, submitted_by, original_branch, target_branch)
        results.append(result)
        user_output("")

    # Success output
    user_output("")
    user_output(click.style("✓", fg="green") + f" {len(results)} issue(s) submitted successfully!")
    user_output("")
    user_output("Submitted issues:")
    for r in results:
        user_output(f"  • #{r.issue_number}: {r.issue_title}")
        user_output(f"    Issue: {r.issue_url}")
        if r.pr_url:
            user_output(f"    PR: {r.pr_url}")
        user_output(f"    Workflow: {r.workflow_url}")
