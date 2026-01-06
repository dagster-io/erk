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
from erk_shared.github.metadata.core import format_plan_commands_section
from erk_shared.github.metadata.plan_header import (
    format_plan_content_comment,
    format_plan_header_body,
    update_plan_header_comment_id,
)
from erk_shared.plan_utils import extract_title_from_plan

# Label configurations
_LABEL_ERK_PLAN = "erk-plan"
_LABEL_ERK_PLAN_DESC = "Implementation plan for manual execution"
_LABEL_ERK_PLAN_COLOR = "0E8A16"

_LABEL_ERK_EXTRACTION = "erk-extraction"
_LABEL_ERK_EXTRACTION_DESC = "Documentation extraction plan"
_LABEL_ERK_EXTRACTION_COLOR = "D93F0B"

_LABEL_ERK_OBJECTIVE = "erk-objective"
_LABEL_ERK_OBJECTIVE_DESC = "Multi-phase objective with roadmap"
_LABEL_ERK_OBJECTIVE_COLOR = "5319E7"


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


def create_plan_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    plan_content: str,
    *,
    title: str | None,
    plan_type: str | None,
    extra_labels: list[str] | None,
    title_suffix: str | None,
    source_plan_issues: list[int] | None,
    extraction_session_ids: list[str] | None,
    source_repo: str | None,
    objective_issue: int | None,
) -> CreatePlanIssueResult:
    """Create Schema v2/v3 plan issue with proper structure.

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
        source_repo: For cross-repo plans, the implementation repo in "owner/repo" format
        objective_issue: Optional parent objective issue number

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

    # Build issue title
    issue_title = f"{title} {title_suffix}"

    # Standard and extraction plans: metadata body + plan content in comment
    created_at = datetime.now(UTC).isoformat()
    issue_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
        worktree_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        plan_type=plan_type,
        source_plan_issues=source_plan_issues if source_plan_issues else [],
        extraction_session_ids=extraction_session_ids if extraction_session_ids else [],
        source_repo=source_repo,
        objective_issue=objective_issue,
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
        comment_id = github_issues.add_comment(repo_root, result.number, plan_comment)
    except RuntimeError as e:
        # Partial success - issue created but comment failed
        return CreatePlanIssueResult(
            success=False,
            issue_number=result.number,
            issue_url=result.url,
            title=title,
            error=f"Issue #{result.number} created but failed to add plan comment: {e}",
        )

    # Step 6: Update issue body with plan_comment_id for direct lookup
    updated_body = update_plan_header_comment_id(issue_body, comment_id)

    # Step 7: Add commands section for standard plans only (not extraction)
    if plan_type != "extraction":
        commands_section = format_plan_commands_section(result.number)
        updated_body = updated_body + "\n\n" + commands_section

    github_issues.update_issue_body(repo_root, result.number, updated_body)

    return CreatePlanIssueResult(
        success=True,
        issue_number=result.number,
        issue_url=result.url,
        title=title,
        error=None,
    )


def create_objective_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    plan_content: str,
    *,
    title: str | None,
    extra_labels: list[str] | None,
) -> CreatePlanIssueResult:
    """Create objective issue with erk-plan + erk-objective labels.

    Objectives are roadmaps, not implementation plans. They have:
    - Labels: erk-plan + erk-objective (like extraction has erk-plan + erk-extraction)
    - Plan content directly in body (no metadata block)
    - No comment (content is in body)
    - No title suffix
    - No commands section

    Args:
        github_issues: GitHubIssues interface (real, fake, or dry-run)
        repo_root: Repository root directory
        plan_content: The full plan markdown content
        title: Optional title (extracted from H1 if None)
        extra_labels: Additional labels beyond erk-plan and erk-objective

    Returns:
        CreatePlanIssueResult with success status and details

    Note:
        Does NOT raise exceptions. All errors returned in result.
    """
    # Step 1: Validate authentication (username not used in objective body but validates gh CLI)
    if github_issues.get_current_username() is None:
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

    # Step 3: Build labels - objectives use erk-plan + erk-objective (like extraction)
    labels = [_LABEL_ERK_PLAN, _LABEL_ERK_OBJECTIVE]

    # Add any extra labels
    if extra_labels:
        for label in extra_labels:
            if label not in labels:
                labels.append(label)

    # Ensure labels exist
    label_errors = _ensure_labels_exist(github_issues, repo_root, labels, None)
    if label_errors:
        return CreatePlanIssueResult(
            success=False,
            issue_number=None,
            issue_url=None,
            title=title,
            error=label_errors,
        )

    # Step 4: Create issue with plan content directly in body (no metadata)
    try:
        result = github_issues.create_issue(
            repo_root=repo_root,
            title=title,  # No suffix for objectives
            body=plan_content.strip(),
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

    # No comment, no commands section for objectives
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
            elif label == _LABEL_ERK_OBJECTIVE:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_OBJECTIVE,
                    description=_LABEL_ERK_OBJECTIVE_DESC,
                    color=_LABEL_ERK_OBJECTIVE_COLOR,
                )
            # Extra labels are assumed to already exist
    except RuntimeError as e:
        return f"Failed to ensure labels exist: {e}"

    return None


@dataclass(frozen=True)
class LabelDefinition:
    """Definition of a label with its properties."""

    name: str
    description: str
    color: str


def get_erk_label_definitions() -> list[LabelDefinition]:
    """Get all erk label definitions.

    Returns list of LabelDefinition for all erk labels (erk-plan,
    erk-extraction, erk-objective). Used by init command to set up
    labels in target issue repositories.
    """
    return [
        LabelDefinition(
            name=_LABEL_ERK_PLAN,
            description=_LABEL_ERK_PLAN_DESC,
            color=_LABEL_ERK_PLAN_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_ERK_EXTRACTION,
            description=_LABEL_ERK_EXTRACTION_DESC,
            color=_LABEL_ERK_EXTRACTION_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_ERK_OBJECTIVE,
            description=_LABEL_ERK_OBJECTIVE_DESC,
            color=_LABEL_ERK_OBJECTIVE_COLOR,
        ),
    ]


def get_required_erk_labels() -> list[LabelDefinition]:
    """Get erk labels required for doctor check.

    Returns subset of labels checked by doctor command. Excludes
    erk-extraction (optional, for documentation workflows).

    Used by doctor command to verify required labels exist.
    """
    return [
        LabelDefinition(
            name=_LABEL_ERK_PLAN,
            description=_LABEL_ERK_PLAN_DESC,
            color=_LABEL_ERK_PLAN_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_ERK_OBJECTIVE,
            description=_LABEL_ERK_OBJECTIVE_DESC,
            color=_LABEL_ERK_OBJECTIVE_COLOR,
        ),
    ]
