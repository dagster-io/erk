"""Shared workflow for creating worktrees from plans.

This module provides the canonical logic for preparing plans for worktree creation,
including validation, branch naming, and metadata extraction. Used by both
`erk wt create --from-plan` and `erk implement`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.naming import generate_issue_branch_name, sanitize_worktree_name
from erk_shared.plan_store.types import Plan, PlanState


@dataclass(frozen=True)
class IssueBranchSetup:
    """Result of successfully preparing an issue for worktree creation.

    Attributes:
        branch_name: Git branch name (e.g., P123-fix-bug-01-15-1430)
        worktree_name: Sanitized directory name for the worktree
        plan_content: Issue body to use as plan.md content
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        issue_title: Issue title for reference
        objective_issue: Linked objective issue number, or None if not linked
        warnings: List of warning messages (e.g., non-OPEN issue)
    """

    branch_name: str
    worktree_name: str
    plan_content: str
    issue_number: int
    issue_url: str
    issue_title: str
    objective_issue: int | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class IssueValidationFailed:
    """Result when issue validation fails.

    Attributes:
        message: User-facing error message explaining the failure
    """

    message: str


# Union type for prepare results - clients handle both cases
PrepareIssueResult = IssueBranchSetup | IssueValidationFailed


def prepare_plan_for_worktree(
    plan: Plan,
    timestamp: datetime,
    *,
    plan_backend: Literal["draft_pr", "github"],
    warn_non_open: bool,
) -> PrepareIssueResult:
    """Prepare and validate plan data for worktree creation.

    Validates the plan has required labels and generates branch/worktree names.
    Does NOT create the branch or worktree - just validates and computes names.

    Args:
        plan: Plan from plan_store
        timestamp: Timestamp for branch name suffix
        warn_non_open: Whether to include warning for non-OPEN plans

    Returns:
        IssueBranchSetup on success, IssueValidationFailed on validation failure
    """
    # Validate erk-plan label
    if "erk-plan" not in plan.labels:
        return IssueValidationFailed(
            f"Issue #{plan.plan_identifier} must have 'erk-plan' label.\n"
            f"To add the label:\n"
            f"  gh issue edit {plan.plan_identifier} --add-label erk-plan"
        )

    # Validate plan_identifier can be converted to int (LBYL)
    if not plan.plan_identifier.isdigit():
        return IssueValidationFailed(
            f"Plan identifier '{plan.plan_identifier}' is not a valid issue number. "
            "Expected a numeric GitHub issue number."
        )
    issue_number = int(plan.plan_identifier)

    # Collect warnings
    warnings: list[str] = []
    if warn_non_open and plan.state != PlanState.OPEN:
        warnings.append(
            f"Issue #{plan.plan_identifier} is {plan.state.value}. Proceeding anyway..."
        )

    # PLAN_BACKEND_SPLIT: draft-PR backend reuses plan-header branch;
    # issue backend generates fresh branch
    # Two code paths based on backend:
    # - Draft PR backend: branch always exists in plan-header (set by plan_save)
    # - Issue backend: branch is always generated fresh
    if plan_backend == "draft_pr":
        existing_branch = plan.header_fields.get(BRANCH_NAME)
        if not isinstance(existing_branch, str) or len(existing_branch) == 0:
            return IssueValidationFailed(
                f"Draft PR plan #{plan.plan_identifier} is missing required "
                f"branch_name in plan-header metadata. "
                f"This indicates the plan was not saved correctly."
            )
        branch_name = existing_branch
    else:
        branch_name = generate_issue_branch_name(
            issue_number,
            plan.title,
            timestamp,
            objective_id=plan.objective_id,
        )
    worktree_name = sanitize_worktree_name(branch_name)

    return IssueBranchSetup(
        branch_name=branch_name,
        worktree_name=worktree_name,
        plan_content=plan.body,
        issue_number=issue_number,
        issue_url=plan.url,
        issue_title=plan.title,
        objective_issue=plan.objective_id,
        warnings=tuple(warnings),
    )
