"""Shared context builders for test scenarios.

This module provides reusable context builder functions to eliminate duplication
across test files. These builders encapsulate common patterns for setting up
ErkContext with appropriate fake implementations.
"""

from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.fake import FakeGit
from erk_shared.github.auth.fake import FakeGitHubAuthGateway
from erk_shared.github.gateway import GitHubGateway, create_fake_github_gateway
from erk_shared.github.pr.fake import FakeGitHubPrGateway
from erk_shared.github.repo.fake import FakeGitHubRepoGateway
from erk_shared.github.run.fake import FakeGitHubRunGateway
from erk_shared.github.workflow.fake import FakeGitHubWorkflowGateway
from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.core.context import ErkContext
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import ErkInMemEnv, ErkIsolatedFsEnv


def build_workspace_test_context(
    env: ErkInMemEnv | ErkIsolatedFsEnv,
    *,
    dry_run: bool = False,
    use_graphite: bool = False,
    current_branch: str | None = None,
    **kwargs,
) -> ErkContext:
    """Build ErkContext for workspace command tests (create, split, consolidate, delete).

    This builder provides a standard context configuration for workspace manipulation
    commands with sensible defaults and support for common testing scenarios.

    Args:
        env: Pure or isolated erk environment fixture
        dry_run: Whether to wrap git operations with DryRunGit (default: False)
        use_graphite: Whether to enable Graphite integration (default: False)
        current_branch: Current branch name for FakeGit configuration (default: None)
        **kwargs: Additional arguments passed to env.build_context()
                  (can include custom git, github, graphite, shell, issues instances)

    Returns:
        ErkContext configured for workspace command testing

    Example:
        >>> with erk_inmem_env(runner) as env:
        ...     ctx = build_workspace_test_context(env, dry_run=True)
        ...     result = runner.invoke(cli, ["delete", "branch"], obj=ctx)
    """
    # Only create default git if not provided in kwargs
    if "git" not in kwargs:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        if dry_run:
            git_ops = DryRunGit(git_ops)
        kwargs["git"] = git_ops

    # Handle legacy 'issues' parameter by converting to GitHubGateway
    # This maintains backwards compatibility with tests that pass issues=FakeGitHubIssues(...)
    if "issues" in kwargs:
        issues_gateway = kwargs.pop("issues")
        # Pop github if also provided - we'll extract data from it for the sub-gateways
        old_github = kwargs.pop("github", None)

        # Extract issues list from FakeGitHubIssues for the pr sub-gateway
        # PlanListService.get_plan_list_data() calls github.pr.get_issues_with_pr_linkages()
        # which uses FakeGitHubPrGateway._issues (a list), not the issue sub-gateway
        issues_list = list(getattr(issues_gateway, "_issues", {}).values())

        # Extract pr_issue_linkages from old FakeGitHub if available
        # This preserves PR linkage data for tests that need it
        # FakeGitHub stores pr_issue_linkages on its internal _pr gateway
        pr_gateway = getattr(old_github, "_pr", None)
        pr_issue_linkages = getattr(pr_gateway, "_pr_issue_linkages", None)
        # FakeGitHub stores workflow_runs_by_node_id on its internal _run gateway
        run_gateway = getattr(old_github, "_run", None)
        workflow_runs_by_node_id = getattr(run_gateway, "_workflow_runs_by_node_id", None)

        # Create GitHubGateway using the provided issues gateway
        kwargs["github"] = GitHubGateway(
            auth=FakeGitHubAuthGateway(),
            pr=FakeGitHubPrGateway(issues=issues_list, pr_issue_linkages=pr_issue_linkages),
            issue=issues_gateway,  # type: ignore[arg-type]
            run=FakeGitHubRunGateway(workflow_runs_by_node_id=workflow_runs_by_node_id),
            workflow=FakeGitHubWorkflowGateway(),
            repo=FakeGitHubRepoGateway(),
        )

    # Provide defaults for other integrations if not in kwargs
    if "github" not in kwargs:
        kwargs["github"] = create_fake_github_gateway()
    if "graphite" not in kwargs:
        kwargs["graphite"] = FakeGraphite()
    if "shell" not in kwargs:
        kwargs["shell"] = FakeShell()

    return env.build_context(
        use_graphite=use_graphite,
        dry_run=dry_run,
        **kwargs,
    )


def build_graphite_test_context(
    env: ErkInMemEnv | ErkIsolatedFsEnv, *, dry_run: bool = False, **kwargs
) -> ErkContext:
    """Build ErkContext for Graphite-enabled command tests.

    Convenience wrapper around build_workspace_test_context() that enables
    Graphite integration by default.

    Args:
        env: Pure or isolated erk environment fixture
        dry_run: Whether to wrap git operations with DryRunGit (default: False)
        **kwargs: Additional arguments passed to env.build_context()

    Returns:
        ErkContext configured for Graphite command testing

    Example:
        >>> with erk_inmem_env(runner) as env:
        ...     ctx = build_graphite_test_context(env)
        ...     result = runner.invoke(cli, ["land-stack"], obj=ctx)
    """
    return build_workspace_test_context(env, dry_run=dry_run, use_graphite=True, **kwargs)


def build_navigation_test_context(
    env: ErkInMemEnv | ErkIsolatedFsEnv, *, current_branch: str | None = None, **kwargs
) -> ErkContext:
    """Build ErkContext for navigation command tests (up, down, goto).

    Convenience wrapper around build_workspace_test_context() for navigation
    commands that typically need to specify the current branch.

    Args:
        env: Pure or isolated erk environment fixture
        current_branch: Current branch name for FakeGit configuration (default: None)
        **kwargs: Additional arguments passed to env.build_context()

    Returns:
        ErkContext configured for navigation command testing

    Example:
        >>> with erk_inmem_env(runner) as env:
        ...     ctx = build_navigation_test_context(env, current_branch="feat-1")
        ...     result = runner.invoke(cli, ["up"], obj=ctx)
    """
    return build_workspace_test_context(env, current_branch=current_branch, **kwargs)
