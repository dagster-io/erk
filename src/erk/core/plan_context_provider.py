"""Plan context provider for PR description generation.

This module provides plan context for branches linked to erk-plan issues,
enabling more accurate PR descriptions that understand the "why" behind changes.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
    extract_plan_header_objective_issue,
)
from erk_shared.naming import extract_leading_issue_number


@dataclass(frozen=True)
class PlanContext:
    """Context from an erk-plan issue for PR generation.

    Attributes:
        issue_number: The erk-plan issue number
        plan_content: The full plan markdown content
        objective_summary: Optional summary of the parent objective (e.g., "Objective #123: Title")
    """

    issue_number: int
    plan_content: str
    objective_summary: str | None


class PlanContextProvider:
    """Provides plan context for branches linked to erk-plan issues.

    This provider extracts plan content from GitHub issues when a branch
    follows the naming convention P{issue_number}-{slug} or {issue_number}-{slug}.
    """

    def __init__(self, github_issues: GitHubIssues) -> None:
        """Initialize the provider.

        Args:
            github_issues: Gateway for GitHub issue operations
        """
        self._github_issues = github_issues

    def get_plan_context(
        self,
        *,
        repo_root: Path,
        branch_name: str,
    ) -> PlanContext | None:
        """Get plan context for a branch, if available.

        Attempts to fetch plan context by:
        1. Extracting issue number from branch name (P5763-fix-... -> 5763)
        2. Fetching the issue body
        3. Extracting plan_comment_id from metadata
        4. Fetching the comment and extracting plan content
        5. Optionally getting objective title if linked

        Returns None on any failure, allowing graceful degradation for
        branches not linked to plans.

        Args:
            repo_root: Repository root path
            branch_name: Current branch name

        Returns:
            PlanContext if plan found, None otherwise
        """
        # Step 1: Extract issue number from branch name
        issue_number = extract_leading_issue_number(branch_name)
        if issue_number is None:
            return None

        # Step 2: Fetch the issue body
        try:
            issue_info = self._github_issues.get_issue(repo_root, issue_number)
        except RuntimeError:
            # Issue doesn't exist or API error - graceful degradation
            return None

        # Step 3: Extract plan_comment_id from metadata
        comment_id = extract_plan_header_comment_id(issue_info.body)
        if comment_id is None:
            # Not an erk-plan issue or no plan comment yet
            return None

        # Step 4: Fetch the comment and extract plan content
        try:
            comment_body = self._github_issues.get_comment_by_id(repo_root, comment_id)
        except RuntimeError:
            # Comment not found or API error
            return None

        plan_content = extract_plan_from_comment(comment_body)
        if plan_content is None:
            # Comment doesn't contain plan content
            return None

        # Step 5: Optionally get objective title if linked
        objective_summary = self._get_objective_summary(
            repo_root=repo_root,
            issue_body=issue_info.body,
        )

        return PlanContext(
            issue_number=issue_number,
            plan_content=plan_content,
            objective_summary=objective_summary,
        )

    def _get_objective_summary(
        self,
        *,
        repo_root: Path,
        issue_body: str,
    ) -> str | None:
        """Get objective summary if plan is linked to an objective.

        Args:
            repo_root: Repository root path
            issue_body: Plan issue body

        Returns:
            Summary like "Objective #123: Title" if linked, None otherwise
        """
        objective_issue = extract_plan_header_objective_issue(issue_body)
        if objective_issue is None:
            return None

        try:
            objective_info = self._github_issues.get_issue(repo_root, objective_issue)
            return f"Objective #{objective_issue}: {objective_info.title}"
        except RuntimeError:
            # Objective issue not found or API error
            return None
