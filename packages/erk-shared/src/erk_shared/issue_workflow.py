"""Shared workflow for creating worktrees from GitHub issues.

This module provides the canonical logic for preparing issues for worktree creation,
including validation, branch naming, and metadata extraction. Used by both
`erk wt create --from-plan` and `erk implement`.
"""

from dataclasses import dataclass
from datetime import datetime

from erk_shared.github.issues import IssueInfo
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
        warnings: List of warning messages (e.g., non-OPEN issue)
    """

    branch_name: str
    worktree_name: str
    plan_content: str
    issue_number: int
    issue_url: str
    issue_title: str
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
    warn_non_open: bool = True,
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

    branch_name = generate_issue_branch_name(
        issue_number,
        plan.title,
        timestamp,
    )
    worktree_name = sanitize_worktree_name(branch_name)

    return IssueBranchSetup(
        branch_name=branch_name,
        worktree_name=worktree_name,
        plan_content=plan.body,
        issue_number=issue_number,
        issue_url=plan.url,
        issue_title=plan.title,
        warnings=tuple(warnings),
    )


def prepare_issue_for_worktree(
    issue_info: IssueInfo,
    timestamp: datetime,
    *,
    warn_non_open: bool = True,
) -> PrepareIssueResult:
    """Prepare and validate issue data for worktree creation.

    Validates the issue has required labels and generates branch/worktree names.
    Does NOT create the branch or worktree - just validates and computes names.

    Args:
        issue_info: Issue information from GitHub
        timestamp: Timestamp for branch name suffix
        warn_non_open: Whether to include warning for non-OPEN issues

    Returns:
        IssueBranchSetup on success, IssueValidationFailed on validation failure
    """
    # Validate erk-plan label
    if "erk-plan" not in issue_info.labels:
        return IssueValidationFailed(
            f"Issue #{issue_info.number} must have 'erk-plan' label.\n"
            f"To add the label:\n"
            f"  gh issue edit {issue_info.number} --add-label erk-plan"
        )

    # Collect warnings
    warnings: list[str] = []
    if warn_non_open and issue_info.state != "OPEN":
        warnings.append(f"Issue #{issue_info.number} is {issue_info.state}. Proceeding anyway...")

    branch_name = generate_issue_branch_name(
        issue_info.number,
        issue_info.title,
        timestamp,
    )
    worktree_name = sanitize_worktree_name(branch_name)

    return IssueBranchSetup(
        branch_name=branch_name,
        worktree_name=worktree_name,
        plan_content=issue_info.body,
        issue_number=issue_info.number,
        issue_url=issue_info.url,
        issue_title=issue_info.title,
        warnings=tuple(warnings),
    )
