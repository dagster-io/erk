"""Create Schema v2 plan issues with metadata-only body and plan content comment.

This module consolidates the 6-step workflow for creating plan issues:
1. Get GitHub username (fail if not authenticated)
2. Extract title from plan H1 (or use provided)
3. Ensure all required labels exist
4. Create issue with metadata-only body
5. Add first comment with plan content
6. Handle partial failures (issue created but comment failed)

All callers should use create_plan_issue() instead of duplicating this logic.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.metadata import (
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.plan_utils import extract_title_from_plan

# Label configurations
_LABEL_ERK_PLAN = "erk-plan"
_LABEL_ERK_PLAN_DESC = "Implementation plan for manual execution"
_LABEL_ERK_PLAN_COLOR = "0E8A16"

_LABEL_ERK_EXTRACTION = "erk-extraction"
_LABEL_ERK_EXTRACTION_DESC = "Documentation extraction plan"
_LABEL_ERK_EXTRACTION_COLOR = "D93F0B"


@dataclass(frozen=True)
class CreatePlanIssueResult:
    """Result of creating a Schema v2 plan issue.

    Attributes:
        success: Whether the entire operation completed successfully
        issue_number: Issue number if created (may be set even on failure if
            partial success - issue created but comment failed)
        issue_url: Issue URL if created
        title: The title used for the issue (extracted or provided)
        error: Error message if failed, None if success
    """

    success: bool
    issue_number: int | None
    issue_url: str | None
    title: str
    error: str | None


@dataclass(frozen=True)
class UpdatePlanIssueResult:
    """Result of updating a Schema v2 plan issue's content.

    Attributes:
        success: Whether the update completed successfully
        issue_number: The issue number that was updated
        issue_url: The issue URL (for display purposes)
        error: Error message if failed, None if success
    """

    success: bool
    issue_number: int
    issue_url: str | None
    error: str | None


def create_plan_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    plan_content: str,
    *,
    title: str | None = None,
    plan_type: str | None = None,
    extra_labels: list[str] | None = None,
    title_suffix: str | None = None,
    source_plan_issues: list[int] | None = None,
    extraction_session_ids: list[str] | None = None,
) -> CreatePlanIssueResult:
    """Create Schema v2 plan issue with proper structure.

    Handles the complete workflow:
    1. Get GitHub username (fail if not authenticated)
    2. Extract title from plan H1 (or use provided)
    3. Ensure all labels exist
    4. Create issue with metadata-only body
    5. Add first comment with plan-body block

    Args:
        github_issues: GitHubIssues interface (real, fake, or dry-run)
        repo_root: Repository root directory
        plan_content: The full plan markdown content
        title: Optional title (extracted from H1 if None)
        plan_type: Optional type discriminator ("extraction" or None for standard)
        extra_labels: Additional labels beyond erk-plan
        title_suffix: Suffix for issue title (default: "[erk-plan]" or "[erk-extraction]")
        source_plan_issues: For extraction plans, list of source issue numbers
        extraction_session_ids: For extraction plans, list of session IDs analyzed

    Returns:
        CreatePlanIssueResult with success status and details

    Note:
        Does NOT raise exceptions. All errors returned in result.
        Partial success (issue created, comment failed) is possible.
    """
    # Step 1: Get GitHub username
    username = github_issues.get_current_username()
    if username is None:
        return CreatePlanIssueResult(
            success=False,
            issue_number=None,
            issue_url=None,
            title="",
            error="Could not get GitHub username (gh CLI not authenticated?)",
        )

    # Step 2: Extract or use provided title
    if title is None:
        title = extract_title_from_plan(plan_content)

    # Step 3: Determine labels based on plan_type
    labels = [_LABEL_ERK_PLAN]
    if plan_type == "extraction":
        labels.append(_LABEL_ERK_EXTRACTION)

    # Add any extra labels
    if extra_labels:
        for label in extra_labels:
            if label not in labels:
                labels.append(label)

    # Ensure labels exist
    label_errors = _ensure_labels_exist(github_issues, repo_root, labels, plan_type)
    if label_errors:
        return CreatePlanIssueResult(
            success=False,
            issue_number=None,
            issue_url=None,
            title=title,
            error=label_errors,
        )

    # Step 4: Determine title suffix
    if title_suffix is None:
        if plan_type == "extraction":
            title_suffix = "[erk-extraction]"
        else:
            title_suffix = "[erk-plan]"

    issue_title = f"{title} {title_suffix}"

    # Prepare metadata body
    created_at = datetime.now(UTC).isoformat()
    issue_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
        plan_type=plan_type,
        source_plan_issues=source_plan_issues if source_plan_issues else [],
        extraction_session_ids=extraction_session_ids if extraction_session_ids else [],
    )

    # Create issue
    try:
        result = github_issues.create_issue(
            repo_root=repo_root,
            title=issue_title,
            body=issue_body,
            labels=labels,
        )
    except RuntimeError as e:
        return CreatePlanIssueResult(
            success=False,
            issue_number=None,
            issue_url=None,
            title=title,
            error=f"Failed to create GitHub issue: {e}",
        )

    # Step 5: Add first comment with plan content
    plan_comment = format_plan_content_comment(plan_content.strip())
    try:
        github_issues.add_comment(repo_root, result.number, plan_comment)
    except RuntimeError as e:
        # Partial success - issue created but comment failed
        return CreatePlanIssueResult(
            success=False,
            issue_number=result.number,
            issue_url=result.url,
            title=title,
            error=f"Issue #{result.number} created but failed to add plan comment: {e}",
        )

    return CreatePlanIssueResult(
        success=True,
        issue_number=result.number,
        issue_url=result.url,
        title=title,
        error=None,
    )


def _ensure_labels_exist(
    github_issues: GitHubIssues,
    repo_root: Path,
    labels: list[str],
    plan_type: str | None,
) -> str | None:
    """Ensure all required labels exist in the repository.

    Args:
        github_issues: GitHubIssues interface
        repo_root: Repository root directory
        labels: List of label names to ensure exist
        plan_type: Plan type for determining label descriptions

    Returns:
        Error message if failed, None if success
    """
    try:
        for label in labels:
            if label == _LABEL_ERK_PLAN:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_PLAN,
                    description=_LABEL_ERK_PLAN_DESC,
                    color=_LABEL_ERK_PLAN_COLOR,
                )
            elif label == _LABEL_ERK_EXTRACTION:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_EXTRACTION,
                    description=_LABEL_ERK_EXTRACTION_DESC,
                    color=_LABEL_ERK_EXTRACTION_COLOR,
                )
            # Extra labels are assumed to already exist
    except RuntimeError as e:
        return f"Failed to ensure labels exist: {e}"

    return None


def update_plan_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    issue_number: int,
    plan_content: str,
) -> UpdatePlanIssueResult:
    """Update the plan content in an existing issue's first comment.

    Schema v2 plan issues store the plan content in the first comment,
    not in the issue body. This function:
    1. Gets the issue comments
    2. Finds the first comment (plan content per Schema v2)
    3. Updates that comment with new content

    Args:
        github_issues: GitHubIssues interface (real, fake, or dry-run)
        repo_root: Repository root directory
        issue_number: Issue number to update
        plan_content: The new plan markdown content

    Returns:
        UpdatePlanIssueResult with success status and details

    Note:
        Does NOT raise exceptions. All errors returned in result.
    """
    # Step 1: Get the issue to verify it exists and get the URL
    try:
        issue = github_issues.get_issue(repo_root, issue_number)
    except RuntimeError as e:
        return UpdatePlanIssueResult(
            success=False,
            issue_number=issue_number,
            issue_url=None,
            error=f"Failed to get issue #{issue_number}: {e}",
        )

    # Step 2: Get issue comments
    try:
        comments = github_issues.get_issue_comments_with_urls(repo_root, issue_number)
    except RuntimeError as e:
        return UpdatePlanIssueResult(
            success=False,
            issue_number=issue_number,
            issue_url=issue.url,
            error=f"Failed to get comments for issue #{issue_number}: {e}",
        )

    # Step 3: Find first comment (plan content per Schema v2)
    if not comments:
        return UpdatePlanIssueResult(
            success=False,
            issue_number=issue_number,
            issue_url=issue.url,
            error=f"Issue #{issue_number} has no comments (expected Schema v2 plan comment)",
        )

    first_comment = comments[0]

    # Step 4: Update the comment with new plan content
    plan_comment = format_plan_content_comment(plan_content.strip())
    try:
        github_issues.update_comment(repo_root, first_comment.id, plan_comment)
    except RuntimeError as e:
        return UpdatePlanIssueResult(
            success=False,
            issue_number=issue_number,
            issue_url=issue.url,
            error=f"Failed to update comment on issue #{issue_number}: {e}",
        )

    return UpdatePlanIssueResult(
        success=True,
        issue_number=issue_number,
        issue_url=issue.url,
        error=None,
    )
