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

from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.pr.abc import PrKit
from erk_shared.integrations.pr.types import (
    GraphiteEnhanceError,
    GraphiteEnhanceResult,
    GraphiteSkipped,
)


def execute_graphite_enhance(
    ops: PrKit,
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
        ops: PrKit interface providing git, github, and graphite operations
        cwd: Working directory (must be in a git repository)
        pr_number: PR number that was created/updated by core submit

    Yields:
        ProgressEvent for status updates
        CompletionEvent with:
            - GraphiteEnhanceResult on success
            - GraphiteEnhanceError on failure
            - GraphiteSkipped if enhancement was skipped (not authenticated, not tracked)
    """
    repo_root = ops.git.get_repository_root(cwd)
    branch_name = ops.git.get_current_branch(cwd)
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
    is_gt_authed, gt_username, _ = ops.graphite.check_auth_status()
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
    all_branches = ops.graphite.get_all_branches(ops.git, repo_root)
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
    yield ProgressEvent("Running gt submit to add stack metadata...")
    try:
        # gt submit is idempotent - it will update the existing PR with stack metadata
        # We don't need to restack here since the PR already exists
        ops.graphite.submit_stack(
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
        elif "conflict" in error_msg:
            yield CompletionEvent(
                GraphiteEnhanceError(
                    success=False,
                    error_type="graphite_conflict",
                    message="Merge conflicts detected during Graphite submission",
                    details={"branch": branch_name, "error": str(e)},
                )
            )
            return
        else:
            yield CompletionEvent(
                GraphiteEnhanceError(
                    success=False,
                    error_type="graphite_submit_failed",
                    message=f"Failed to enhance PR with Graphite: {e}",
                    details={"branch": branch_name, "error": str(e)},
                )
            )
            return

    yield ProgressEvent("Graphite stack metadata added", style="success")

    # Get Graphite URL
    remote_url = ops.git.get_remote_url(repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url = ops.graphite.get_graphite_url(repo_id, pr_number)

    yield CompletionEvent(
        GraphiteEnhanceResult(
            success=True,
            graphite_url=graphite_url,
            message="PR enhanced with Graphite stack metadata",
        )
    )


def should_enhance_with_graphite(
    ops: PrKit,
    cwd: Path,
) -> tuple[bool, str]:
    """Check if a PR should be enhanced with Graphite.

    This is a quick check to determine if Graphite enhancement would succeed.
    Use this for UI purposes (showing whether --no-graphite matters).

    Args:
        ops: PrKit interface
        cwd: Working directory

    Returns:
        Tuple of (should_enhance, reason):
        - (True, "tracked") - Branch is tracked and Graphite is authenticated
        - (False, "not_authenticated") - Graphite is not authenticated
        - (False, "not_tracked") - Branch is not tracked by Graphite
    """
    # Check Graphite auth
    is_authed, _, _ = ops.graphite.check_auth_status()
    if not is_authed:
        return (False, "not_authenticated")

    # Check if branch is tracked
    repo_root = ops.git.get_repository_root(cwd)
    branch_name = ops.git.get_current_branch(cwd)
    if branch_name is None:
        return (False, "no_branch")

    all_branches = ops.graphite.get_all_branches(ops.git, repo_root)
    if branch_name not in all_branches:
        return (False, "not_tracked")

    return (True, "tracked")
