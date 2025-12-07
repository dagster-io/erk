"""Pre-analysis phase for submit-branch workflow.

This phase handles:
0. Check authentication (Graphite and GitHub) and commit uncommitted changes
1. Get current branch
2. Get parent branch
3. Check if parent branch has a merged PR
4. Check for merge conflicts (informational)
5. Count commits in branch (compared to parent)
6. Run gt squash to consolidate commits (only if 2+ commits)
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.github.types import PRNotFound
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import PreAnalysisError, PreAnalysisResult


def execute_pre_analysis(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[PreAnalysisResult | PreAnalysisError]]:
    """Execute the pre-analysis phase. Returns success or error result.

    Args:
        ops: GtKit operations interface.
        cwd: Working directory (repository path).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with PreAnalysisResult or PreAnalysisError
    """
    # Step 0a: Check Graphite authentication FIRST (before any git operations)
    yield ProgressEvent("Checking Graphite authentication... (gt auth whoami)")
    gt_authenticated, gt_username, _ = ops.graphite.check_auth_status()
    if not gt_authenticated:
        yield CompletionEvent(
            PreAnalysisError(
                success=False,
                error_type="gt_not_authenticated",
                message="Graphite CLI (gt) is not authenticated",
                details={
                    "fix": "Run 'gt auth' to authenticate with Graphite",
                    "authenticated": False,
                },
            )
        )
        return
    yield ProgressEvent(f"Authenticated as {gt_username}", style="success")

    # Step 0b: Check GitHub authentication (required for PR operations)
    yield ProgressEvent("Checking GitHub authentication... (gh auth status)")
    gh_authenticated, gh_username, _ = ops.github.check_auth_status()
    if not gh_authenticated:
        yield CompletionEvent(
            PreAnalysisError(
                success=False,
                error_type="gh_not_authenticated",
                message="GitHub CLI (gh) is not authenticated",
                details={
                    "fix": "Run 'gh auth login' to authenticate with GitHub",
                    "authenticated": False,
                },
            )
        )
        return
    yield ProgressEvent(f"Authenticated as {gh_username}", style="success")

    # Step 0c: Check for and commit uncommitted changes
    uncommitted_changes_committed = False
    if ops.git.has_uncommitted_changes(cwd):
        yield ProgressEvent("Staging uncommitted changes... (git add -A)")
        try:
            ops.git.add_all(cwd)
            yield ProgressEvent("Changes staged", style="success")
        except subprocess.CalledProcessError:
            yield CompletionEvent(
                PreAnalysisError(
                    success=False,
                    error_type="squash_failed",
                    message="Failed to stage uncommitted changes",
                    details={"reason": "git add failed"},
                )
            )
            return

        yield ProgressEvent("Committing staged changes... (git commit)")
        try:
            ops.git.commit(cwd, "WIP: Prepare for submission")
            uncommitted_changes_committed = True
            yield ProgressEvent("Uncommitted changes committed", style="success")
        except subprocess.CalledProcessError:
            yield CompletionEvent(
                PreAnalysisError(
                    success=False,
                    error_type="squash_failed",
                    message="Failed to commit uncommitted changes",
                    details={"reason": "git commit failed"},
                )
            )
            return

    # Step 1: Get current branch
    yield ProgressEvent("Getting current branch...")
    branch_name = ops.git.get_current_branch(cwd)

    if branch_name is None:
        yield CompletionEvent(
            PreAnalysisError(
                success=False,
                error_type="no_branch",
                message="Could not determine current branch",
                details={"branch_name": "unknown"},
            )
        )
        return

    # Step 2: Get parent branch
    yield ProgressEvent("Getting parent branch...")
    repo_root = ops.git.get_repository_root(cwd)
    parent_branch = ops.graphite.get_parent_branch(ops.git, repo_root, branch_name)

    if parent_branch is None:
        yield CompletionEvent(
            PreAnalysisError(
                success=False,
                error_type="no_parent",
                message=f"Could not determine parent branch for: {branch_name}",
                details={"branch_name": branch_name},
            )
        )
        return

    # Step 3: Check if parent branch has a merged PR (would cause gt submit to fail)
    trunk_branch = ops.git.detect_trunk_branch(repo_root)
    if parent_branch != trunk_branch:
        yield ProgressEvent(f"Checking if parent branch '{parent_branch}' is merged...")
        parent_pr = ops.github.get_pr_for_branch(repo_root, parent_branch)
        if not isinstance(parent_pr, PRNotFound) and parent_pr.state == "MERGED":
            yield CompletionEvent(
                PreAnalysisError(
                    success=False,
                    error_type="parent_merged",
                    message=(
                        f"Parent branch '{parent_branch}' has been merged. "
                        "Run 'gt sync' to update your stack."
                    ),
                    details={
                        "parent_branch": parent_branch,
                        "pr_number": str(parent_pr.number),
                        "fix": "Run 'gt sync' to reparent this branch to trunk",
                    },
                )
            )
            return
        yield ProgressEvent("Parent branch not merged", style="success")

    # Step 4: Check for merge conflicts (informational only, does not block)
    # First try GitHub API if PR exists (most accurate), then fallback to local git merge-tree
    pr_details = ops.github.get_pr_for_branch(repo_root, branch_name)

    # Track conflict info (will be included in success result)
    has_conflicts = False
    conflict_details: dict[str, str] | None = None

    if not isinstance(pr_details, PRNotFound):
        pr_number = pr_details.number
        # PR exists - check mergeability (use same PRDetails object)
        mergeable = pr_details.mergeable
        merge_state = pr_details.merge_state_status

        if mergeable == "CONFLICTING":
            has_conflicts = True
            conflict_details = {
                "pr_number": str(pr_number),
                "parent_branch": parent_branch,
                "merge_state": merge_state,
                "detection_method": "github_api",
            }
            yield ProgressEvent(
                f"PR #{pr_number} has merge conflicts with {parent_branch}",
                style="warning",
            )

        # UNKNOWN status: proceed with warning (GitHub hasn't computed yet)
        elif mergeable == "UNKNOWN":
            yield ProgressEvent(
                "PR mergeability status is UNKNOWN, proceeding anyway",
                style="warning",
            )

    else:
        # No PR yet - fallback to local git merge-tree check
        if ops.git.check_merge_conflicts(cwd, parent_branch, branch_name):
            has_conflicts = True
            conflict_details = {
                "parent_branch": parent_branch,
                "detection_method": "git_merge_tree",
            }
            yield ProgressEvent(
                f"Branch has local merge conflicts with {parent_branch}",
                style="warning",
            )

    # Step 5: Count commits in branch
    yield ProgressEvent(f"Counting commits ahead of {parent_branch}...")
    commit_count = ops.git.count_commits_ahead(cwd, parent_branch)

    if commit_count == 0:
        yield CompletionEvent(
            PreAnalysisError(
                success=False,
                error_type="no_commits",
                message=f"No commits found in branch: {branch_name}",
                details={"branch_name": branch_name, "parent_branch": parent_branch},
            )
        )
        return

    # Step 6: Run gt squash only if 2+ commits
    squashed = False
    if commit_count >= 2:
        yield ProgressEvent(f"Squashing {commit_count} commits... (gt squash --no-edit)")
        try:
            ops.graphite.squash_branch(repo_root, quiet=False)
            squashed = True
            yield ProgressEvent(f"Squashed {commit_count} commits into 1", style="success")
        except subprocess.CalledProcessError as e:
            # Check if failure was due to merge conflict
            stderr = e.stderr if hasattr(e, "stderr") else ""
            combined_output = (e.stdout if hasattr(e, "stdout") else "") + stderr
            if "conflict" in combined_output.lower() or "merge conflict" in combined_output.lower():
                yield CompletionEvent(
                    PreAnalysisError(
                        success=False,
                        error_type="squash_conflict",
                        message="Merge conflicts detected while squashing commits",
                        details={
                            "branch_name": branch_name,
                            "commit_count": str(commit_count),
                            "stdout": e.stdout if hasattr(e, "stdout") else "",
                            "stderr": stderr,
                        },
                    )
                )
                return

            # Generic squash failure (not conflict-related)
            yield CompletionEvent(
                PreAnalysisError(
                    success=False,
                    error_type="squash_failed",
                    message="Failed to squash commits",
                    details={
                        "branch_name": branch_name,
                        "commit_count": str(commit_count),
                        "stdout": e.stdout if hasattr(e, "stdout") else "",
                        "stderr": stderr,
                    },
                )
            )
            return

    # Build success message
    message_parts = [f"Pre-analysis complete for branch: {branch_name}"]

    if uncommitted_changes_committed:
        message_parts.append("Committed uncommitted changes")

    if squashed:
        message_parts.append(f"Squashed {commit_count} commits into 1")
    else:
        message_parts.append("Single commit, no squash needed")

    message = "\n".join(message_parts)

    yield ProgressEvent("Pre-analysis complete", style="success")
    yield CompletionEvent(
        PreAnalysisResult(
            success=True,
            branch_name=branch_name,
            parent_branch=parent_branch,
            commit_count=commit_count,
            squashed=squashed,
            uncommitted_changes_committed=uncommitted_changes_committed,
            message=message,
            has_conflicts=has_conflicts,
            conflict_details=conflict_details,
        )
    )
