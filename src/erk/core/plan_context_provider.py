"""Plan context provider for PR description generation.

This module provides plan context for branches linked to erk-plan issues,
enabling more accurate PR descriptions that understand the "why" behind changes.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.naming import extract_leading_issue_number
from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import PlanNotFound


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

    Uses PlanStore for plan fetching. GitHubIssues is retained solely for
    objective title lookup (objectives are issues, not plans).
    """

    def __init__(self, *, plan_store: PlanStore, github_issues: GitHubIssues) -> None:
        self._plan_store = plan_store
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
        2. Fetching the plan via PlanStore
        3. Optionally getting objective title if linked

        Returns None on any failure, allowing graceful degradation for
        branches not linked to plans.

        Args:
            repo_root: Repository root path
            branch_name: Current branch name

        Returns:
            PlanContext if plan found, None otherwise
        """
        issue_number = extract_leading_issue_number(branch_name)
        if issue_number is None:
            return None

        result = self._plan_store.get_plan(repo_root, str(issue_number))
        if isinstance(result, PlanNotFound):
            return None

        objective_summary = self._get_objective_summary(
            repo_root=repo_root,
            objective_id=result.objective_id,
        )

        return PlanContext(
            issue_number=issue_number,
            plan_content=result.body,
            objective_summary=objective_summary,
        )

    def _get_objective_summary(
        self,
        *,
        repo_root: Path,
        objective_id: int | None,
    ) -> str | None:
        """Get objective summary if plan is linked to an objective.

        Args:
            repo_root: Repository root path
            objective_id: Parent objective issue number, or None

        Returns:
            Summary like "Objective #123: Title" if linked, None otherwise
        """
        if objective_id is None:
            return None

        objective_info = self._github_issues.get_issue(repo_root, objective_id)
        if isinstance(objective_info, IssueNotFound):
            return None
        return f"Objective #{objective_id}: {objective_info.title}"
