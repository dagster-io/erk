"""Production implementation of GitHub operations.

DEPRECATED: This module provides backward compatibility for code that imports
RealGitHub directly. New code should use GitHubGateway with sub-gateways.

The RealGitHub class is now a thin wrapper that delegates to the new
sub-gateway implementations:
- github.auth.real.RealGitHubAuthGateway
- github.pr.real.RealGitHubPrGateway
- github.run.real.RealGitHubRunGateway
- github.workflow.real.RealGitHubWorkflowGateway
- github.repo.real.RealGitHubRepoGateway
"""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.auth.real import RealGitHubAuthGateway
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.pr.real import RealGitHubPrGateway
from erk_shared.github.repo.real import RealGitHubRepoGateway
from erk_shared.github.run.real import RealGitHubRunGateway
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    RepoInfo,
    WorkflowRun,
)
from erk_shared.github.workflow.real import RealGitHubWorkflowGateway
from erk_shared.integrations.time.abc import Time


class RealGitHub(GitHub):
    """DEPRECATED: Backward-compatible wrapper around the new sub-gateway pattern.

    This class maintains the original RealGitHub interface while delegating
    all operations to the new focused sub-gateways. Use GitHubGateway for new code.

    Migration path:
        # Old pattern (deprecated):
        github = RealGitHub(time)
        github.get_pr_status(repo_root, branch, debug=False)

        # New pattern (preferred):
        from erk_shared.github.gateway import GitHubGateway
        github = GitHubGateway(
            auth=RealGitHubAuthGateway(),
            pr=RealGitHubPrGateway(),
            ...
        )
        github.pr.get_pr_status(repo_root, branch, debug=False)
    """

    def __init__(self, time: Time) -> None:
        """Initialize RealGitHub with Time abstraction.

        Args:
            time: Time abstraction for sleep operations
        """
        self._time = time
        self._auth = RealGitHubAuthGateway()
        self._pr = RealGitHubPrGateway()
        self._run = RealGitHubRunGateway(time)
        self._workflow = RealGitHubWorkflowGateway(time)
        self._repo = RealGitHubRepoGateway()

    # =========================================================================
    # Auth operations - delegate to RealGitHubAuthGateway
    # =========================================================================

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        return self._auth.check_auth_status()

    # =========================================================================
    # PR operations - delegate to RealGitHubPrGateway
    # =========================================================================

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        return self._pr.get_prs_for_repo(repo_root, include_checks=include_checks)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        return self._pr.get_pr_status(repo_root, branch, debug=debug)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        return self._pr.get_pr_base_branch(repo_root, pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        self._pr.update_pr_base_branch(repo_root, pr_number, new_base)

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        self._pr.update_pr_body(repo_root, pr_number, body)

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        return self._pr.get_pr_mergeability(repo_root, pr_number)

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        return self._pr.enrich_prs_with_ci_status_batch(prs, repo_root)

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        return self._pr.fetch_pr_titles_batch(prs, repo_root)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
        subject: str | None = None,
        body: str | None = None,
    ) -> bool:
        return self._pr.merge_pr(
            repo_root, pr_number, squash=squash, verbose=verbose, subject=subject, body=body
        )

    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
        *,
        draft: bool = False,
    ) -> int:
        return self._pr.create_pr(repo_root, branch, title, body, base, draft=draft)

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        self._pr.close_pr(repo_root, pr_number)

    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        return self._pr.get_prs_linked_to_issues(location, issue_numbers)

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        return self._pr.get_pr_checkout_info(repo_root, pr_number)

    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        return self._pr.get_issues_with_pr_linkages(location, labels, state=state, limit=limit)

    def get_pr_info_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        return self._pr.get_pr_info_for_branch(repo_root, branch)

    def get_pr_state_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        return self._pr.get_pr_state_for_branch(repo_root, branch)

    def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
        return self._pr.get_pr_title(repo_root, pr_number)

    def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
        return self._pr.get_pr_body(repo_root, pr_number)

    def update_pr_title_and_body(
        self, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        self._pr.update_pr_title_and_body(repo_root, pr_number, title, body)

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        self._pr.mark_pr_ready(repo_root, pr_number)

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        return self._pr.get_pr_diff(repo_root, pr_number)

    def get_pr_mergeability_status(self, repo_root: Path, pr_number: int) -> tuple[str, str]:
        return self._pr.get_pr_mergeability_status(repo_root, pr_number)

    # =========================================================================
    # Run operations - delegate to RealGitHubRunGateway
    # =========================================================================

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        return self._run.list_workflow_runs(repo_root, workflow, limit, user=user)

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        return self._run.get_workflow_run(repo_root, run_id)

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        return self._run.get_run_logs(repo_root, run_id)

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        return self._run.get_workflow_runs_by_branches(repo_root, workflow, branches)

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        return self._run.poll_for_workflow_run(
            repo_root, workflow, branch_name, timeout, poll_interval
        )

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        return self._run.get_workflow_runs_by_node_ids(repo_root, node_ids)

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        return self._run.get_workflow_run_node_id(repo_root, run_id)

    # =========================================================================
    # Workflow operations - delegate to RealGitHubWorkflowGateway
    # =========================================================================

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        return self._workflow.trigger_workflow(repo_root, workflow, inputs, ref)

    # =========================================================================
    # Repo operations - delegate to RealGitHubRepoGateway
    # =========================================================================

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        return self._repo.get_repo_info(repo_root)
