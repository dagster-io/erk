"""Finalize phase for submit-branch workflow.

This phase handles:
1. Update PR metadata (title, body) with AI-generated content
2. Clean up temp files
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.types import GitHubRepoId
from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import FinalizeResult, PostAnalysisError


def build_pr_metadata_section(pr_number: int, issue_number: int | None = None) -> str:
    """Build metadata footer section for PR body.

    This section is appended AFTER the PR body content, not before.
    It contains essential metadata: issue closing reference (if linked to a plan)
    and checkout command.

    Note: Issue closing is handled via commit message keywords ("Closes #N")
    added by the gt finalize process.

    Args:
        pr_number: PR number
        issue_number: Optional issue number to close (from .impl/issue.json)

    Returns:
        Metadata footer section as string
    """
    metadata_parts: list[str] = []

    # Separator at start of footer
    metadata_parts.append("\n---\n")

    # Issue closing reference (if linked to a plan)
    if issue_number is not None:
        metadata_parts.append(f"\nCloses #{issue_number}\n")

    # Checkout command
    metadata_parts.append(
        f"\nTo checkout this PR in a fresh worktree and environment locally, run:\n\n"
        f"```\n"
        f"erk pr checkout {pr_number}\n"
        f"```\n"
    )

    return "\n".join(metadata_parts)


def execute_finalize(
    ops: GtKit,
    cwd: Path,
    pr_number: int,
    pr_title: str,
    pr_body: str | None = None,
    pr_body_file: Path | None = None,
    diff_file: str | None = None,
) -> Generator[ProgressEvent | CompletionEvent[FinalizeResult | PostAnalysisError]]:
    """Execute finalize phase: update PR metadata and clean up.

    Args:
        ops: GtKit for dependency injection.
        cwd: Working directory (repository path).
        pr_number: PR number to update
        pr_title: AI-generated PR title (first line of commit message)
        pr_body: AI-generated PR body (remaining lines). Mutually exclusive with pr_body_file.
        pr_body_file: Path to file containing PR body. Mutually exclusive with pr_body.
        diff_file: Optional temp diff file to clean up

    Yields:
        ProgressEvent for status updates
        CompletionEvent with FinalizeResult on success, or PostAnalysisError on failure

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

    # Get impl directory for metadata
    impl_dir = cwd / ".impl"

    issue_number: int | None = None
    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    # Build metadata section and combine with AI body
    metadata_section = build_pr_metadata_section(pr_number=pr_number, issue_number=issue_number)
    # pr_body is guaranteed non-None here (either passed in or read from file, validated above)
    assert pr_body is not None

    final_body = pr_body + metadata_section

    # Get repo root for GitHub operations
    repo_root = ops.git.get_repository_root(cwd)

    # Update PR metadata
    yield ProgressEvent("Updating PR metadata... (gh pr edit)")
    ops.github.update_pr_title_and_body(repo_root, pr_number, pr_title, final_body)
    yield ProgressEvent("PR metadata updated", style="success")

    # Amend local commit with PR title and body (without metadata footer)
    yield ProgressEvent("Updating local commit message...")
    commit_message = pr_title
    if pr_body:
        commit_message = f"{pr_title}\n\n{pr_body}"
    ops.git.amend_commit(repo_root, commit_message)
    yield ProgressEvent("Local commit message updated", style="success")

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
    pr_url_result = ops.github.get_pr_info_for_branch(repo_root, branch_name)
    pr_url = pr_url_result[1] if pr_url_result else ""

    # Get Graphite URL by parsing repo identity from git remote URL (no API call)
    remote_url = ops.git.get_remote_url(repo_root, "origin")
    owner, repo_name = parse_git_remote_url(remote_url)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    graphite_url = ops.graphite.get_graphite_url(repo_id, pr_number)

    yield CompletionEvent(
        FinalizeResult(
            success=True,
            pr_number=pr_number,
            pr_url=pr_url,
            pr_title=pr_title,
            graphite_url=graphite_url,
            branch_name=branch_name,
            issue_number=issue_number,
            message=f"Successfully updated PR #{pr_number}: {pr_url}",
        )
    )
