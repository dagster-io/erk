"""Stub GitHub implementation for dot-agent-kit context creation.

This module provides a minimal stub implementation of the GitHub interface
that can be imported by dot-agent-kit without requiring the full erk package.
The main erk package has a complete RealGitHub implementation with all the
actual logic.

This stub raises NotImplementedError for all methods since dot-agent-kit
never actually calls methods on the GitHub instance - it only uses GitHubIssues.
"""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.types import (
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    WorkflowRun,
)


class RealGitHub(GitHub):
    """Stub implementation for context creation only.

    This is a minimal stub that allows dot-agent-kit to create a context
    without depending on the full erk package. All methods raise
    NotImplementedError since they should not be called by dot-agent-kit.

    The real implementation with full functionality is in erk.core.github.real.
    """

    def __init__(self):
        """Initialize RealGitHub stub."""

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

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
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real."
        )
        raise NotImplementedError(msg)

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_prs_linked_to_issues(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[PullRequestInfo]]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def get_workflow_runs_batch(
        self,
        repo_root: Path,
        run_ids: list[str],
        *,
        workflow: str | None = None,
        user: str | None = None,
    ) -> dict[str, WorkflowRun | None]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Stub method - not implemented in erk-shared."""
        msg = (
            "RealGitHub from erk-shared is a stub for context creation only. "
            "Use the full implementation from erk.core.github.real if you need "
            "actual GitHub operations."
        )
        raise NotImplementedError(msg)
