"""Create git commit and submit current branch with Graphite (two-phase).

This script handles mechanical git/gh/gt operations for the submit-branch workflow,
leaving only AI-driven analysis in the Claude command layer. It operates in two phases:

Phase 1 (pre-analysis):
1. Check for and commit any uncommitted changes
2. Get current branch and parent branch
3. Count commits in branch (compared to parent)
4. Run gt squash to consolidate commits (only if 2+ commits)
5. Return branch info for AI analysis

Phase 2 (post-analysis):
1. Split commit message into PR title (first line) and body (remaining lines)
2. Amend commit with AI-generated commit message
3. Submit branch with gt submit --publish --no-interactive --restack
4. Check if PR exists and update metadata (title, body)
5. Return PR info and status

Usage:
    dot-agent run gt submit-pr pre-analysis
    dot-agent run gt submit-pr post-analysis --commit-message "..."

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (validation failed or operation failed)

Error Types:
    - no_branch: Could not determine current branch
    - no_parent: Could not determine parent branch
    - no_commits: No commits found in branch
    - squash_failed: Failed to squash commits
    - amend_failed: Failed to amend commit
    - submit_failed: Failed to submit branch (generic)
    - submit_timeout: Submit command timed out
    - submit_merged_parent: Parent branches merged but not in main trunk
    - submit_diverged: Branch has diverged from remote
    - submit_empty_parent: Stack contains empty parent branch (already merged)
    - pr_update_failed: Failed to update PR metadata
    - claude_not_available: Claude CLI is not available or not executable
    - ai_generation_failed: AI commit message generation failed

Examples:
    $ dot-agent run gt submit-pr pre-analysis
    {"success": true, "branch_name": "feature", ...}

    $ dot-agent run gt submit-pr post-analysis --commit-message "feat: add feature"
        --pr-title "Add feature" --pr-body "Full description"
    {"success": true, "pr_number": 123, ...}
"""

import json
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, NamedTuple

import click

from erk_shared.impl_folder import (
    has_issue_reference,
    read_issue_reference,
)
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.real import RealGtKit

PreAnalysisErrorType = Literal[
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_parent",
    "no_commits",
    "squash_failed",
    "squash_conflict",
]

PostAnalysisErrorType = Literal[
    "amend_failed",
    "submit_failed",
    "submit_timeout",
    "submit_merged_parent",
    "submit_diverged",
    "submit_conflict",
    "submit_empty_parent",
    "pr_update_failed",
    "claude_not_available",
    "ai_generation_failed",
]


@dataclass
class PreAnalysisResult:
    """Success result from pre-analysis phase."""

    success: bool
    branch_name: str
    parent_branch: str
    commit_count: int
    squashed: bool
    uncommitted_changes_committed: bool
    message: str
    has_conflicts: bool = False
    conflict_details: dict[str, str] | None = None


@dataclass
class PreAnalysisError:
    """Error result from pre-analysis phase."""

    success: bool
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, str | bool]


@dataclass
class PostAnalysisResult:
    """Success result from post-analysis phase."""

    success: bool
    pr_number: int | None
    pr_url: str
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str


@dataclass
class PostAnalysisError:
    """Error result from post-analysis phase."""

    success: bool
    error_type: PostAnalysisErrorType
    message: str
    details: dict[str, str]


@dataclass
class PreflightResult:
    """Result from preflight phase (pre-analysis + submit + diff extraction)."""

    success: bool
    pr_number: int
    pr_url: str
    graphite_url: str
    branch_name: str
    diff_file: str  # Path to temp diff file
    repo_root: str
    current_branch: str
    parent_branch: str
    issue_number: int | None
    message: str


@dataclass
class FinalizeResult:
    """Result from finalize phase (update PR metadata)."""

    success: bool
    pr_number: int
    pr_url: str
    pr_title: str
    graphite_url: str
    branch_name: str
    issue_number: int | None
    message: str


def execute_pre_analysis(ops: GtKit | None = None) -> PreAnalysisResult | PreAnalysisError:
    """Execute the pre-analysis phase. Returns success or error result."""
    if ops is None:
        ops = RealGtKit()

    # Step 0a: Check Graphite authentication FIRST (before any git operations)
    click.echo("  ↳ Checking Graphite authentication... (gt auth whoami)", err=True)
    gt_authenticated, gt_username, _ = ops.main_graphite().check_auth_status()
    if not gt_authenticated:
        return PreAnalysisError(
            success=False,
            error_type="gt_not_authenticated",
            message="Graphite CLI (gt) is not authenticated",
            details={
                "fix": "Run 'gt auth' to authenticate with Graphite",
                "authenticated": False,
            },
        )
    click.echo(f"  ✓ Authenticated as {gt_username}", err=True)

    # Step 0b: Check GitHub authentication (required for PR operations)
    click.echo("  ↳ Checking GitHub authentication... (gh auth status)", err=True)
    gh_authenticated, gh_username, _ = ops.github().check_auth_status()
    if not gh_authenticated:
        return PreAnalysisError(
            success=False,
            error_type="gh_not_authenticated",
            message="GitHub CLI (gh) is not authenticated",
            details={
                "fix": "Run 'gh auth login' to authenticate with GitHub",
                "authenticated": False,
            },
        )
    click.echo(f"  ✓ Authenticated as {gh_username}", err=True)

    # Step 0c: Check for and commit uncommitted changes
    cwd = Path.cwd()
    uncommitted_changes_committed = False
    if ops.git().has_uncommitted_changes(cwd):
        click.echo("  ↳ Staging uncommitted changes... (git add -A)", err=True)
        try:
            ops.git().add_all(cwd)
            click.echo("  ✓ Changes staged", err=True)
        except subprocess.CalledProcessError:
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to stage uncommitted changes",
                details={"reason": "git add failed"},
            )
        click.echo("  ↳ Committing staged changes... (git commit)", err=True)
        try:
            ops.git().commit(cwd, "WIP: Prepare for submission")
            uncommitted_changes_committed = True
            click.echo("  ✓ Uncommitted changes committed", err=True)
        except subprocess.CalledProcessError:
            return PreAnalysisError(
                success=False,
                error_type="squash_failed",
                message="Failed to commit uncommitted changes",
                details={"reason": "git commit failed"},
            )

    # Step 1: Get current branch
    branch_name = ops.git().get_current_branch(cwd)

    if branch_name is None:
        return PreAnalysisError(
            success=False,
            error_type="no_branch",
            message="Could not determine current branch",
            details={"branch_name": "unknown"},
        )

    # Step 2: Get parent branch
    repo_root = ops.git().get_repository_root(cwd)
    parent_branch = ops.main_graphite().get_parent_branch(ops.git(), repo_root, branch_name)

    if parent_branch is None:
        return PreAnalysisError(
            success=False,
            error_type="no_parent",
            message=f"Could not determine parent branch for: {branch_name}",
            details={"branch_name": branch_name},
        )

    # Step 2.5: Check for merge conflicts (informational only, does not block)
    # First try GitHub API if PR exists (most accurate), then fallback to local git merge-tree
    pr_number, pr_url = ops.github().get_pr_status(branch_name)

    # Track conflict info (will be included in success result)
    has_conflicts = False
    conflict_details: dict[str, str] | None = None

    if pr_number is not None:
        # PR exists - check mergeability
        mergeable, merge_state = ops.github().get_pr_mergeability(pr_number)

        if mergeable == "CONFLICTING":
            has_conflicts = True
            conflict_details = {
                "pr_number": str(pr_number),
                "parent_branch": parent_branch,
                "merge_state": merge_state,
                "detection_method": "github_api",
            }
            click.echo(
                f"  ↳ PR #{pr_number} has merge conflicts with {parent_branch}",
                err=True,
            )

        # UNKNOWN status: proceed with warning (GitHub hasn't computed yet)
        elif mergeable == "UNKNOWN":
            click.echo(
                "  ↳ PR mergeability status is UNKNOWN, proceeding anyway",
                err=True,
            )

    else:
        # No PR yet - fallback to local git merge-tree check
        if ops.git().check_merge_conflicts(cwd, parent_branch, branch_name):
            has_conflicts = True
            conflict_details = {
                "parent_branch": parent_branch,
                "detection_method": "git_merge_tree",
            }
            click.echo(
                f"  ↳ Branch has local merge conflicts with {parent_branch}",
                err=True,
            )

    # Step 3: Count commits in branch
    commit_count = ops.git().count_commits_ahead(cwd, parent_branch)

    if commit_count == 0:
        return PreAnalysisError(
            success=False,
            error_type="no_commits",
            message=f"No commits found in branch: {branch_name}",
            details={"branch_name": branch_name, "parent_branch": parent_branch},
        )

    # Step 4: Run gt squash only if 2+ commits
    squashed = False
    if commit_count >= 2:
        click.echo(f"  ↳ Squashing {commit_count} commits... (gt squash --no-edit)", err=True)
        try:
            ops.main_graphite().squash_branch(repo_root, quiet=False)
            squashed = True
            click.echo(f"  ✓ Squashed {commit_count} commits into 1", err=True)
        except subprocess.CalledProcessError as e:
            # Check if failure was due to merge conflict
            stderr = e.stderr if hasattr(e, "stderr") else ""
            combined_output = (e.stdout if hasattr(e, "stdout") else "") + stderr
            if "conflict" in combined_output.lower() or "merge conflict" in combined_output.lower():
                return PreAnalysisError(
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

            # Generic squash failure (not conflict-related)
            return PreAnalysisError(
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

    # Build success message
    message_parts = [f"Pre-analysis complete for branch: {branch_name}"]

    if uncommitted_changes_committed:
        message_parts.append("Committed uncommitted changes")

    if squashed:
        message_parts.append(f"Squashed {commit_count} commits into 1")
    else:
        message_parts.append("Single commit, no squash needed")

    message = "\n".join(message_parts)

    return PreAnalysisResult(
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


def build_pr_metadata_section(pr_number: int) -> str:
    """Build metadata footer section for PR body.

    This section is appended AFTER the PR body content, not before.
    It contains only essential metadata: checkout command.

    Note: Issue closing is now handled via GitHub's native branch linking
    (branches created with `gh issue develop` automatically close issues when merged).

    Args:
        pr_number: PR number

    Returns:
        Metadata footer section as string
    """
    metadata_parts: list[str] = []

    # Separator at start of footer
    metadata_parts.append("\n---\n")

    # Checkout command
    metadata_parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_number}\n"
        f"```\n"
    )

    return "\n".join(metadata_parts)


class _SubmitResult(NamedTuple):
    """Result from running submit_stack in background thread."""

    success: bool
    error: RuntimeError | None = None


def _run_gt_submit_with_progress(ops: GtKit, repo_root: Path) -> _SubmitResult:
    """Run gt submit with descriptive progress markers.

    Displays periodic progress updates during the submit operation.
    This function should only be called after a separate restack phase.

    Args:
        ops: GtKit operations interface
        repo_root: Repository root directory

    Returns:
        _SubmitResult with success status and optional error
    """
    start_time = time.time()
    result_holder: list[_SubmitResult] = []

    # Run submit in background thread
    def run_submit():
        try:
            ops.main_graphite().submit_stack(repo_root, publish=True, restack=False, quiet=False)
            result_holder.append(_SubmitResult(success=True))
        except RuntimeError as e:
            result_holder.append(_SubmitResult(success=False, error=e))

    thread = threading.Thread(target=run_submit, daemon=True)
    thread.start()

    # Progress markers: (threshold_seconds, description)
    progress_markers = [
        (10, "Pushing to remote"),
        (20, "Creating PR"),
        (30, "Finalizing"),
    ]

    marker_idx = 0

    # Monitor progress and show markers
    while thread.is_alive():
        elapsed = time.time() - start_time

        # Show next marker if threshold reached
        if marker_idx < len(progress_markers):
            threshold, description = progress_markers[marker_idx]
            if elapsed >= threshold:
                click.echo(
                    click.style(f"  ... [{int(elapsed)}s] {description}", dim=True),
                    err=True,
                )
                marker_idx += 1

        # Check every second
        thread.join(timeout=1.0)

    return result_holder[0] if result_holder else _SubmitResult(success=False)


def _execute_submit_only(
    ops: GtKit,
) -> tuple[int, str, str, str] | PostAnalysisError:
    """Submit branch and wait for PR info, without modifying commit message.

    Returns:
        Tuple of (pr_number, pr_url, graphite_url, branch_name) on success
        PostAnalysisError on failure
    """
    cwd = Path.cwd()
    branch_name = ops.git().get_current_branch(cwd) or "unknown"

    # Phase 1: Restack the stack
    click.echo("  ↳ Rebasing stack... (gt restack)", err=True)
    restack_start = time.time()
    try:
        repo_root = ops.git().get_repository_root(cwd)
        ops.main_graphite().restack(repo_root, no_interactive=True, quiet=False)
    except subprocess.CalledProcessError as e:
        # Check for restack errors (conflicts, etc.)
        has_output = hasattr(e, "stdout") and hasattr(e, "stderr")
        combined_output = e.stdout + e.stderr if has_output else str(e)
        combined_lower = combined_output.lower()

        # Check for merge conflicts
        if "conflict" in combined_lower or "merge conflict" in combined_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_conflict",
                message="Merge conflicts detected during stack rebase",
                details={
                    "branch_name": branch_name,
                    "stdout": e.stdout if hasattr(e, "stdout") else "",
                    "stderr": e.stderr if hasattr(e, "stderr") else str(e),
                },
            )

        # Generic restack failure
        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to restack branch",
            details={
                "branch_name": branch_name,
                "stdout": e.stdout if hasattr(e, "stdout") else "",
                "stderr": e.stderr if hasattr(e, "stderr") else str(e),
            },
        )

    restack_elapsed = int(time.time() - restack_start)
    click.echo(f"  ✓ Stack rebased ({restack_elapsed}s)", err=True)

    # Phase 2: Submit to GitHub (with progress markers)
    click.echo("  ↳ Pushing branches and creating PR... (gt submit --publish)", err=True)
    result = _run_gt_submit_with_progress(ops, repo_root)

    if not result.success:
        # Extract error message for categorization
        error_message = str(result.error) if result.error else ""
        error_lower = error_message.lower()

        # Check for empty parent branch
        nothing_to_submit = "Nothing to submit!" in error_message
        no_changes = "does not introduce any changes" in error_message
        if nothing_to_submit or no_changes:
            return PostAnalysisError(
                success=False,
                error_type="submit_empty_parent",
                message=(
                    "Stack contains an empty parent branch that was already merged. "
                    "Run 'gt track --parent <trunk>' to reparent this branch, then 'gt restack'."
                ),
                details={
                    "branch_name": branch_name,
                    "error": error_message,
                },
            )

        if "conflict" in error_lower or "merge conflict" in error_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_conflict",
                message="Merge conflicts detected during branch submission",
                details={
                    "branch_name": branch_name,
                    "error": error_message,
                },
            )

        if "merged but the merged commits are not contained" in error_message:
            return PostAnalysisError(
                success=False,
                error_type="submit_merged_parent",
                message="Parent branches have been merged but are not in main trunk",
                details={
                    "branch_name": branch_name,
                    "error": error_message,
                },
            )

        if "updated remotely" in error_lower or "must sync" in error_lower:
            return PostAnalysisError(
                success=False,
                error_type="submit_diverged",
                message="Branch has diverged from remote - manual sync required",
                details={
                    "branch_name": branch_name,
                    "error": error_message,
                },
            )

        if "timed out after 120 seconds" in error_message:
            return PostAnalysisError(
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

        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="Failed to submit branch with gt submit",
            details={
                "branch_name": branch_name,
                "error": error_message,
            },
        )

    click.echo("  ✓ Branch submitted to Graphite", err=True)

    # Wait for PR info
    pr_info = None
    max_retries = 5
    retry_delays = [0.5, 1.0, 2.0, 4.0, 8.0]

    click.echo("⏳ Waiting for PR info from GitHub API... (gh pr view)", err=True)

    for attempt in range(max_retries):
        if attempt > 0:
            click.echo(f"   Attempt {attempt + 1}/{max_retries}...", err=True)
        pr_info = ops.github().get_pr_info()
        if pr_info is not None:
            pr_num, _ = pr_info
            click.echo(f"✓ PR info retrieved (PR #{pr_num})", err=True)
            break
        if attempt < max_retries - 1:
            time.sleep(retry_delays[attempt])

    if pr_info is None:
        return PostAnalysisError(
            success=False,
            error_type="submit_failed",
            message="PR was submitted but could not retrieve PR info from GitHub",
            details={"branch_name": branch_name},
        )

    pr_number, pr_url = pr_info
    graphite_url_result = ops.github().get_graphite_pr_url(pr_number)
    graphite_url = graphite_url_result or ""

    return (pr_number, pr_url, graphite_url, branch_name)


def execute_preflight(
    ops: GtKit | None = None,
    *,
    session_id: str,
) -> PreflightResult | PreAnalysisError | PostAnalysisError:
    """Execute preflight phase: auth, squash, submit, get diff.

    This combines pre-analysis + submit + diff extraction into a single phase
    for use by the slash command orchestration.

    Args:
        ops: Optional GtKit for dependency injection.
        session_id: Claude session ID for scratch file isolation. Writes diff
            to .tmp/<session_id>/ in repo root (readable by subagents without
            permission prompts).

    Returns:
        PreflightResult on success, or PreAnalysisError/PostAnalysisError on failure
    """
    if ops is None:
        ops = RealGtKit()

    from erk_shared.integrations.gt.prompts import truncate_diff

    # Step 1: Pre-analysis (squash commits, auth checks)
    click.echo("🔍 Running pre-analysis checks...", err=True)
    pre_result = execute_pre_analysis(ops)
    if isinstance(pre_result, PreAnalysisError):
        return pre_result
    click.echo("✓ Pre-analysis complete", err=True)

    # Step 2: Submit branch (with existing commit message)
    click.echo("🚀 Submitting PR...", err=True)
    submit_start = time.time()
    submit_result = _execute_submit_only(ops)
    if isinstance(submit_result, PostAnalysisError):
        return submit_result
    submit_elapsed = int(time.time() - submit_start)
    click.echo(f"✓ Branch submitted ({submit_elapsed}s)", err=True)

    pr_number, pr_url, graphite_url, branch_name = submit_result

    # Step 3: Get PR diff from GitHub API
    click.echo(f"📊 Getting PR diff from GitHub... (gh pr diff {pr_number})", err=True)
    pr_diff = ops.github().get_pr_diff(pr_number)
    diff_lines = len(pr_diff.splitlines())
    click.echo(f"✓ PR diff retrieved ({diff_lines} lines)", err=True)

    # Step 4: Truncate diff if needed and write to temp file
    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated:
        click.echo("  ⚠️  Diff truncated for size", err=True)

    # Get repo root and branch info for AI prompt (needed before writing diff)
    cwd = Path.cwd()
    repo_root = ops.git().get_repository_root(cwd)
    current_branch = ops.git().get_current_branch(cwd) or branch_name
    parent_branch = (
        ops.main_graphite().get_parent_branch(ops.git(), repo_root, current_branch) or "main"
    )

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
    click.echo(f"✓ Diff written to {diff_file}", err=True)

    # Get issue reference if present
    cwd = Path.cwd()
    impl_dir = cwd / ".impl"
    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    return PreflightResult(
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
    )


def execute_finalize(
    pr_number: int,
    pr_title: str,
    pr_body: str | None = None,
    pr_body_file: Path | None = None,
    diff_file: str | None = None,
    ops: GtKit | None = None,
) -> FinalizeResult | PostAnalysisError:
    """Execute finalize phase: update PR metadata and clean up.

    Args:
        pr_number: PR number to update
        pr_title: AI-generated PR title (first line of commit message)
        pr_body: AI-generated PR body (remaining lines). Mutually exclusive with pr_body_file.
        pr_body_file: Path to file containing PR body. Mutually exclusive with pr_body.
        diff_file: Optional temp diff file to clean up
        ops: Optional GtKit for dependency injection

    Returns:
        FinalizeResult on success, or PostAnalysisError on failure

    Raises:
        ValueError: If neither pr_body nor pr_body_file is provided, or if both are provided.
    """
    # LBYL: Validate exactly one of pr_body or pr_body_file is provided
    if pr_body is not None and pr_body_file is not None:
        raise ValueError("Cannot specify both --pr-body and --pr-body-file")
    if pr_body is None and pr_body_file is None:
        raise ValueError("Must specify either --pr-body or --pr-body-file")

    # Read body from file if pr_body_file is provided
    if pr_body_file is not None:
        if not pr_body_file.exists():
            raise ValueError(f"PR body file does not exist: {pr_body_file}")
        pr_body = pr_body_file.read_text(encoding="utf-8")

    if ops is None:
        ops = RealGtKit()

    # Get impl directory for metadata
    cwd = Path.cwd()
    impl_dir = cwd / ".impl"

    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    # Build metadata section and combine with AI body
    metadata_section = build_pr_metadata_section(pr_number=pr_number)
    # pr_body is guaranteed non-None here (either passed in or read from file, validated above)
    assert pr_body is not None

    final_body = pr_body + metadata_section

    # Update PR metadata
    click.echo("📝 Updating PR metadata... (gh pr edit)", err=True)
    if ops.github().update_pr_metadata(pr_title, final_body):
        click.echo("✓ PR metadata updated", err=True)
    else:
        click.echo("⚠️  Failed to update PR metadata", err=True)

    # Clean up temp diff file
    if diff_file is not None:
        diff_path = Path(diff_file)
        if diff_path.exists():
            try:
                diff_path.unlink()
                click.echo(f"✓ Cleaned up temp file: {diff_file}", err=True)
            except OSError:
                pass  # Ignore cleanup errors

    # Get PR info for result
    cwd = Path.cwd()
    branch_name = ops.git().get_current_branch(cwd) or "unknown"
    pr_url_result = ops.github().get_pr_info()
    pr_url = pr_url_result[1] if pr_url_result else ""
    graphite_url = ops.github().get_graphite_pr_url(pr_number) or ""

    return FinalizeResult(
        success=True,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_title=pr_title,
        graphite_url=graphite_url,
        branch_name=branch_name,
        issue_number=issue_number,
        message=f"Successfully updated PR #{pr_number}: {pr_url}",
    )


@click.group()
def pr_submit() -> None:
    """Create git commit and submit current branch with Graphite (two-phase)."""
    pass


@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID for scratch file isolation. "
    "Writes diff to .tmp/<session-id>/ in repo root.",
)
def preflight(session_id: str) -> None:
    """Execute preflight phase: auth, squash, submit, get diff.

    Returns JSON with PR info and path to temp diff file for AI analysis.
    This is phase 1 of the 3-phase workflow for slash command orchestration.
    """
    try:
        result = execute_preflight(session_id=session_id)
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, (PreAnalysisError, PostAnalysisError)):
            raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


@click.command()
@click.option("--pr-number", required=True, type=int, help="PR number to update")
@click.option("--pr-title", required=True, help="AI-generated PR title")
@click.option("--pr-body", required=False, help="AI-generated PR body (text)")
@click.option(
    "--pr-body-file",
    type=click.Path(exists=True, path_type=Path),
    required=False,
    help="Path to file containing PR body (mutually exclusive with --pr-body)",
)
@click.option("--diff-file", required=False, help="Temp diff file to clean up")
def finalize(
    pr_number: int,
    pr_title: str,
    pr_body: str | None,
    pr_body_file: Path | None,
    diff_file: str | None,
) -> None:
    """Execute finalize phase: update PR metadata.

    This is phase 3 of the 3-phase workflow for slash command orchestration.
    Accepts PR body either as inline text (--pr-body) or from a file (--pr-body-file).
    """
    try:
        result = execute_finalize(pr_number, pr_title, pr_body, pr_body_file, diff_file)
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, PostAnalysisError):
            raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Validation error: {e}", err=True)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None


# Register subcommands
pr_submit.add_command(preflight)
pr_submit.add_command(finalize)
