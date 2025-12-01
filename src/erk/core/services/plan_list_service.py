"""Service for efficiently fetching plan list data via batched API calls.

Schema Version 2 Optimization:
- Extracts last_dispatched_run_id directly from issue body metadata
- Uses batch workflow run lookup by IDs (single GraphQL query for all plans)
- Eliminates expensive get_workflow_runs_by_titles() which fetched 100+ runs
- Eliminates comments fetch (worktree_name now in issue body)
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import extract_plan_header_dispatch_info
from erk_shared.github.types import PullRequestInfo, WorkflowRun

from erk.cli.constants import DISPATCH_WORKFLOW_NAME


@dataclass(frozen=True)
class PlanListData:
    """Combined data for plan listing (schema v2 only).

    Attributes:
        issues: List of IssueInfo objects
        pr_linkages: Mapping of issue_number -> list of PRs that close that issue
        workflow_runs: Mapping of issue_number -> most relevant WorkflowRun
    """

    issues: list[IssueInfo]
    pr_linkages: dict[int, list[PullRequestInfo]]
    workflow_runs: dict[int, WorkflowRun | None]


class PlanListService:
    """Service for efficiently fetching plan list data.

    Composes GitHub and GitHubIssues integrations to batch fetch all data
    needed for plan listing.

    Schema Version 2 Only:
    - Issues have last_dispatched_run_id in body metadata
    - Uses get_workflow_runs_batch(run_ids) for single GraphQL query
    - Extracts worktree_name from issue body (no comments needed)
    """

    def __init__(self, github: GitHub, github_issues: GitHubIssues) -> None:
        """Initialize PlanListService with required integrations.

        Args:
            github: GitHub integration for PR and workflow operations
            github_issues: GitHub issues integration for issue operations
        """
        self._github = github
        self._github_issues = github_issues

    def get_plan_list_data(
        self,
        repo_root: Path,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        skip_pr_linkages: bool = False,
    ) -> PlanListData:
        """Batch fetch all data needed for plan listing.

        Schema Version 2 Only:
        - Extracts last_dispatched_run_id from issue body (plan-header block)
        - Uses get_workflow_runs_batch() for single GraphQL query
        - Extracts worktree_name from issue body (no comments needed)

        Args:
            repo_root: Repository root directory
            labels: Labels to filter issues by (e.g., ["erk-plan"])
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum number of issues to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)
            skip_pr_linkages: If True, skip fetching PR linkages (for performance)

        Returns:
            PlanListData containing issues, PR linkages, and workflow runs
        """
        # Fetch issues using GitHubIssues integration
        issues = self._github_issues.list_issues(repo_root, labels=labels, state=state, limit=limit)

        # Extract issue numbers for batch operations
        issue_numbers = [issue.number for issue in issues]

        # Conditionally fetch PR linkages (skip for performance when not needed)
        pr_linkages: dict[int, list[PullRequestInfo]] = {}
        if not skip_pr_linkages:
            pr_linkages = self._github.get_prs_linked_to_issues(repo_root, issue_numbers)

        # Conditionally fetch workflow runs (skip for performance when not needed)
        workflow_runs: dict[int, WorkflowRun | None] = {}
        if not skip_workflow_runs:
            # Collect all run IDs and build mapping back to issue numbers
            run_id_to_issue: dict[str, int] = {}
            for issue in issues:
                run_id, _ = extract_plan_header_dispatch_info(issue.body)
                if run_id is not None:
                    run_id_to_issue[run_id] = issue.number

            # Batch fetch all workflow runs in single API call
            # Uses gh run list with --workflow and --user filters for efficiency
            if run_id_to_issue:
                run_ids = list(run_id_to_issue.keys())
                # Get current user from gh auth status for filtering
                _, username, _ = self._github.check_auth_status()
                runs_by_id = self._github.get_workflow_runs_batch(
                    repo_root,
                    run_ids,
                    workflow=DISPATCH_WORKFLOW_NAME,
                    user=username,
                )

                # Map results back to issue numbers
                for run_id, run in runs_by_id.items():
                    issue_number = run_id_to_issue[run_id]
                    workflow_runs[issue_number] = run

        return PlanListData(
            issues=issues,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
        )
