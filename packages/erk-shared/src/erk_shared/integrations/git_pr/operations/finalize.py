"""Finalize phase for git-only PR workflow.

This phase handles:
1. Update PR title and body with AI-generated content
2. Add PR body footer (checkout command, issue closing)
3. Clean up temp files
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import PRNotFound
from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.git_pr.abc import GitPrKit
from erk_shared.integrations.git_pr.types import (
    GitFinalizeError,
    GitFinalizeResult,
)
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent


def execute_finalize(
    ops: GitPrKit,
    cwd: Path,
    pr_number: int,
    pr_title: str,
    pr_body: str | None = None,
    pr_body_file: Path | None = None,
    diff_file: str | None = None,
) -> Generator[ProgressEvent | CompletionEvent[GitFinalizeResult | GitFinalizeError]]:
    """Execute finalize phase: update PR metadata and clean up.

    This is phase 2 of the 2-phase workflow for git-only PR submission.

    Args:
        ops: GitPrKit for dependency injection.
        cwd: Working directory (repository path).
        pr_number: PR number to update.
        pr_title: AI-generated PR title (first line of commit message).
        pr_body: AI-generated PR body (text). Mutually exclusive with pr_body_file.
        pr_body_file: Path to file containing PR body. Mutually exclusive with pr_body.
        diff_file: Optional temp diff file to clean up.

    Yields:
        ProgressEvent for status updates
        CompletionEvent with GitFinalizeResult on success, or GitFinalizeError on failure

    Raises:
        ValueError: If neither pr_body nor pr_body_file is provided, or if both are.
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

    # Get impl directory for metadata
    impl_dir = cwd / ".impl"

    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    # Build metadata section and combine with AI body
    metadata_section = build_pr_body_footer(
        pr_number=pr_number,
        issue_number=issue_number,
    )

    # pr_body is guaranteed non-None here (either passed in or read from file)
    assert pr_body is not None
    final_body = pr_body + metadata_section

    # Get repo root for GitHub operations
    repo_root = ops.git.get_repository_root(cwd)

    # Update PR metadata
    yield ProgressEvent("Updating PR metadata... (gh pr edit)")
    try:
        ops.github.update_pr_title_and_body(repo_root, pr_number, pr_title, final_body)
    except Exception as e:
        yield CompletionEvent(
            GitFinalizeError(
                success=False,
                error_type="pr_update_failed",
                message="Failed to update PR metadata",
                details={"error": str(e), "pr_number": str(pr_number)},
            )
        )
        return
    yield ProgressEvent("PR metadata updated", style="success")

    # Clean up temp diff file
    if diff_file is not None:
        diff_path = Path(diff_file)
        if diff_path.exists():
            try:
                diff_path.unlink()
                yield ProgressEvent(f"Cleaned up temp file: {diff_file}", style="success")
            except OSError:
                pass  # Ignore cleanup errors

    # Get PR info for result
    branch_name = ops.git.get_current_branch(cwd) or "unknown"
    pr_result = ops.github.get_pr_for_branch(repo_root, branch_name)
    pr_url = pr_result.url if not isinstance(pr_result, PRNotFound) else ""

    yield CompletionEvent(
        GitFinalizeResult(
            success=True,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_title=pr_title,
            branch_name=branch_name,
            issue_number=issue_number,
            message=f"Successfully updated PR #{pr_number}: {pr_url}",
        )
    )
