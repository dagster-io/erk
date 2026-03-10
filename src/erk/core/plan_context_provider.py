"""Plan context provider for PR description generation.

This module provides plan context for branches linked to plans,
enabling more accurate PR descriptions that understand the "why" behind changes.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.github.issues.types import IssueNotFound
from erk_shared.gateway.remote_github.abc import RemoteGitHub
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import PlanNotFound


@dataclass(frozen=True)
class PlanContext:
    """Context from an erk plan for PR generation.

    Attributes:
        pr_id: The PR identifier (e.g., "123" for PR numbers)
        plan_content: The full plan markdown content
        objective_summary: Optional summary of the parent objective (e.g., "Objective #123: Title")
    """

    pr_id: str
    plan_content: str
    objective_summary: str | None


class PlanContextProvider:
    """Provides plan context for branches linked to erk plans.

    This provider extracts plan content from the plan backend when a branch
    is associated with a plan. Uses PlanBackend.get_plan_for_branch() to
    encapsulate the branch→plan resolution strategy.

    Uses RemoteGitHub for objective title lookup (objectives are issues, not plans).
    """

    def __init__(self, *, plan_backend: PlanBackend, remote_github: RemoteGitHub) -> None:
        self._plan_backend = plan_backend
        self._remote_github = remote_github

    def get_plan_context(
        self,
        *,
        repo_root: Path,
        branch_name: str,
        owner: str,
        repo: str,
    ) -> PlanContext | None:
        """Get plan context for a branch, if available.

        Attempts to fetch plan context by:
        1. Resolving branch to plan via PlanBackend.get_plan_for_branch()
        2. Optionally getting objective title if linked

        Returns None on any failure, allowing graceful degradation for
        branches not linked to plans.
        """
        result = self._plan_backend.get_plan_for_branch(repo_root, branch_name)
        if isinstance(result, PlanNotFound):
            return None

        objective_summary = self._get_objective_summary(
            owner=owner,
            repo=repo,
            objective_id=result.objective_id,
        )

        return PlanContext(
            pr_id=result.pr_identifier,
            plan_content=result.body,
            objective_summary=objective_summary,
        )

    def _get_objective_summary(
        self,
        *,
        owner: str,
        repo: str,
        objective_id: int | None,
    ) -> str | None:
        """Get objective summary if plan is linked to an objective."""
        if objective_id is None:
            return None

        objective_info = self._remote_github.get_issue(owner=owner, repo=repo, number=objective_id)
        if isinstance(objective_info, IssueNotFound):
            return None
        return f"Objective #{objective_id}: {objective_info.title}"
