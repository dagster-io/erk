"""Composite gateway for GitHub operations."""

from dataclasses import dataclass

from erk_shared.github.auth.abc import GitHubAuthGateway
from erk_shared.github.issue.abc import GitHubIssueGateway
from erk_shared.github.pr.abc import GitHubPrGateway
from erk_shared.github.repo.abc import GitHubRepoGateway
from erk_shared.github.run.abc import GitHubRunGateway
from erk_shared.github.workflow.abc import GitHubWorkflowGateway


@dataclass(frozen=True)
class GitHubGateway:
    """Composite gateway providing access to all GitHub sub-gateways.

    This class follows the composite gateway pattern, organizing GitHub
    operations into logical groups that align with the `gh` CLI command
    hierarchy (auth, pr, issue, run, workflow, repo).

    Usage:
        ctx.github.auth.check_auth_status()
        ctx.github.pr.create_pr(...)
        ctx.github.issue.create_issue(...)
        ctx.github.run.list_workflow_runs(...)
        ctx.github.workflow.trigger_workflow(...)
        ctx.github.repo.get_repo_info(...)
    """

    auth: GitHubAuthGateway
    pr: GitHubPrGateway
    issue: GitHubIssueGateway
    run: GitHubRunGateway
    workflow: GitHubWorkflowGateway
    repo: GitHubRepoGateway


def create_fake_github_gateway(
    *,
    auth: GitHubAuthGateway | None = None,
    pr: GitHubPrGateway | None = None,
    issue: GitHubIssueGateway | None = None,
    run: GitHubRunGateway | None = None,
    workflow: GitHubWorkflowGateway | None = None,
    repo: GitHubRepoGateway | None = None,
) -> GitHubGateway:
    """Create a GitHubGateway with fake sub-gateways for testing.

    This factory function creates a GitHubGateway populated with
    fake implementations. Provide custom sub-gateways to override
    defaults. Use this in tests instead of manually constructing.

    Args:
        auth: Optional custom auth gateway (defaults to FakeGitHubAuthGateway)
        pr: Optional custom PR gateway (defaults to FakeGitHubPrGateway)
        issue: Optional custom issue gateway (defaults to FakeGitHubIssueGateway)
        run: Optional custom run gateway (defaults to FakeGitHubRunGateway)
        workflow: Optional custom workflow gateway (defaults to FakeGitHubWorkflowGateway)
        repo: Optional custom repo gateway (defaults to FakeGitHubRepoGateway)

    Returns:
        GitHubGateway with specified or default fake sub-gateways

    Example:
        >>> # Default fakes
        >>> github = create_fake_github_gateway()
        >>> ctx = ErkContext.for_test(github=github)

        >>> # Custom PR gateway for specific test assertions
        >>> from erk_shared.github.pr.fake import FakeGitHubPrGateway
        >>> pr = FakeGitHubPrGateway(pr_issue_linkages={42: [pr1, pr2]})
        >>> github = create_fake_github_gateway(pr=pr)
        >>> # Later: assert pr.closed_prs == [100]
    """
    from erk_shared.github.auth.fake import FakeGitHubAuthGateway
    from erk_shared.github.issue.fake import FakeGitHubIssueGateway
    from erk_shared.github.pr.fake import FakeGitHubPrGateway
    from erk_shared.github.repo.fake import FakeGitHubRepoGateway
    from erk_shared.github.run.fake import FakeGitHubRunGateway
    from erk_shared.github.workflow.fake import FakeGitHubWorkflowGateway

    return GitHubGateway(
        auth=auth or FakeGitHubAuthGateway(),
        pr=pr or FakeGitHubPrGateway(),
        issue=issue or FakeGitHubIssueGateway(),
        run=run or FakeGitHubRunGateway(),
        workflow=workflow or FakeGitHubWorkflowGateway(),
        repo=repo or FakeGitHubRepoGateway(),
    )
