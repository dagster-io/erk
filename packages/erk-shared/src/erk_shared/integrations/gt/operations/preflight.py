"""Preflight phase for submit-branch workflow.

This phase combines pre-analysis + submit + diff extraction into a single phase
for use by the slash command orchestration.
"""

import subprocess
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import NamedTuple

from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId, PRNotFound
from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.operations.pre_analysis import execute_pre_analysis
from erk_shared.integrations.gt.types import (
    PostAnalysisError,
    PreAnalysisError,
    PreflightResult,
)


class _SubmitResult(NamedTuple):
    """Result from running submit_stack in background thread."""

    success: bool
    error: RuntimeError | None = None


def _execute_submit_only(
    ops: GtKit,
    cwd: Path,
) -> Generator[ProgressEvent | CompletionEvent[tuple[int, str, str, str] | PostAnalysisError]]:
    """Submit branch and wait for PR info, without modifying commit message.

    Yields:
        ProgressEvent for status updates
        CompletionEvent with tuple of (pr_number, pr_url, graphite_url, branch_name) on success
        CompletionEvent with PostAnalysisError on failure
    """
    branch_name = ops.git.get_current_branch(cwd) or "unknown"

    # Phase 1: Restack the stack
    yield ProgressEvent("Rebasing stack... (gt restack)")
    restack_start = time.time()
    try:
        repo_root = ops.git.get_repository_root(cwd)
        ops.graphite.restack(repo_root, no_interactive=True, quiet=False)
    except subprocess.CalledProcessError as e:
        # Check for restack errors (conflicts, etc.)
        has_output = hasattr(e, "stdout") and hasattr(e, "stderr")
        combined_output = e.stdout + e.stderr if has_output else str(e)
        combined_lower = combined_output.lower()

        # Check for merge conflicts
        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            yield CompletionEvent(
                PostAnalysisError(
                    success=False,
                    error_type="submit_conflict",
                    message="Merge conflicts detected during stack rebase",
                    details={
                        "branch_name": branch_name,
                        "stdout": e.stdout if hasattr(e, "stdout") else "",
                        "stderr": e.stderr if hasattr(e, "stderr") else str(e),
                    },
                )
            )
            return

        # Generic restack failure
        yield CompletionEvent(
            PostAnalysisError(
                success=False,
                error_type="submit_failed",
                message="Failed to restack branch",
                details={
                    "branch_name": branch_name,
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": e.stderr if hasattr(e, "stderr") else str(e),
                },
            )
        )
        return

    restack_elapsed = int(time.time() - restack_start)
    yield ProgressEvent(f"Stack rebased ({restack_elapsed}s)", style="success")

    # Phase 2: Submit to GitHub
    yield ProgressEvent("Pushing branches and creating PR... (gt submit --publish)")

    # Run submit (without progress tracking for now since we can't yield from nested function)
    submit_result: _SubmitResult | None = None

    def run_submit():
        nonlocal submit_result
        try:
            ops.graphite.submit_stack(repo_root, publish=True, restack=False, quiet=False)
            submit_result = _SubmitResult(success=True)
        except RuntimeError as e:
            submit_result = _SubmitResult(success=False, error=e)

    thread = threading.Thread(target=run_submit, daemon=True)
    thread.start()

    # Wait with progress updates
    start_time = time.time()
    progress_markers = [(10, "Pushing to remote"), (20, "Creating PR"), (30, "Finalizing")]
    marker_idx = 0

    while thread.is_alive():
        elapsed = time.time() - start_time
        if marker_idx < len(progress_markers):
            threshold, description = progress_markers[marker_idx]
            if elapsed >= threshold:
                yield ProgressEvent(f"[{int(elapsed)}s] {description}")
                marker_idx += 1
        thread.join(timeout=1.0)

    if submit_result is None:
        submit_result = _SubmitResult(success=False)

    if not submit_result.success:
        # Extract error message for categorization
        error_message = str(submit_result.error) if submit_result.error else ""
        error_lower = error_message.lower()

        # Check for empty parent branch
        nothing_to_submit = "Nothing to submit!" in error_message
        no_changes = "does not introduce any changes" in error_message
        if nothing_to_submit or no_changes:
            yield CompletionEvent(
                PostAnalysisError(
                    success=False,
                    error_type="submit_empty_parent",
                    message=(
                        "Stack contains an empty parent branch that was already merged. "
                        "Run 'gt track --parent <trunk>' to reparent this branch, "
                        "then 'gt restack'."
                    ),
                    details={
                        "branch_name": branch_name,
                        "error": error_message,
                    },
                )
            )
            return

        if "conflict" in error_lower or "merge conflict" in error_lower:
            yield CompletionEvent(
                PostAnalysisError(
                    success=False,
                    error_type="submit_conflict",
                    message="Merge conflicts detected during branch submission",
                    details={
                        "branch_name": branch_name,
                        "error": error_message,
                    },
                )
            )
            return

        if "merged but the merged commits are not contained" in error_message:
            yield CompletionEvent(
                PostAnalysisError(
                    success=False,
                    error_type="submit_merged_parent",
                    message="Parent branches have been merged but are not in main trunk",
                    details={
                        "branch_name": branch_name,
                        "error": error_message,
                    },
                )
            )
            return

        if "updated remotely" in error_lower or "must sync" in error_lower:
            yield CompletionEvent(
                PostAnalysisError(
                    success=False,
                    error_type="submit_diverged",
                    message="Branch has diverged from remote - manual resolution required",
                    details={
                        "branch_name": branch_name,
                        "error": error_message,
                    },
                )
            )
            return

        if "timed out after 120 seconds" in error_message:
            yield CompletionEvent(
                PostAnalysisError(
                    success=False,
                    error_type="submit_timeout",
                    message=(
                        "gt submit timed out after 120 seconds. "
                        "Check network connectivity and try again."
                    ),
                    details={
                        "branch_name": branch_name,
                        "error": error_message,
                    },
                )
            )
            return

        yield CompletionEvent(
            PostAnalysisError(
                success=False,
                error_type="submit_failed",
                message="Failed to submit branch with gt submit",
                details={
                    "branch_name": branch_name,
                    "error": error_message,
                },
            )
        )
        return

    yield ProgressEvent("Branch submitted to Graphite", style="success")

    # Wait for PR info
    max_retries = 5
    retry_delays = [0.5, 1.0, 2.0, 4.0, 8.0]
    repo_root = ops.git.get_repository_root(cwd)

    yield ProgressEvent("Waiting for PR info from GitHub API... (gh pr view)")

    pr_details = None
    for attempt in range(max_retries):
        if attempt > 0:
            yield ProgressEvent(f"Attempt {attempt + 1}/{max_retries}...")
        pr_result = ops.github.get_pr_for_branch(repo_root, branch_name)
        if not isinstance(pr_result, PRNotFound):
            pr_details = pr_result
            yield ProgressEvent(f"PR info retrieved (PR #{pr_details.number})", style="success")
            break
        if attempt < max_retries - 1:
            time.sleep(retry_delays[attempt])

    if pr_details is None:
        yield CompletionEvent(
            PostAnalysisError(
                success=False,
                error_type="submit_failed",
                message="PR was submitted but could not retrieve PR info from GitHub",
                details={"branch_name": branch_name},
            )
        )
        return

    pr_number = pr_details.number
    pr_url = pr_details.url
    # Get Graphite URL by parsing repo identity from git remote URL (no API call)
    remote_url = ops.git.get_remote_url(repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url = ops.graphite.get_graphite_url(repo_id, pr_number)

    yield CompletionEvent((pr_number, pr_url, graphite_url, branch_name))


def execute_preflight(
    ops: GtKit,
    cwd: Path,
    session_id: str,
) -> Generator[
    ProgressEvent | CompletionEvent[PreflightResult | PreAnalysisError | PostAnalysisError]
]:
    """Execute preflight phase: auth, squash, submit, get diff.

    This combines pre-analysis + submit + diff extraction into a single phase
    for use by the slash command orchestration.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).
        session_id: Claude session ID for scratch file isolation. Writes diff
            to .tmp/<session_id>/ in repo root (readable by subagents without
            permission prompts).

    Yields:
        ProgressEvent for status updates
        CompletionEvent with PreflightResult on success, or PreAnalysisError/PostAnalysisError
            on failure
    """
    from erk_shared.integrations.gt.prompts import truncate_diff

    # Step 1: Pre-analysis (squash commits, auth checks)
    yield ProgressEvent("Running pre-analysis checks...")
    pre_result = None
    for event in execute_pre_analysis(ops, cwd):
        if isinstance(event, CompletionEvent):
            pre_result = event.result
        else:
            yield event
    if pre_result is None or isinstance(pre_result, PreAnalysisError):
        if pre_result is not None:
            yield CompletionEvent(pre_result)
        return
    yield ProgressEvent("Pre-analysis complete", style="success")

    # Step 2: Submit branch (with existing commit message)
    yield ProgressEvent("Submitting PR...")
    submit_start = time.time()
    submit_result = None
    for event in _execute_submit_only(ops, cwd):
        if isinstance(event, CompletionEvent):
            submit_result = event.result
        else:
            yield event
    if submit_result is None or isinstance(submit_result, PostAnalysisError):
        if submit_result is not None:
            yield CompletionEvent(submit_result)
        return
    submit_elapsed = int(time.time() - submit_start)
    yield ProgressEvent(f"Branch submitted ({submit_elapsed}s)", style="success")

    pr_number, pr_url, graphite_url, branch_name = submit_result

    # Step 3: Get PR diff from GitHub API
    repo_root = ops.git.get_repository_root(cwd)
    yield ProgressEvent(f"Getting PR diff from GitHub... (gh pr diff {pr_number})")
    pr_diff = ops.github.get_pr_diff(repo_root, pr_number)
    diff_lines = len(pr_diff.splitlines())
    yield ProgressEvent(f"PR diff retrieved ({diff_lines} lines)", style="success")

    # Step 4: Truncate diff if needed and write to temp file
    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated:
        yield ProgressEvent("Diff truncated for size", style="warning")

    # Get repo root and branch info for AI prompt (needed before writing diff)
    current_branch = ops.git.get_current_branch(cwd) or branch_name
    parent_branch = ops.graphite.get_parent_branch(ops.git, repo_root, current_branch) or "main"

    # Write diff to scratch file in repo .tmp/<session_id>/
    from erk_shared.scratch.scratch import write_scratch_file

    diff_file = str(
        write_scratch_file(
            diff_content,
            session_id=session_id,
            suffix=".diff",
            prefix="pr-diff-",
            repo_root=Path(repo_root),
        )
    )
    yield ProgressEvent(f"Diff written to {diff_file}", style="success")

    # Get issue reference if present
    impl_dir = cwd / ".impl"
    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    yield CompletionEvent(
        PreflightResult(
            success=True,
            pr_number=pr_number,
            pr_url=pr_url,
            graphite_url=graphite_url,
            branch_name=branch_name,
            diff_file=diff_file,
            repo_root=str(repo_root),
            current_branch=current_branch,
            parent_branch=parent_branch,
            issue_number=issue_number,
            message=f"Preflight complete for branch: {branch_name}\nPR #{pr_number}: {pr_url}",
            commit_messages=pre_result.commit_messages,
        )
    )
