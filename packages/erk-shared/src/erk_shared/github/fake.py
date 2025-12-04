"""Fake GitHub operations for testing.

DEPRECATED: This module provides backward compatibility for code using the old
monolithic FakeGitHub class. New code should use the composite gateway pattern:

    from erk_shared.github.gateway import GitHubGateway, create_fake_github_gateway
    from erk_shared.github.pr.fake import FakeGitHubPrGateway

The FakeGitHub class is a thin wrapper that delegates to the new sub-gateways.
"""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.auth.fake import FakeGitHubAuthGateway
from erk_shared.github.gateway import GitHubGateway, create_fake_github_gateway
from erk_shared.github.issue.fake import FakeGitHubIssueGateway
from erk_shared.github.issue.types import IssueInfo
from erk_shared.github.pr.fake import FakeGitHubPrGateway
from erk_shared.github.repo.fake import FakeGitHubRepoGateway
from erk_shared.github.run.fake import FakeGitHubRunGateway
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    RepoInfo,
    WorkflowRun,
)
from erk_shared.github.workflow.fake import FakeGitHubWorkflowGateway


class FakeGitHub(GitHub):
    """DEPRECATED: Backward-compatible wrapper around the new sub-gateway pattern.

    This class delegates to FakeGitHubPrGateway, FakeGitHubRunGateway, etc.
    New code should use create_fake_github_gateway() instead.

    The constructor signature is preserved for backward compatibility with
    existing tests.
    """

    def __init__(
        self,
        *,
        prs: dict[str, PullRequestInfo] | None = None,
        pr_statuses: dict[str, tuple[str | None, int | None, str | None]] | None = None,
        pr_bases: dict[int, str] | None = None,
        pr_mergeability: dict[int, PRMergeability | None] | None = None,
        workflow_runs: list[WorkflowRun] | None = None,
        workflow_runs_by_node_id: dict[str, WorkflowRun] | None = None,
        run_logs: dict[str, str] | None = None,
        pr_issue_linkages: dict[int, list[PullRequestInfo]] | None = None,
        polled_run_id: str | None = None,
        pr_checkout_infos: dict[int, PRCheckoutInfo] | None = None,
        authenticated: bool = True,
        auth_username: str | None = "test-user",
        auth_hostname: str | None = "github.com",
        issues: list[IssueInfo] | None = None,
        pr_titles: dict[int, str] | None = None,
        pr_bodies_by_number: dict[int, str] | None = None,
        pr_diffs: dict[int, str] | None = None,
        merge_should_succeed: bool = True,
        pr_update_should_succeed: bool = True,
    ) -> None:
        """Create FakeGitHub with pre-configured state.

        DEPRECATED: Use create_fake_github_gateway() with individual sub-gateway
        fakes instead.
        """
        # Create sub-gateways with the provided configuration
        self._pr = FakeGitHubPrGateway(
            prs=prs,
            pr_statuses=pr_statuses,
            pr_bases=pr_bases,
            pr_mergeability=pr_mergeability,
            pr_issue_linkages=pr_issue_linkages,
            pr_checkout_infos=pr_checkout_infos,
            pr_titles=pr_titles,
            pr_bodies_by_number=pr_bodies_by_number,
            pr_diffs=pr_diffs,
            merge_should_succeed=merge_should_succeed,
            pr_update_should_succeed=pr_update_should_succeed,
            issues=issues or [],
        )
        self._run = FakeGitHubRunGateway(
            workflow_runs=workflow_runs,
            workflow_runs_by_node_id=workflow_runs_by_node_id,
            run_logs=run_logs,
        )
        self._workflow = FakeGitHubWorkflowGateway(
            polled_run_id=polled_run_id,
        )
        self._auth = FakeGitHubAuthGateway(
            authenticated=authenticated,
            username=auth_username,
            hostname=auth_hostname,
        )
        self._issue = FakeGitHubIssueGateway(
            issues={issue.number: issue for issue in (issues or [])},
        )
        self._repo = FakeGitHubRepoGateway()

        # Store reference to runs list for trigger_workflow to add to
        self._workflow_runs = workflow_runs if workflow_runs is not None else []

    # =========================================================================
    # Properties delegating to sub-gateways
    # =========================================================================

    @property
    def merged_prs(self) -> list[int]:
        """List of PR numbers that were merged."""
        return self._pr.merged_prs

    @property
    def closed_prs(self) -> list[int]:
        """Read-only access to tracked PR closures for test assertions."""
        return self._pr.closed_prs

    @property
    def get_prs_for_repo_calls(self) -> list[tuple[Path, bool]]:
        """Read-only access to tracked get_prs_for_repo() calls."""
        return self._pr.get_prs_for_repo_calls

    @property
    def get_pr_status_calls(self) -> list[tuple[Path, str]]:
        """Read-only access to tracked get_pr_status() calls."""
        return self._pr.get_pr_status_calls

    @property
    def created_prs(self) -> list[tuple[str, str, str, str | None, bool]]:
        """Read-only access to tracked PR creations."""
        return self._pr.created_prs

    @property
    def updated_pr_bases(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR base updates."""
        return self._pr.updated_pr_bases

    @property
    def updated_pr_bodies(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR body updates."""
        return self._pr.updated_pr_bodies

    @property
    def updated_pr_titles(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR title updates."""
        return self._pr.updated_pr_titles

    @property
    def triggered_workflows(self) -> list[tuple[str, dict[str, str]]]:
        """Read-only access to tracked workflow triggers."""
        # Strip the ref from the new format for backward compat
        return [(w, i) for w, i, _ref in self._workflow.triggered_workflows]

    @property
    def poll_attempts(self) -> list[tuple[str, str, int, int]]:
        """Read-only access to tracked poll attempts."""
        return self._workflow.poll_attempts

    @property
    def check_auth_status_calls(self) -> list[None]:
        """Get the list of check_auth_status() calls that were made."""
        return self._auth.check_auth_status_calls

    # =========================================================================
    # PR operations - delegate to FakeGitHubPrGateway
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

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        return self._pr.fetch_pr_titles_batch(prs, repo_root)

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        return self._pr.enrich_prs_with_ci_status_batch(prs, repo_root)

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

    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        return self._pr.get_issues_with_pr_linkages(location, labels, state, limit)

    # =========================================================================
    # Run operations - delegate to FakeGitHubRunGateway
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

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        return self._run.get_workflow_runs_by_node_ids(repo_root, node_ids)

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        return self._run.get_workflow_run_node_id(repo_root, run_id)

    # =========================================================================
    # Workflow operations - delegate to FakeGitHubWorkflowGateway
    # =========================================================================

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        run_id = self._workflow.trigger_workflow(repo_root, workflow, inputs, ref)
        # Also add to run gateway's list so get_workflow_run can find it
        branch = inputs.get("branch_name", "main")
        triggered_run = WorkflowRun(
            run_id=run_id,
            status="queued",
            conclusion=None,
            branch=branch,
            head_sha="abc123",
            node_id=f"WFR_{run_id}",
        )
        self._run._workflow_runs.insert(0, triggered_run)
        return run_id

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        return self._workflow.poll_for_workflow_run(
            repo_root, workflow, branch_name, timeout, poll_interval
        )

    # =========================================================================
    # Auth operations - delegate to FakeGitHubAuthGateway
    # =========================================================================

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        return self._auth.check_auth_status()

    # =========================================================================
    # Repo operations - delegate to FakeGitHubRepoGateway
    # =========================================================================

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        return self._repo.get_repo_info(repo_root)


# =============================================================================
# Re-exports for migration convenience
# =============================================================================
# These allow importing new types from the old location during migration.

__all__ = [
    # Legacy (backward compat)
    "FakeGitHub",
    # New composite gateway
    "GitHubGateway",
    "create_fake_github_gateway",
    # New sub-gateway fakes
    "FakeGitHubAuthGateway",
    "FakeGitHubPrGateway",
    "FakeGitHubIssueGateway",
    "FakeGitHubRunGateway",
    "FakeGitHubWorkflowGateway",
    "FakeGitHubRepoGateway",
]
