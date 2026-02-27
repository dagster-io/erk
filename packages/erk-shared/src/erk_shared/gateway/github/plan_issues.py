"""GitHub issue creation for objectives and label management.

This module contains:
- create_objective_issue(): Create objective issues with roadmap metadata
- Label management utilities (definitions, ensuring labels exist)
- CreatePlanIssueResult: Result type shared by objective issue creation

Plan creation now uses create_plan_draft_pr() from plan_store.create_plan_draft_pr.
"""

from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.core import (
    create_objective_header_block,
    extract_raw_metadata_blocks,
    format_objective_content_comment,
    render_metadata_block,
    update_objective_header_comment_id,
)
from erk_shared.gateway.github.metadata.roadmap import (
    parse_roadmap_frontmatter,
    render_roadmap_block_inner,
)
from erk_shared.gateway.github.types import BodyText
from erk_shared.gateway.time.abc import Time
from erk_shared.naming import InvalidObjectiveSlug, validate_objective_slug
from erk_shared.plan_utils import extract_title_from_plan

# Label configurations
_LABEL_ERK_PLAN = "erk-plan"
_LABEL_ERK_PLAN_DESC = "Implementation plan for manual execution"
_LABEL_ERK_PLAN_COLOR = "0E8A16"

_LABEL_ERK_PR = "erk-pr"
_LABEL_ERK_PR_DESC = "Plan managed as a draft PR"
_LABEL_ERK_PR_COLOR = "1D76DB"

_LABEL_ERK_LEARN = "erk-learn"
_LABEL_ERK_LEARN_DESC = "Documentation learning plan"
_LABEL_ERK_LEARN_COLOR = "D93F0B"

_LABEL_ERK_OBJECTIVE = "erk-objective"
_LABEL_ERK_OBJECTIVE_DESC = "Multi-phase objective with roadmap"
_LABEL_ERK_OBJECTIVE_COLOR = "5319E7"

_LABEL_NO_CHANGES = "no-changes"
_LABEL_NO_CHANGES_DESC = "Implementation produced no code changes"
_LABEL_NO_CHANGES_COLOR = "FFA500"  # Orange - attention needed


@dataclass(frozen=True)
class CreatePlanIssueResult:
    """Result of creating a Schema v2 plan issue.

    Attributes:
        success: Whether the entire operation completed successfully
        plan_number: Plan number if created (may be set even on failure if
            partial success - issue created but comment failed)
        plan_url: Plan URL if created
        title: The title used for the issue (extracted or provided)
        error: Error message if failed, None if success
    """

    success: bool
    plan_number: int | None
    plan_url: str | None
    title: str
    error: str | None


def _build_objective_roadmap_block(plan_content: str) -> str | None:
    """Extract existing objective-roadmap metadata block from plan content.

    Looks for a pre-existing ``objective-roadmap`` metadata block in
    ``<details>`` format. The objective-create skill is responsible for
    producing this block in the plan content.

    Args:
        plan_content: The full objective markdown content

    Returns:
        Rendered objective-roadmap metadata block string, or None if no
        valid v2 roadmap block found.
    """
    raw_blocks = extract_raw_metadata_blocks(plan_content)
    roadmap_block = next((block for block in raw_blocks if block.key == "objective-roadmap"), None)

    if roadmap_block is None:
        return None

    if not roadmap_block.body.strip().startswith("<details>"):
        return None

    # Validate the block parses correctly
    steps = parse_roadmap_frontmatter(roadmap_block.body)
    if steps is None:
        return None

    # Re-render to normalize format
    inner = render_roadmap_block_inner(steps)

    return (
        "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->\n"
        "<!-- erk:metadata-block:objective-roadmap -->\n"
        f"{inner}\n"
        "<!-- /erk:metadata-block:objective-roadmap -->"
    )


def create_objective_issue(
    github_issues: GitHubIssues,
    repo_root: Path,
    plan_content: str,
    *,
    time: Time,
    title: str | None,
    extra_labels: list[str] | None,
    slug: str | None,
) -> CreatePlanIssueResult:
    """Create objective issue with v2 format: metadata body + content comment.

    Objectives use the same pattern as plans:
    - Body: objective-header metadata block + objective-roadmap block (if roadmap exists)
    - First comment: objective content wrapped in objective-body metadata block
    - Labels: erk-objective (NOT erk-plan)
    - No title suffix, no commands section

    Args:
        github_issues: GitHubIssues interface (real, fake, or dry-run)
        repo_root: Repository root directory
        plan_content: The full objective markdown content
        title: Optional title (extracted from H1 if None)
        extra_labels: Additional labels beyond erk-objective
        slug: Optional short kebab-case identifier (validated, not transformed)

    Returns:
        CreatePlanIssueResult with success status and details

    Note:
        Does NOT raise exceptions. All errors returned in result.
    """
    # Step 1: Get GitHub username
    username = github_issues.get_current_username()
    if username is None:
        return CreatePlanIssueResult(
            success=False,
            plan_number=None,
            plan_url=None,
            title="",
            error="Could not get GitHub username (gh CLI not authenticated?)",
        )

    # Step 2: Extract or use provided title
    if title is None:
        title = extract_title_from_plan(plan_content)

    # Step 2b: Validate slug if provided (gate - reject invalid, don't transform)
    if slug is not None:
        slug_result = validate_objective_slug(slug)
        if isinstance(slug_result, InvalidObjectiveSlug):
            return CreatePlanIssueResult(
                success=False,
                plan_number=None,
                plan_url=None,
                title=title,
                error=slug_result.message,
            )

    # Step 3: Build labels - objectives only use erk-objective (NOT erk-plan)
    labels = [_LABEL_ERK_OBJECTIVE]

    # Add any extra labels
    if extra_labels:
        for label in extra_labels:
            if label not in labels:
                labels.append(label)

    # Ensure labels exist
    label_errors = _ensure_labels_exist(github_issues, repo_root, labels)
    if label_errors:
        return CreatePlanIssueResult(
            success=False,
            plan_number=None,
            plan_url=None,
            title=title,
            error=label_errors,
        )

    # Step 4: Build issue body with metadata blocks
    created_at = time.now().replace(tzinfo=UTC).isoformat()
    header_block = create_objective_header_block(
        created_at=created_at,
        created_by=username,
        objective_comment_id=None,
        slug=slug,
    )
    issue_body = render_metadata_block(header_block)

    # Add roadmap block if plan content has roadmap data
    roadmap_block_content = _build_objective_roadmap_block(plan_content)
    if roadmap_block_content is not None:
        issue_body = issue_body + "\n\n" + roadmap_block_content

    # Step 5: Create issue
    try:
        result = github_issues.create_issue(
            repo_root=repo_root,
            title=title,  # No suffix for objectives
            body=issue_body,
            labels=labels,
        )
    except RuntimeError as e:
        return CreatePlanIssueResult(
            success=False,
            plan_number=None,
            plan_url=None,
            title=title,
            error=f"Failed to create GitHub issue: {e}",
        )

    # Step 6: Add first comment with objective content
    objective_comment = format_objective_content_comment(plan_content)
    try:
        comment_id = github_issues.add_comment(repo_root, result.number, objective_comment)
    except RuntimeError as e:
        # Partial success - issue created but comment failed
        return CreatePlanIssueResult(
            success=False,
            plan_number=result.number,
            plan_url=result.url,
            title=title,
            error=f"Issue #{result.number} created but failed to add objective comment: {e}",
        )

    # Step 7: Update issue body with objective_comment_id
    updated_body = update_objective_header_comment_id(issue_body, comment_id)
    github_issues.update_issue_body(repo_root, result.number, BodyText(content=updated_body))

    return CreatePlanIssueResult(
        success=True,
        plan_number=result.number,
        plan_url=result.url,
        title=title,
        error=None,
    )


def _ensure_labels_exist(
    github_issues: GitHubIssues,
    repo_root: Path,
    labels: list[str],
) -> str | None:
    """Ensure all required labels exist in the repository.

    Args:
        github_issues: GitHubIssues interface
        repo_root: Repository root directory
        labels: List of label names to ensure exist

    Returns:
        Error message if failed, None if success
    """
    try:
        for label in labels:
            if label == _LABEL_ERK_PR:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_PR,
                    description=_LABEL_ERK_PR_DESC,
                    color=_LABEL_ERK_PR_COLOR,
                )
            elif label == _LABEL_ERK_PLAN:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_PLAN,
                    description=_LABEL_ERK_PLAN_DESC,
                    color=_LABEL_ERK_PLAN_COLOR,
                )
            elif label == _LABEL_ERK_LEARN:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_LEARN,
                    description=_LABEL_ERK_LEARN_DESC,
                    color=_LABEL_ERK_LEARN_COLOR,
                )
            elif label == _LABEL_ERK_OBJECTIVE:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_ERK_OBJECTIVE,
                    description=_LABEL_ERK_OBJECTIVE_DESC,
                    color=_LABEL_ERK_OBJECTIVE_COLOR,
                )
            elif label == _LABEL_NO_CHANGES:
                github_issues.ensure_label_exists(
                    repo_root=repo_root,
                    label=_LABEL_NO_CHANGES,
                    description=_LABEL_NO_CHANGES_DESC,
                    color=_LABEL_NO_CHANGES_COLOR,
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
    erk-learn, erk-objective, no-changes). Used by init command to set up
    labels in target issue repositories.
    """
    return [
        LabelDefinition(
            name=_LABEL_ERK_PR,
            description=_LABEL_ERK_PR_DESC,
            color=_LABEL_ERK_PR_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_ERK_PLAN,
            description=_LABEL_ERK_PLAN_DESC,
            color=_LABEL_ERK_PLAN_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_ERK_LEARN,
            description=_LABEL_ERK_LEARN_DESC,
            color=_LABEL_ERK_LEARN_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_ERK_OBJECTIVE,
            description=_LABEL_ERK_OBJECTIVE_DESC,
            color=_LABEL_ERK_OBJECTIVE_COLOR,
        ),
        LabelDefinition(
            name=_LABEL_NO_CHANGES,
            description=_LABEL_NO_CHANGES_DESC,
            color=_LABEL_NO_CHANGES_COLOR,
        ),
    ]


def get_required_erk_labels() -> list[LabelDefinition]:
    """Get erk labels required for doctor check.

    Returns subset of labels checked by doctor command. Excludes
    erk-learn (optional, for documentation workflows).

    Used by doctor command to verify required labels exist.
    """
    return [
        LabelDefinition(
            name=_LABEL_ERK_PR,
            description=_LABEL_ERK_PR_DESC,
            color=_LABEL_ERK_PR_COLOR,
        ),
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
