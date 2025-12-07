"""Land a single PR from Graphite stack without affecting upstack branches.

This script safely lands a single PR from a Graphite stack by:
1. Validating the branch is exactly one level up from trunk
2. Checking an open pull request exists
3. Squash-merging the PR to trunk
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess


def execute_land_pr(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[LandPrSuccess | LandPrError]]:
    """Execute the land-pr workflow. Returns success or error result.

    Args:
        ops: GtKit operations interface.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with LandPrSuccess or LandPrError
    """
    # Step 1: Get current branch
    yield ProgressEvent("Getting current branch...")
    branch_name = ops.git.get_current_branch(cwd)
    if branch_name is None:
        branch_name = "unknown"

    # Step 2: Get parent branch
    yield ProgressEvent("Getting parent branch...")
    repo_root = ops.git.get_repository_root(cwd)
    parent = ops.graphite.get_parent_branch(ops.git, repo_root, branch_name)

    if parent is None:
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="parent_not_trunk",
                message=f"Could not determine parent branch for: {branch_name}",
                details={"current_branch": branch_name},
            )
        )
        return

    # Step 3: Validate parent is trunk
    yield ProgressEvent("Validating parent is trunk branch...")
    trunk = ops.git.detect_trunk_branch(repo_root)
    if parent != trunk:
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="parent_not_trunk",
                message=(
                    f"Branch must be exactly one level up from {trunk}\n"
                    f"Current branch: {branch_name}\n"
                    f"Parent branch: {parent} (expected: {trunk})\n\n"
                    f"Please navigate to a branch that branches directly from {trunk}."
                ),
                details={
                    "current_branch": branch_name,
                    "parent_branch": parent,
                },
            )
        )
        return

    # Step 4: Check PR exists and is open
    yield ProgressEvent("Checking PR status...")
    pr_details = ops.github.get_pr_for_branch(repo_root, branch_name)
    if pr_details is None:
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="no_pr_found",
                message=(
                    "No pull request found for this branch\n\n"
                    "Please create a PR first using: gt submit"
                ),
                details={"current_branch": branch_name},
            )
        )
        return

    pr_number = pr_details.number
    pr_state = pr_details.state
    if pr_state != "OPEN":
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="pr_not_open",
                message=(
                    f"Pull request is not open (state: {pr_state})\n\n"
                    f"This command only works with open pull requests."
                ),
                details={
                    "current_branch": branch_name,
                    "pr_number": pr_number,
                    "pr_state": pr_state,
                },
            )
        )
        return

    # Step 5: Get children branches
    yield ProgressEvent("Getting child branches...")
    children = ops.graphite.get_child_branches(ops.git, repo_root, branch_name)

    # Step 6: Get PR title and body for merge commit message (use same PRDetails object)
    yield ProgressEvent("Getting PR metadata...")

    # Merge with squash using title and body
    yield ProgressEvent(f"Merging PR #{pr_number}...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body or None
    if not ops.github.merge_pr(repo_root, pr_number, subject=subject, body=body):
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="merge_failed",
                message=(
                    f"Failed to merge PR #{pr_number}\n\nPlease resolve the issue and try again."
                ),
                details={
                    "current_branch": branch_name,
                    "pr_number": pr_number,
                },
            )
        )
        return

    yield ProgressEvent(f"PR #{pr_number} merged successfully", style="success")

    # Build success message with child info (navigation handled by CLI layer)
    if len(children) == 0:
        message = f"Successfully merged PR #{pr_number} for branch {branch_name}"
    elif len(children) == 1:
        message = (
            f"Successfully merged PR #{pr_number} for branch {branch_name}\n"
            f"Child branch: {children[0]}"
        )
    else:
        children_list = ", ".join(children)
        message = (
            f"Successfully merged PR #{pr_number} for branch {branch_name}\n"
            f"Multiple children: {children_list}"
        )

    yield CompletionEvent(
        LandPrSuccess(
            success=True,
            pr_number=pr_number,
            branch_name=branch_name,
            message=message,
        )
    )
