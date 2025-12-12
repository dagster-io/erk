"""Graphite enhancement operation for existing PRs.

This module implements the "Graphite layer" of the unified PR submission architecture.
It is called AFTER the core submission (git push + gh pr create) to optionally add
Graphite stack metadata to an existing PR.

Key insight from Graphite documentation:
- gt submit is idempotent - it will update existing PRs rather than creating new ones
- This means we can create a PR via gh pr create, then call gt submit to add stack metadata

This layer is optional and can be skipped with --no-graphite flag.
"""

from collections.abc import Generator
from pathlib import Path
from typing import NamedTuple

from erk_shared.context.context import ErkContext
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.pr.types import (
    GraphiteEnhanceError,
    GraphiteEnhanceResult,
    GraphiteSkipped,
)


class GraphiteCheckResult(NamedTuple):
    """Result of checking if Graphite enhancement should proceed.

    Attributes:
        should_enhance: Whether Graphite enhancement should proceed
        reason: The reason code - one of:
            - "tracked": Branch is tracked and Graphite is authenticated
            - "not_authenticated": Graphite is not authenticated
            - "not_tracked": Branch is not tracked by Graphite
            - "no_branch": Not on a branch (detached HEAD)
    """

    should_enhance: bool
    reason: str


class GtSubmitResult(NamedTuple):
    """Result of running gt submit.

    Attributes:
        success: Whether the submission succeeded (or was already up to date)
        error_event: If not success, the CompletionEvent to yield before returning
    """

    success: bool
    error_event: (
        CompletionEvent[GraphiteEnhanceResult | GraphiteEnhanceError | GraphiteSkipped] | None
    )


def _run_gt_submit(
    ctx: ErkContext,
    repo_root: Path,
    branch_name: str,
) -> Generator[ProgressEvent, None, GtSubmitResult]:
    """Run gt submit to add Graphite stack metadata.

    This function handles the gt submit interaction including all error cases.

    Args:
        ctx: ErkContext providing graphite operations
        repo_root: Repository root path
        branch_name: Current branch name (for error messages)

    Yields:
        ProgressEvent for status updates

    Returns:
        GtSubmitResult indicating success or containing the error event to yield
    """
    yield ProgressEvent("Running gt submit to add stack metadata...")
    try:
        # gt submit is idempotent - it will update the existing PR with stack metadata
        # We don't need to restack here since the PR already exists
        ctx.graphite.submit_stack(
            repo_root,
            publish=True,  # Mark as ready for review (not draft)
            restack=False,  # Don't restack, we just want to add metadata
            quiet=False,
        )
    except RuntimeError as e:
        error_msg = str(e).lower()

        # Check for common non-fatal cases
        if "nothing to submit" in error_msg or "no changes" in error_msg:
            # This is actually success - the PR exists and doesn't need updating
            yield ProgressEvent("PR already up to date with Graphite", style="success")
            return GtSubmitResult(success=True, error_event=None)
        if "conflict" in error_msg:
            return GtSubmitResult(
                success=False,
                error_event=CompletionEvent(
                    GraphiteEnhanceError(
                        success=False,
                        error_type="graphite_conflict",
                        message="Merge conflicts detected during Graphite submission",
                        details={"branch": branch_name, "error": str(e)},
                    )
                ),
            )
        return GtSubmitResult(
            success=False,
            error_event=CompletionEvent(
                GraphiteEnhanceError(
                    success=False,
                    error_type="graphite_submit_failed",
                    message=f"Failed to enhance PR with Graphite: {e}",
                    details={"branch": branch_name, "error": str(e)},
                )
            ),
        )

    yield ProgressEvent("Graphite stack metadata added", style="success")
    return GtSubmitResult(success=True, error_event=None)


def execute_graphite_enhance(
    ctx: ErkContext,
    cwd: Path,
    pr_number: int,
) -> Generator[
    ProgressEvent | CompletionEvent[GraphiteEnhanceResult | GraphiteEnhanceError | GraphiteSkipped]
]:
    """Enhance an existing PR with Graphite stack metadata.

    This operation is called after execute_core_submit() to optionally add
    Graphite stack metadata to the PR. The PR must already exist on GitHub.

    The operation:
    1. Checks if Graphite is authenticated
    2. Checks if the branch is tracked by Graphite
    3. Runs gt submit to add stack metadata (idempotent - won't recreate PR)

    Args:
        ctx: ErkContext providing git, github, and graphite operations
        cwd: Working directory (must be in a git repository)
        pr_number: PR number that was created/updated by core submit

    Yields:
        ProgressEvent for status updates
        CompletionEvent with:
            - GraphiteEnhanceResult on success
            - GraphiteEnhanceError on failure
            - GraphiteSkipped if enhancement was skipped (not authenticated, not tracked)
    """
    repo_root = ctx.git.get_repository_root(cwd)
    branch_name = ctx.git.get_current_branch(cwd)
    if branch_name is None:
        yield CompletionEvent(
            GraphiteSkipped(
                success=True,
                reason="no_branch",
                message="Not on a branch, skipping Graphite enhancement",
            )
        )
        return

    # Step 1: Check Graphite authentication
    yield ProgressEvent("Checking Graphite authentication...")
    is_gt_authed, gt_username, _ = ctx.graphite.check_auth_status()
    if not is_gt_authed:
        yield ProgressEvent("Graphite not authenticated, skipping enhancement", style="warning")
        yield CompletionEvent(
            GraphiteSkipped(
                success=True,
                reason="not_authenticated",
                message="Graphite is not authenticated. Run 'gt auth' to enable stack features.",
            )
        )
        return
    yield ProgressEvent(f"Graphite authenticated as {gt_username}", style="success")

    # Step 2: Check if branch is tracked by Graphite
    yield ProgressEvent("Checking if branch is tracked by Graphite...")
    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if branch_name not in all_branches:
        yield ProgressEvent("Branch not tracked by Graphite, skipping enhancement", style="warning")
        yield CompletionEvent(
            GraphiteSkipped(
                success=True,
                reason="not_tracked",
                message=(
                    f"Branch '{branch_name}' is not tracked by Graphite. "
                    "Use 'gt track' to enable stack features."
                ),
            )
        )
        return
    yield ProgressEvent("Branch is tracked by Graphite", style="success")

    # Step 3: Run gt submit to add stack metadata
    submit_result = yield from _run_gt_submit(ctx, repo_root, branch_name)
    if not submit_result.success:
        if submit_result.error_event is not None:
            yield submit_result.error_event
        return

    # Get Graphite URL
    remote_url = ctx.git.get_remote_url(repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url = ctx.graphite.get_graphite_url(repo_id, pr_number)

    yield CompletionEvent(
        GraphiteEnhanceResult(
            success=True,
            graphite_url=graphite_url,
            message="PR enhanced with Graphite stack metadata",
        )
    )


def should_enhance_with_graphite(
    ctx: ErkContext,
    cwd: Path,
) -> GraphiteCheckResult:
    """Check if a PR should be enhanced with Graphite.

    This is a quick check to determine if Graphite enhancement would succeed.
    Use this for UI purposes (showing whether --no-graphite matters).

    Args:
        ctx: ErkContext
        cwd: Working directory

    Returns:
        GraphiteCheckResult with should_enhance and reason fields:
        - (True, "tracked") - Branch is tracked and Graphite is authenticated
        - (False, "not_authenticated") - Graphite is not authenticated
        - (False, "not_tracked") - Branch is not tracked by Graphite
        - (False, "no_branch") - Not on a branch (detached HEAD)
    """
    # Check Graphite auth
    is_authed, _, _ = ctx.graphite.check_auth_status()
    if not is_authed:
        return GraphiteCheckResult(should_enhance=False, reason="not_authenticated")

    # Check if branch is tracked
    repo_root = ctx.git.get_repository_root(cwd)
    branch_name = ctx.git.get_current_branch(cwd)
    if branch_name is None:
        return GraphiteCheckResult(should_enhance=False, reason="no_branch")

    all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
    if branch_name not in all_branches:
        return GraphiteCheckResult(should_enhance=False, reason="not_tracked")

    return GraphiteCheckResult(should_enhance=True, reason="tracked")
