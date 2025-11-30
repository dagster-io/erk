"""Submit issue for remote AI implementation via GitHub Actions."""

import click
from erk_shared.output.output import user_output

from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
from erk.core.services.submit_service import (
    SubmitOperationError,
    SubmitResult,
    SubmitValidationError,
    ValidatedIssue,
)


def _display_validation_result(validated: ValidatedIssue) -> None:
    """Display validation result for a single issue."""
    if validated.branch_exists:
        if validated.pr_number is not None:
            user_output(
                f"Using existing branch: {click.style(validated.branch_name, fg='cyan')} "
                f"(PR #{validated.pr_number})"
            )
        else:
            user_output(
                f"Using existing branch: {click.style(validated.branch_name, fg='cyan')} (no PR)"
            )
    else:
        user_output(f"Will create branch: {click.style(validated.branch_name, fg='cyan')}")


def _submit_single_issue(
    ctx: ErkContext,
    repo: RepoContext,
    validated: ValidatedIssue,
    submitted_by: str,
    original_branch: str,
) -> SubmitResult:
    """Submit a single validated issue and handle local state cleanup.

    This wraps the service's submit() method with:
    - Progress output messages
    - Local state restoration (checkout original branch, delete local branch)
    - Error handling with SystemExit

    Args:
        ctx: ErkContext with dependencies
        repo: Repository context
        validated: Already-validated issue
        submitted_by: GitHub username
        original_branch: Branch to restore after submission

    Returns:
        SubmitResult on success

    Raises:
        SystemExit: On operation errors
    """
    branch_name = validated.branch_name

    # Show progress
    if validated.branch_exists:
        if validated.pr_number is not None:
            user_output(
                f"PR #{validated.pr_number} already exists for branch "
                f"'{branch_name}' (state: existing)"
            )
            user_output("Skipping branch/PR creation, triggering workflow...")
        else:
            user_output(f"Branch '{branch_name}' exists but no PR. Adding placeholder commit...")
    else:
        trunk_branch = ctx.git.get_trunk_branch(repo.root)
        user_output(f"Creating branch from origin/{trunk_branch}...")

    # Call the service
    try:
        result = ctx.submit_service.submit(
            repo_root=repo.root,
            validated=validated,
            submitted_by=submitted_by,
        )
    except SubmitOperationError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    # Report closed orphan PRs if any
    if result.closed_orphan_prs:
        pr_list = ", ".join(f"#{pr}" for pr in result.closed_orphan_prs)
        user_output(f"Closed {len(result.closed_orphan_prs)} orphaned draft PR(s): {pr_list}")

    # Show success messages based on what happened
    if validated.branch_exists and validated.pr_number is None:
        # Branch existed but no PR - we added a placeholder commit
        user_output("Placeholder commit pushed")
        user_output(f"Draft PR #{result.pr_number} created")
    elif validated.branch_exists and validated.pr_number is not None:
        # Branch and PR both existed
        user_output(click.style("✓", fg="green") + f" PR #{result.pr_number} reused")
    else:
        # New branch and PR created
        user_output(click.style("✓", fg="green") + f" Draft PR #{result.pr_number} created")

    user_output(click.style("✓", fg="green") + " Workflow triggered.")
    user_output(click.style("✓", fg="green") + " Queued event comment posted")

    # Restore local state (if we modified it)
    if not validated.branch_exists or validated.pr_number is None:
        # We created or modified the branch locally, need to clean up
        user_output("Restoring local state...")
        ctx.git.checkout_branch(repo.root, original_branch)
        ctx.git.delete_branch(repo.root, branch_name, force=True)
        user_output(click.style("✓", fg="green") + " Local branch cleaned up")

    return result


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

    # Save current state
    original_branch = ctx.git.get_current_branch(repo.root)
    if original_branch is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Not on a branch (detached HEAD state). Cannot submit from here."
        )
        raise SystemExit(1)

    # Get GitHub username (authentication already validated)
    _, username, _ = ctx.github.check_auth_status()
    submitted_by = username or "unknown"

    # Phase 1: Validate ALL issues upfront (atomic - fail fast before any side effects)
    user_output(f"Validating {len(issue_numbers)} issue(s)...")
    user_output("")

    validated: list[ValidatedIssue] = []
    for issue_number in issue_numbers:
        user_output(f"Validating issue #{issue_number}...")
        try:
            validated_issue = ctx.submit_service.validate_issue(repo.root, issue_number)
        except SubmitValidationError as e:
            user_output(click.style("Error: ", fg="red") + str(e))
            raise SystemExit(1) from None

        _display_validation_result(validated_issue)
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
        result = _submit_single_issue(ctx, repo, v, submitted_by, original_branch)
        results.append(result)
        user_output("")

    # Success output
    user_output("")
    user_output(click.style("✓", fg="green") + f" {len(results)} issue(s) submitted successfully!")
    user_output("")
    user_output("Submitted issues:")
    for r in results:
        user_output(f"  • #{r.issue_number}")
        user_output(f"    PR: {r.pr_url}")
        user_output(f"    Workflow: {r.workflow_url}")
