"""Shared workflow for preparing plans for worktree creation.

This module provides the canonical logic for preparing plans for worktree creation,
including validation, branch naming, and metadata extraction. Used by both
`erk wt create --from-plan` and `erk implement`.
"""

from dataclasses import dataclass
from datetime import datetime

from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.naming import (
    InvalidWorktreeName,
    sanitize_worktree_name,
    validate_worktree_name,
)
from erk_shared.plan_store.types import Plan, PlanState


@dataclass(frozen=True)
class PlanBranchSetup:
    """Result of successfully preparing a plan for worktree creation.

    Attributes:
        branch_name: Git branch name (e.g., plnd/fix-bug-01-15-1430)
        worktree_name: Sanitized directory name for the worktree
        plan_content: Plan body to use as plan.md content
        plan_number: Plan number
        issue_url: Full GitHub issue URL
        issue_title: Issue title for reference
        objective_issue: Linked objective issue number, or None if not linked
        warnings: List of warning messages (e.g., non-OPEN plan)
    """

    branch_name: str
    worktree_name: str
    plan_content: str
    plan_number: int
    issue_url: str
    issue_title: str
    objective_issue: int | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanValidationFailed:
    """Result when plan validation fails.

    Attributes:
        message: User-facing error message explaining the failure
    """

    message: str


# Union type for prepare results - clients handle both cases
PreparePlanResult = PlanBranchSetup | PlanValidationFailed


def prepare_plan_for_worktree(
    plan: Plan,
    timestamp: datetime,
    *,
    warn_non_open: bool,
) -> PreparePlanResult:
    """Prepare and validate plan data for worktree creation.

    Validates the plan has required labels and generates branch/worktree names.
    Does NOT create the branch or worktree - just validates and computes names.

    Args:
        plan: Plan from plan_store
        timestamp: Timestamp for branch name suffix
        warn_non_open: Whether to include warning for non-OPEN plans

    Returns:
        PlanBranchSetup on success, PlanValidationFailed on validation failure
    """
    # Validate erk-plan label
    if "erk-plan" not in plan.labels:
        return PlanValidationFailed(
            f"Plan #{plan.pr_identifier} must have 'erk-plan' label.\n"
            f"To add the label:\n"
            f"  gh issue edit {plan.pr_identifier} --add-label erk-plan"
        )

    # Validate plan_identifier can be converted to int (LBYL)
    if not plan.pr_identifier.isdigit():
        return PlanValidationFailed(
            f"Plan identifier '{plan.pr_identifier}' is not a valid plan number. "
            "Expected a numeric GitHub issue number."
        )
    plan_number = int(plan.pr_identifier)

    # Collect warnings
    warnings: list[str] = []
    if warn_non_open and plan.state != PlanState.OPEN:
        warnings.append(f"Plan #{plan.pr_identifier} is {plan.state.value}. Proceeding anyway...")

    # Branch name comes from plan-header metadata (set by plan_save)
    existing_branch = plan.header_fields.get(BRANCH_NAME)
    if not isinstance(existing_branch, str) or len(existing_branch) == 0:
        return PlanValidationFailed(
            f"Draft PR plan #{plan.pr_identifier} is missing required "
            f"branch_name in plan-header metadata. "
            f"This indicates the plan was not saved correctly."
        )
    branch_name = existing_branch
    # Validate worktree name — agent-facing backpressure gate.
    # sanitize_worktree_name() produces the candidate name from the branch;
    # validate_worktree_name() confirms it is already clean.
    worktree_name = sanitize_worktree_name(branch_name)
    wt_validation = validate_worktree_name(worktree_name)
    if isinstance(wt_validation, InvalidWorktreeName):
        return PlanValidationFailed(
            f"Generated worktree name failed validation.\n{wt_validation.format_message()}"
        )
    worktree_name = wt_validation.name

    return PlanBranchSetup(
        branch_name=branch_name,
        worktree_name=worktree_name,
        plan_content=plan.body,
        plan_number=plan_number,
        issue_url=plan.url,
        issue_title=plan.title,
        objective_issue=plan.objective_id,
        warnings=tuple(warnings),
    )
