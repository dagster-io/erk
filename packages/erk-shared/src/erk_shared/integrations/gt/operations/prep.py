"""Prepare branch for PR submission (squash + diff extraction, no submit).

This script handles the mechanical preparation of a branch for PR submission,
without actually submitting to GitHub. It checks for conflicts, squashes commits,
and extracts the diff for AI commit message generation.
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import PrepError, PrepResult


def execute_prep(
    ops: GtKit,
    cwd: Path,
    session_id: str,
) -> Generator[ProgressEvent | CompletionEvent[PrepResult | PrepError]]:
    """Execute prep phase: check auth, check conflicts, squash, extract diff.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).
        session_id: Claude session ID for scratch file isolation. Writes diff
            to .tmp/<session_id>/ in repo root (readable by subagents without
            permission prompts).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with PrepResult on success, or PrepError on failure
    """
    # Step 0a: Check Graphite authentication FIRST
    yield ProgressEvent("Checking Graphite authentication... (gt auth whoami)")
    gt_authenticated, gt_username, _ = ops.graphite.check_auth_status()
    if not gt_authenticated:
        gt_error: PrepError = {
            "success": False,
            "error_type": "gt_not_authenticated",
            "message": "Graphite CLI (gt) is not authenticated",
            "details": {
                "fix": "Run 'gt auth' to authenticate with Graphite",
                "authenticated": False,
            },
        }
        yield CompletionEvent(gt_error)
        return
    yield ProgressEvent(f"Authenticated as {gt_username}", style="success")

    # Step 0b: Check GitHub authentication
    yield ProgressEvent("Checking GitHub authentication... (gh auth status)")
    gh_authenticated, gh_username, _ = ops.github.check_auth_status()
    if not gh_authenticated:
        gh_error: PrepError = {
            "success": False,
            "error_type": "gh_not_authenticated",
            "message": "GitHub CLI (gh) is not authenticated",
            "details": {
                "fix": "Run 'gh auth login' to authenticate with GitHub",
                "authenticated": False,
            },
        }
        yield CompletionEvent(gh_error)
        return
    yield ProgressEvent(f"Authenticated as {gh_username}", style="success")

    # Step 1: Get current branch
    yield ProgressEvent("Getting current branch...")
    branch_name = ops.git.get_current_branch(cwd)
    if branch_name is None:
        no_branch_error: PrepError = {
            "success": False,
            "error_type": "no_branch",
            "message": "Could not determine current branch",
            "details": {"branch_name": "unknown"},
        }
        yield CompletionEvent(no_branch_error)
        return

    # Step 2: Get parent branch
    yield ProgressEvent("Getting parent branch...")
    repo_root = ops.git.get_repository_root(cwd)
    parent_branch = ops.graphite.get_parent_branch(ops.git, repo_root, branch_name)
    if parent_branch is None:
        no_parent_error: PrepError = {
            "success": False,
            "error_type": "no_parent",
            "message": f"Could not determine parent branch for: {branch_name}",
            "details": {"branch_name": branch_name},
        }
        yield CompletionEvent(no_parent_error)
        return

    # Step 3: Check for restack conflicts (CRITICAL - abort if any)
    yield ProgressEvent("Checking for restack conflicts... (gt restack --dry-run)")
    try:
        # Run restack dry-run to check for conflicts
        ops.graphite.restack(repo_root, no_interactive=True, quiet=True)
        yield ProgressEvent("No restack conflicts detected", style="success")
    except subprocess.CalledProcessError as e:
        # Check if failure was due to conflicts
        stderr = e.stderr if hasattr(e, "stderr") else ""
        combined_output = (e.stdout if hasattr(e, "stdout") else "") + stderr
        if "conflict" in combined_output.lower() or "merge conflict" in combined_output.lower():
            restack_error: PrepError = {
                "success": False,
                "error_type": "restack_conflict",
                "message": (
                    "Restack conflicts detected. Run 'gt restack' to resolve conflicts first."
                ),
                "details": {
                    "branch_name": branch_name,
                    "parent_branch": parent_branch,
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": stderr,
                },
            }
            yield CompletionEvent(restack_error)
            return
        # Generic restack check failure - proceed anyway
        yield ProgressEvent("Could not verify restack status, proceeding", style="warning")

    # Step 4: Count commits in branch
    yield ProgressEvent(f"Counting commits ahead of {parent_branch}...")
    commit_count = ops.git.count_commits_ahead(cwd, parent_branch)
    if commit_count == 0:
        no_commits_error: PrepError = {
            "success": False,
            "error_type": "no_commits",
            "message": f"No commits found in branch: {branch_name}",
            "details": {"branch_name": branch_name, "parent_branch": parent_branch},
        }
        yield CompletionEvent(no_commits_error)
        return

    # Step 5: Squash commits only if 2+ commits
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
                squash_conflict_error: PrepError = {
                    "success": False,
                    "error_type": "squash_conflict",
                    "message": "Merge conflicts detected while squashing commits",
                    "details": {
                        "branch_name": branch_name,
                        "commit_count": str(commit_count),
                        "stdout": e.stdout if hasattr(e, "stdout") else "",
                        "stderr": stderr,
                    },
                }
                yield CompletionEvent(squash_conflict_error)
                return

            # Generic squash failure
            squash_failed_error: PrepError = {
                "success": False,
                "error_type": "squash_failed",
                "message": "Failed to squash commits",
                "details": {
                    "branch_name": branch_name,
                    "commit_count": str(commit_count),
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": stderr,
                },
            }
            yield CompletionEvent(squash_failed_error)
            return

    # Step 6: Get local diff (not PR diff - we haven't submitted yet)
    yield ProgressEvent(f"Getting diff from {parent_branch}...HEAD")
    diff_content = ops.git.get_diff_to_branch(repo_root, parent_branch)
    diff_lines = len(diff_content.splitlines())
    yield ProgressEvent(f"Diff retrieved ({diff_lines} lines)", style="success")

    # Step 7: Write diff to scratch file
    from erk_shared.scratch.scratch import write_scratch_file

    diff_file = str(
        write_scratch_file(
            diff_content,
            session_id=session_id,
            suffix=".diff",
            prefix="pr-prep-diff-",
            repo_root=Path(repo_root),
        )
    )
    yield ProgressEvent(f"Diff written to {diff_file}", style="success")

    # Build success message
    message_parts = [f"Branch prepared for PR: {branch_name}"]
    if squashed:
        message_parts.append(f"Squashed {commit_count} commits into 1")
    else:
        message_parts.append("Single commit, no squash needed")
    message = "\n".join(message_parts)

    result: PrepResult = {
        "success": True,
        "diff_file": diff_file,
        "repo_root": str(repo_root),
        "current_branch": branch_name,
        "parent_branch": parent_branch,
        "commit_count": commit_count,
        "squashed": squashed,
        "message": message,
    }
    yield CompletionEvent(result)
