"""Finalize phase for submit-branch workflow.

This phase handles:
1. Update PR metadata (title, body) with AI-generated content
2. Clean up temp files
"""

from collections.abc import Generator
from pathlib import Path

from erk_shared.github.metadata import find_metadata_block
from erk_shared.github.parsing import parse_git_remote_url
from erk_shared.github.pr_footer import build_pr_body_footer
from erk_shared.github.types import GitHubRepoId, PRNotFound
from erk_shared.impl_folder import has_issue_reference, read_issue_reference
from erk_shared.integrations.gt.abc import GtKit
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import FinalizeResult, PostAnalysisError

# Label added to PRs that originate from extraction plans.
# Checked by land_cmd.py to skip creating pending-extraction marker.
ERK_SKIP_EXTRACTION_LABEL = "erk-skip-extraction"


def is_extraction_plan(impl_dir: Path) -> bool:
    """Check if the plan in the impl folder is an extraction plan.

    Reads plan.md and checks the plan-header metadata block for plan_type: "extraction".

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if plan_type is "extraction", False otherwise (including if plan.md
        doesn't exist or metadata block is missing)
    """
    plan_file = impl_dir / "plan.md"

    if not plan_file.exists():
        return False

    plan_content = plan_file.read_text(encoding="utf-8")
    block = find_metadata_block(plan_content, "plan-header")

    if block is None:
        return False

    plan_type = block.data.get("plan_type")
    return plan_type == "extraction"


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

    # Check if this is an extraction plan
    is_extraction_origin = is_extraction_plan(impl_dir)

    # Build metadata section and combine with AI body
    metadata_section = build_pr_body_footer(
        pr_number=pr_number,
        issue_number=issue_number,
    )
    # pr_body is guaranteed non-None here (either passed in or read from file, validated above)
    assert pr_body is not None

    final_body = pr_body + metadata_section

    # Get repo root for GitHub operations
    repo_root = ops.git.get_repository_root(cwd)

    # Update PR metadata
    yield ProgressEvent("Updating PR metadata... (gh pr edit)")
    ops.github.update_pr_title_and_body(repo_root, pr_number, pr_title, final_body)
    yield ProgressEvent("PR metadata updated", style="success")

    # Add extraction skip label if this is an extraction plan
    if is_extraction_origin:
        yield ProgressEvent("Adding erk-skip-extraction label...")
        ops.github.add_label_to_pr(repo_root, pr_number, ERK_SKIP_EXTRACTION_LABEL)
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
