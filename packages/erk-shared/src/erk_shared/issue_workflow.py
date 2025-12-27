"""Shared workflow for creating worktrees from GitHub issues.

This module provides the canonical logic for preparing issues for worktree creation,
including validation, branch naming, and metadata extraction. Used by both
`erk wt create --from-issue` and `erk implement`.
"""

from dataclasses import dataclass
from datetime import datetime

from erk_shared.github.issues import IssueInfo
from erk_shared.naming import generate_issue_branch_name, sanitize_worktree_name
from erk_shared.plan_store.types import Plan, PlanState


@dataclass(frozen=True)
class IssueBranchSetup:
    """Result of preparing an issue for worktree creation.

    Attributes:
        branch_name: Git branch name (e.g., P123-fix-bug-01-15-1430)
        worktree_name: Sanitized directory name for the worktree
        plan_content: Issue body to use as plan.md content
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        issue_title: Issue title for reference
    """

    branch_name: str
    worktree_name: str
    plan_content: str
    issue_number: int
    issue_url: str
    issue_title: str


class IssueValidationError(Exception):
    """Raised when issue validation fails."""


def validate_issue_for_worktree(
    issue_info: IssueInfo,
    *,
    warn_non_open: bool = True,
) -> list[str]:
    """Validate issue is suitable for worktree creation.

    Checks that the issue has the required 'erk-plan' label and
    optionally warns about non-OPEN issues.

    Args:
        issue_info: Issue information from GitHub
        warn_non_open: Whether to generate warning for non-OPEN issues

    Returns:
        List of warning messages (empty if no warnings)

    Raises:
        IssueValidationError: If erk-plan label is missing
    """
    warnings: list[str] = []

    if "erk-plan" not in issue_info.labels:
        raise IssueValidationError(
            f"Issue #{issue_info.number} must have 'erk-plan' label.\n"
            f"To add the label:\n"
            f"  gh issue edit {issue_info.number} --add-label erk-plan"
        )

    if warn_non_open and issue_info.state != "OPEN":
        warnings.append(f"Issue #{issue_info.number} is {issue_info.state}. Proceeding anyway...")

    return warnings


def validate_plan_for_worktree(
    plan: Plan,
    *,
    warn_non_open: bool = True,
) -> list[str]:
    """Validate plan is suitable for worktree creation.

    This is the Plan-based variant of validate_issue_for_worktree,
    used when working with the plan_store abstraction.

    Checks that the plan has the required 'erk-plan' label and
    optionally warns about non-OPEN plans.

    Args:
        plan: Plan from plan_store
        warn_non_open: Whether to generate warning for non-OPEN plans

    Returns:
        List of warning messages (empty if no warnings)

    Raises:
        IssueValidationError: If erk-plan label is missing
    """
    warnings: list[str] = []

    if "erk-plan" not in plan.labels:
        raise IssueValidationError(
            f"Issue #{plan.plan_identifier} must have 'erk-plan' label.\n"
            f"To add the label:\n"
            f"  gh issue edit {plan.plan_identifier} --add-label erk-plan"
        )

    if warn_non_open and plan.state != PlanState.OPEN:
        warnings.append(
            f"Issue #{plan.plan_identifier} is {plan.state.value}. Proceeding anyway..."
        )

    return warnings


def prepare_plan_for_worktree(
    plan: Plan,
    timestamp: datetime,
) -> IssueBranchSetup:
    """Prepare plan data for worktree creation.

    This is the Plan-based variant of prepare_issue_for_worktree,
    used when working with the plan_store abstraction.

    Generates branch name and worktree name from plan metadata.
    Does NOT create the branch or worktree - just computes names.

    Args:
        plan: Plan from plan_store
        timestamp: Timestamp for branch name suffix

    Returns:
        IssueBranchSetup with computed names and plan data
    """
    # Plan uses plan_identifier (string) but we need int for issue number
    issue_number = int(plan.plan_identifier)

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
    )


def prepare_issue_for_worktree(
    issue_info: IssueInfo,
    timestamp: datetime,
) -> IssueBranchSetup:
    """Prepare issue data for worktree creation.

    Generates branch name and worktree name from issue metadata.
    Does NOT create the branch or worktree - just computes names.

    Args:
        issue_info: Validated issue information
        timestamp: Timestamp for branch name suffix

    Returns:
        IssueBranchSetup with computed names and issue data
    """
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
    )
