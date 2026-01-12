"""Finalize phase for submit-branch workflow.

This phase handles:
1. Update PR metadata (title, body) with AI-generated content
2. Clean up temp files
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.gateway.gt.abc import GtKit
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.gt.types import FinalizeResult, PostAnalysisError
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.pr_footer import (
    ClosingReference,
    build_pr_body_footer,
    extract_closing_reference,
    extract_footer_from_body,
)
from erk_shared.github.types import GitHubRepoId, PRNotFound
from erk_shared.impl_folder import has_issue_reference, read_issue_reference

# Label added to PRs that originate from learn plans.
# Checked by land_cmd.py to skip creating pending-learn marker.
ERK_SKIP_LEARN_LABEL = "erk-skip-learn"


def is_learn_plan(impl_dir: Path) -> bool:
    """Check if the plan in the impl folder is a learn plan.

    Checks the labels stored in .impl/issue.json for the "erk-learn" label.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if "erk-learn" label is present, False otherwise (including if
        issue.json doesn't exist or labels field is missing)
    """
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        return False

    return "erk-learn" in issue_ref.labels


def _extract_closing_ref_from_pr(
    ops: GtKit,
    cwd: Path,
    pr_number: int,
) -> ClosingReference | None:
    """Extract closing reference from an existing PR's footer.

    Used to preserve closing references when .impl/issue.json is missing.
    """
    repo_root = ops.git.get_repository_root(cwd)
    current_pr = ops.github.get_pr(repo_root, pr_number)
    if isinstance(current_pr, PRNotFound) or not current_pr.body:
        return None
    existing_footer = extract_footer_from_body(current_pr.body)
    if existing_footer is None:
        return None
    return extract_closing_reference(existing_footer)


def execute_finalize(
    *,
    ops: GtKit,
    cwd: Path,
    pr_number: int,
    pr_title: str,
    pr_body: str | None,
    pr_body_file: Path | None,
    diff_file: str | None,
    plans_repo: str | None,
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
    effective_plans_repo: str | None = plans_repo

    if has_issue_reference(impl_dir):
        issue_ref = read_issue_reference(impl_dir)
        if issue_ref is not None:
            issue_number = issue_ref.issue_number

    # Fallback: If no issue_number from .impl/issue.json, try to preserve
    # existing closing reference from the current PR body.
    # This prevents losing closing references when .impl/issue.json is missing
    # and finalize is run (which rebuilds the entire PR body).
    closing_ref: ClosingReference | None = None
    if issue_number is None:
        closing_ref = _extract_closing_ref_from_pr(ops, cwd, pr_number)
    if closing_ref is not None:
        issue_number = closing_ref.issue_number
        effective_plans_repo = closing_ref.plans_repo

    # Check if this is a learn plan
    is_learn_origin = is_learn_plan(impl_dir)

    # Build metadata section and combine with AI body
    metadata_section = build_pr_body_footer(
        pr_number=pr_number,
        issue_number=issue_number,
        plans_repo=effective_plans_repo,
    )
    # pr_body is guaranteed non-None here (either passed in or read from file, validated above)
    assert pr_body is not None

    final_body = pr_body + metadata_section

    # Get repo root for GitHub operations
    repo_root = ops.git.get_repository_root(cwd)

    # Update PR metadata
    yield ProgressEvent("Updating PR metadata... (gh pr edit)")
    ops.github.update_pr_title_and_body(
        repo_root=repo_root, pr_number=pr_number, title=pr_title, body=final_body
    )
    yield ProgressEvent("PR metadata updated", style="success")

    # Add learn skip label if this is a learn plan
    if is_learn_origin:
        yield ProgressEvent("Adding erk-skip-learn label...")
        ops.github.add_label_to_pr(repo_root, pr_number, ERK_SKIP_LEARN_LABEL)
        yield ProgressEvent("Label added", style="success")

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
    pr_result = ops.github.get_pr_for_branch(repo_root, branch_name)
    pr_url = pr_result.url if not isinstance(pr_result, PRNotFound) else ""

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
