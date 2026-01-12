"""Land a single PR from worktree stack without affecting upstack branches.

This script safely lands a single PR from a worktree stack by:
1. Validating the branch is exactly one level up from trunk
2. Checking an open pull request exists
3. Squash-merging the PR to trunk
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.types import LandPrError, LandPrSuccess
from erk_shared.github.types import PRNotFound


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
                error_type="parent-not-trunk",
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
                error_type="parent-not-trunk",
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
    if isinstance(pr_details, PRNotFound):
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="no-pr-found",
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
                error_type="pr-not-open",
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

    # Step 4.5: Validate PR base branch matches trunk
    # GitHub PR base may diverge from local Graphite metadata (e.g., after landing parent)
    yield ProgressEvent("Validating PR base branch...")
    pr_base = ops.github.get_pr_base_branch(repo_root, pr_number)
    if pr_base is None:
        # gh CLI failed unexpectedly (we just successfully queried the PR above)
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="github-api-error",
                message=(
                    f"Failed to get base branch for PR #{pr_number}.\n\nCheck: gh auth status"
                ),
                details={
                    "current_branch": branch_name,
                    "pr_number": pr_number,
                },
            )
        )
        return
    if pr_base != trunk:
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="pr-base-mismatch",
                message=(
                    f"PR #{pr_number} targets '{pr_base}' but should target '{trunk}'.\n\n"
                    f"The GitHub PR's base branch has diverged from your local stack.\n"
                    f"Run: gt restack && gt submit\n"
                    f"Then retry: erk pr land"
                ),
                details={
                    "current_branch": branch_name,
                    "pr_number": pr_number,
                    "pr_base": pr_base,
                    "expected_base": trunk,
                },
            )
        )
        return

    # Step 5: Get children branches
    yield ProgressEvent("Getting child branches...")
    children = ops.graphite.get_child_branches(ops.git, repo_root, branch_name)

    # Update upstack PR base branches BEFORE merging
    # This prevents GitHub from auto-closing PRs when "Automatically delete head branches"
    # is enabled and GitHub deletes the base branch immediately after merge
    if children:
        yield ProgressEvent("Updating upstack PR base branches...")
        for child_branch in children:
            child_pr = ops.github.get_pr_for_branch(repo_root, child_branch)
            if not isinstance(child_pr, PRNotFound) and child_pr.state == "OPEN":
                ops.github.update_pr_base_branch(repo_root, child_pr.number, trunk)

    # Step 6: Get PR title and body for merge commit message (use same PRDetails object)
    yield ProgressEvent("Getting PR metadata...")

    # Merge with squash using title and body
    yield ProgressEvent(f"Merging PR #{pr_number}...")
    subject = f"{pr_details.title} (#{pr_number})" if pr_details.title else None
    body = pr_details.body or None
    merge_result = ops.github.merge_pr(repo_root, pr_number, subject=subject, body=body)
    if merge_result is not True:
        error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
        yield CompletionEvent(
            LandPrError(
                success=False,
                error_type="merge-failed",
                message=f"Failed to merge PR #{pr_number}\n\n{error_detail}",
                details={
                    "current_branch": branch_name,
                    "pr_number": pr_number,
                },
            )
        )
        return

    yield ProgressEvent(f"PR #{pr_number} merged successfully", style="success")

    # Delete remote branch after successful merge
    # Note: We do this separately instead of using `gh pr merge --delete-branch`
    # because --delete-branch attempts local branch operations that fail from worktrees
    yield ProgressEvent(f"Deleting remote branch '{branch_name}'...")
    ops.github.delete_remote_branch(repo_root, branch_name)

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
