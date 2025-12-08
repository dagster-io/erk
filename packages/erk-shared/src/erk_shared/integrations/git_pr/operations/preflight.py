"""Preflight phase for git-only PR workflow.

This phase handles:
1. Check GitHub CLI authentication
2. Stage uncommitted changes
3. Create commit (or use existing commits)
4. Push to remote
5. Create PR (or find existing)
6. Get diff for AI analysis
"""

import subprocess
from collections.abc import Generator
from pathlib import Path

from erk_shared.github.types import PRNotFound
from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.git_pr.abc import GitPrKit
from erk_shared.integrations.git_pr.types import (
    GitPreflightError,
    GitPreflightResult,
)
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent


def execute_preflight(
    ops: GitPrKit,
    cwd: Path,
    session_id: str,
) -> Generator[ProgressEvent | CompletionEvent[GitPreflightResult | GitPreflightError]]:
    """Execute preflight phase: auth, stage, commit, push, create PR, get diff.

    This is phase 1 of the 2-phase workflow for git-only PR submission.

    Args:
        ops: GitPrKit for dependency injection.
        cwd: Working directory (repository path).
        session_id: Claude session ID for scratch file isolation.

    Yields:
        ProgressEvent for status updates
        CompletionEvent with GitPreflightResult on success, or GitPreflightError on failure
    """
    # Step 1: Check GitHub CLI authentication
    yield ProgressEvent("Checking GitHub CLI authentication...")
    is_authenticated, username, _hostname = ops.github.check_auth_status()
    if not is_authenticated:
        yield CompletionEvent(
            GitPreflightError(
                success=False,
                error_type="gh_not_authenticated",
                message="GitHub CLI is not authenticated. Run 'gh auth login' first.",
                details={},
            )
        )
        return
    yield ProgressEvent(f"Authenticated as {username}", style="success")

    # Step 2: Get repository root and current branch
    yield ProgressEvent("Checking repository state...")
    repo_root = ops.git.get_repository_root(cwd)
    current_branch = ops.git.get_current_branch(cwd)
    if current_branch is None:
        yield CompletionEvent(
            GitPreflightError(
                success=False,
                error_type="no_branch",
                message="Not on a branch (detached HEAD state)",
                details={},
            )
        )
        return

    trunk_branch = ops.git.detect_trunk_branch(repo_root)
    yield ProgressEvent(f"On branch '{current_branch}', trunk is '{trunk_branch}'", style="success")

    # Step 3: Stage and commit uncommitted changes if any
    staged, modified, untracked = ops.git.get_file_status(cwd)
    has_uncommitted = bool(staged or modified or untracked)

    if has_uncommitted:
        yield ProgressEvent("Staging uncommitted changes...")
        try:
            ops.git.add_all(cwd)
        except subprocess.CalledProcessError as e:
            yield CompletionEvent(
                GitPreflightError(
                    success=False,
                    error_type="stage_failed",
                    message="Failed to stage changes",
                    details={"error": str(e)},
                )
            )
            return
        yield ProgressEvent("Changes staged", style="success")

    # Get commit messages for AI context (before potential commit)
    commit_messages = ops.git.get_commit_messages_since(cwd, trunk_branch)

    # Step 4: Push to remote
    yield ProgressEvent("Pushing to remote...")
    try:
        ops.git.push_to_remote(cwd, "origin", current_branch, set_upstream=True)
    except subprocess.CalledProcessError as e:
        error_msg = str(e)
        yield CompletionEvent(
            GitPreflightError(
                success=False,
                error_type="push_failed",
                message="Failed to push to remote",
                details={"error": error_msg, "branch": current_branch},
            )
        )
        return
    yield ProgressEvent("Pushed to origin", style="success")

    # Step 5: Check for existing PR or create new one
    yield ProgressEvent("Checking for existing PR...")
    pr_result = ops.github.get_pr_for_branch(repo_root, current_branch)

    pr_created = False
    if isinstance(pr_result, PRNotFound):
        # Create new PR
        yield ProgressEvent("Creating pull request...")
        try:
            # Get first commit message for PR title/body
            if commit_messages:
                first_msg = commit_messages[0]
                lines = first_msg.strip().split("\n")
                pr_title = lines[0]
                pr_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            else:
                pr_title = current_branch
                pr_body = ""

            pr_number = ops.github.create_pr(
                repo_root, current_branch, pr_title, pr_body, base=trunk_branch, draft=False
            )
            pr_created = True
            yield ProgressEvent(f"Created PR #{pr_number}", style="success")
        except Exception as e:
            yield CompletionEvent(
                GitPreflightError(
                    success=False,
                    error_type="pr_create_failed",
                    message="Failed to create pull request",
                    details={"error": str(e), "branch": current_branch},
                )
            )
            return

        # Fetch PR details after creation
        pr_result = ops.github.get_pr_for_branch(repo_root, current_branch)
        if isinstance(pr_result, PRNotFound):
            yield CompletionEvent(
                GitPreflightError(
                    success=False,
                    error_type="pr_create_failed",
                    message="PR created but could not fetch details",
                    details={"branch": current_branch},
                )
            )
            return
    else:
        yield ProgressEvent(f"Found existing PR #{pr_result.number}", style="success")

    pr_number = pr_result.number
    pr_url = pr_result.url

    # Step 6: Get PR diff for AI analysis
    yield ProgressEvent(f"Getting PR diff... (gh pr diff {pr_number})")
    pr_diff = ops.github.get_pr_diff(repo_root, pr_number)
    diff_lines = len(pr_diff.splitlines())
    yield ProgressEvent(f"PR diff retrieved ({diff_lines} lines)", style="success")

    # Step 7: Write diff to scratch file
    from erk_shared.integrations.gt.prompts import truncate_diff
    from erk_shared.scratch.scratch import write_scratch_file

    diff_content, was_truncated = truncate_diff(pr_diff)
    if was_truncated:
        yield ProgressEvent("Diff truncated for size", style="warning")

    diff_file = str(
        write_scratch_file(
            diff_content,
            session_id=session_id,
            suffix=".diff",
            prefix="pr-diff-",
            repo_root=repo_root,
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
        GitPreflightResult(
            success=True,
            pr_number=pr_number,
            pr_url=pr_url,
            branch_name=current_branch,
            diff_file=diff_file,
            issue_number=issue_number,
            pr_created=pr_created,
            repo_root=str(repo_root),
            parent_branch=trunk_branch,
            commit_messages=commit_messages,
            message=f"Preflight complete for branch: {current_branch}\nPR #{pr_number}: {pr_url}",
        )
    )
